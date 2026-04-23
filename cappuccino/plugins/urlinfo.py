#  This file is part of cappuccino.
#
#  cappuccino is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  cappuccino is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with cappuccino.  If not, see <https://www.gnu.org/licenses/>.

import asyncio
import contextlib
import html
import ipaddress
import re
import socket
from secrets import randbelow
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from email.headerregistry import ContentDispositionHeader, ContentTypeHeader

from email.policy import EmailPolicy
from io import StringIO
from urllib.parse import urlparse

import bs4
import irc3
from humanize import naturalsize
from niquests import RequestException
from niquests.cookies import RequestsCookieJar

from cappuccino.plugins import Plugin
from cappuccino.util.formatting import Color, style, truncate_with_ellipsis, unstyle


class ResponseBodyTooLarge(RequestException):
    pass


class InvalidIPAddressError(Exception):
    pass


class ContentTypeNotAllowedError(Exception):
    pass


class RequestTimeout(RequestException):
    pass


__RESPONSE_MAX_BYTES = 10 * 1000 * 1000  # 10M
__URL_REGEX = re.compile(r"https?://\S+", re.IGNORECASE | re.UNICODE)
__HTML_MIMETYPES = ["text/html", "application/xhtml+xml"]
__REQUEST_CHUNK_SIZE = 1024  # Bytes
__ALLOWED_CONTENT_TYPES = ["text", "video", "application"]


def _clean_url(url: str):
    if url:
        url = url.rstrip("'.,\"\1")
        braces = [("{", "}"), ("<", ">"), ("[", "]"), ("(", ")")]
        for left_brace, right_brace in braces:
            if left_brace not in url and url.endswith(right_brace):
                url = url.rstrip(right_brace)
    return url


def _extract_title_from_soup(soup: bs4.BeautifulSoup):
    if title_tag := soup.find("meta", property="og:title", content=True):
        return title_tag.get("content")
    with contextlib.suppress(AttributeError):
        return soup.title.string


def _extract_site_name_from_soup(soup: bs4.BeautifulSoup):
    if site_name_tag := soup.find("meta", property="og:site_name", content=True):
        return site_name_tag.get("content")
    return None


@irc3.plugin
class UrlInfo(Plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self._cookie_jar = RequestsCookieJar()
        # Set a consent cookie for YouTube to bypass the EU cookie wall, which interferes with title extraction by returning a 403.
        self._cookie_jar.set(
            "CONSENT", f"YES+srp.gws-20210512-0-RC3.en+FX+{1 + randbelow(1000)}"
        )
        self._requests.cookies.update(self._cookie_jar)
        self._requests.headers.update(
            {
                "Accept-Language": "en-GB,en-US,en;q=0.5",
                "User-Agent": "Googlebot/2.1 (+http://www.google.com/bot.html)",
            }
        )

    @irc3.event(
        rf"(?iu):(?P<mask>\S+!\S+@\S+) PRIVMSG (?P<target>#\S+) :(?P<data>.*{__URL_REGEX.pattern}).*"
    )
    async def on_url(self, mask, target, data):  # noqa: C901
        if mask.nick in self.config.get("ignore_nicks", "").split() or data.startswith(
            (self.bot.config.cmd, f"{self.bot.nick}: ")
        ):
            return

        urls = [_clean_url(url) for url in set(__URL_REGEX.findall(data))] or []
        for url in urls:
            if urlparse(url).hostname in self.config.get("ignore_hostnames", []):
                urls.remove(url)

        if not urls:
            return

        urls = urls[:3]
        messages = []
        results = await asyncio.gather(
            *[self._process_url(url) for url in urls],
            return_exceptions=True,
        )

        for url, result in zip(urls, results, strict=False):
            hostname = urlparse(url).hostname

            if isinstance(result, InvalidIPAddressError):
                self.logger.debug(f"Invalid IP address for {url}: {result}")
                return
            if isinstance(result, ContentTypeNotAllowedError):
                self.logger.debug(f"Content type not allowed for {url}: {result}")
            elif isinstance(result, (socket.gaierror, ValueError, RequestException)):
                ex = result
                hostname = style(hostname, fg=Color.RED)

                with contextlib.suppress(AttributeError, IndexError):
                    ex = ex.args[0].reason
                error = style(ex, bold=True)
                if isinstance(ex, RequestException):
                    if ex.response is not None and ex.response.reason is not None:
                        status_code = style(ex.response.status_code, bold=True)
                        error = style(ex.response.reason, bold=True)
                        messages.append(f"[ {hostname} ] {status_code} {error}")
                    return
                messages.append(f"[ {hostname} ] {error}")
            elif not isinstance(result, Exception):
                hostname, title, mimetype, size = result
                hostname = style(hostname, fg=Color.GREEN)
                if title is not None:
                    title = style(title, bold=True)
                    reply = f"[ {hostname} ] {title}"
                    if (size and mimetype) and mimetype not in __HTML_MIMETYPES:
                        size = naturalsize(size)
                        reply = f"{reply} ({size} - {mimetype})"
                    messages.append(reply)

        if messages:
            pipe_character = style(" | ", fg=Color.LIGHT_GRAY)
            self.bot.privmsg(target, pipe_character.join(messages))

    async def _stream_response(self, response) -> str:
        content = StringIO()
        async for chunk in await response.iter_content(__REQUEST_CHUNK_SIZE):
            if not chunk:
                continue
            content_length = content.write(chunk.decode("UTF-8", errors="ignore"))
            if content_length > __RESPONSE_MAX_BYTES:
                size = naturalsize(content_length)
                raise ResponseBodyTooLarge(
                    f"Couldn't find the page title within {size}."
                )
        return content.getvalue()

    async def _process_url(self, url: str):
        urlp = urlparse(url)
        if urlp.netloc.lower().removeprefix("www.") == "twitter.com":
            urlp = urlp._replace(netloc="nitter.net")
        url = urlp.geturl()

        hostname = urlp.hostname
        await self._validate_ip_address(hostname)
        hostname = hostname.removeprefix("www.")

        response = await self._requests.get(url, stream=True)
        response.raise_for_status()

        content_type = response.headers.get("Content-Type")
        self._validate_content_type(content_type)
        mimetype = None
        if content_type:
            mimetype = EmailPolicy.header_factory(
                "content-type", content_type
            ).content_type

        title, size = await self._extract_title_and_size(response, content_type)

        return hostname, title, mimetype, size

    async def _validate_ip_address(self, hostname: str):
        loop = asyncio.get_running_loop()
        results = await loop.getaddrinfo(hostname, None)
        for _, _, _, _, sockaddr in results:
            ip = ipaddress.ip_address(sockaddr[0])
            if not ip.is_global:
                raise InvalidIPAddressError(
                    f"{hostname} is not a publicly routable address."
                )

    def _validate_content_type(self, content_type: str):
        if content_type:
            header: ContentTypeHeader = EmailPolicy.header_factory(
                "content-type", content_type
            )
            main_type = header.maintype
            if main_type not in __ALLOWED_CONTENT_TYPES:
                raise ContentTypeNotAllowedError(
                    f"{main_type} not in {__ALLOWED_CONTENT_TYPES}"
                )

    async def _extract_title_and_size(self, response, content_type: str):
        title = None
        size = int(response.headers.get("Content-Length", 0))
        mimetype = None
        if content_type:
            ct_header: ContentTypeHeader = EmailPolicy.header_factory(
                "content-type", content_type
            )
            mimetype = ct_header.content_type
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition:
            header: ContentDispositionHeader = EmailPolicy.header_factory(
                "content-disposition", content_disposition
            )
            title = header.params.get("filename")
        elif mimetype in __HTML_MIMETYPES or mimetype == "text/plain":
            content = await self._stream_response(response)
            if content and not size:
                size = len(content.encode("UTF-8"))

            soup = bs4.BeautifulSoup(content, "html5lib")
            title = _extract_title_from_soup(soup)

            site_name = _extract_site_name_from_soup(soup)
            site_name_max_size = self.config.get("max_site_name_length", 16)
            if (site_name and len(site_name) < site_name_max_size) and (
                len(site_name) > site_name_max_size
            ):
                site_name = truncate_with_ellipsis(title, site_name_max_size)

            if not title and (content and mimetype not in __HTML_MIMETYPES):
                title = re.sub(r"\s+", " ", " ".join(content.split("\n")))

        if title:
            title = unstyle(html.unescape(title).strip())
            max_title_length = self.config.get("max_title_length", 300)
            if len(title) > max_title_length:
                title = truncate_with_ellipsis(title, max_title_length)

        return title, size
