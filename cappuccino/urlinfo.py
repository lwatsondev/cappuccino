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
from niquests import AsyncSession, RequestException
from niquests.cookies import RequestsCookieJar

from cappuccino import Plugin
from cappuccino.util import meta
from cappuccino.util.formatting import Color, style, truncate_with_ellipsis, unstyle


class ResponseBodyTooLarge(RequestException):
    pass


class InvalidIPAddressError(Exception):
    pass


class ContentTypeNotAllowedError(Exception):
    pass


class RequestTimeout(RequestException):
    pass


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
    _max_bytes = 10 * 1000 * 1000  # 10M
    _url_regex = re.compile(r"https?://\S+", re.IGNORECASE | re.UNICODE)
    _max_title_length = 300
    _request_timeout = 5
    _html_mimetypes = ["text/html", "application/xhtml+xml"]
    _request_chunk_size = 1024  # Bytes
    _allowed_content_types = ["text", "video", "application"]

    def __init__(self, bot):
        super().__init__(bot)
        self._ignore_nicks: list[str] = self.config.get("ignore_nicks", "").split()
        self._ignore_hostnames: list[str] = self.config.get("ignore_hostnames", [])
        self._real_user_agent: str = f"cappuccino {meta.VERSION} - {meta.SOURCE}"
        self._fake_user_agent: str = self.config.get(
            "fake_useragent", "Googlebot/2.1 (+http://www.google.com/bot.html)"
        )
        self._fake_useragent_hostnames: list[str] = self.config.get(
            "fake_useragent_hostnames", []
        )
        self._cookie_jar = RequestsCookieJar()
        self._cookie_jar.set(
            "CONSENT", f"YES+srp.gws-20210512-0-RC3.en+FX+{1 + randbelow(1000)}"
        )
        self._session: AsyncSession = AsyncSession()
        self._session.cookies.update(self._cookie_jar)
        self._session.headers.update({"Accept-Language": "en-GB,en-US,en;q=0.5"})

    @irc3.event(
        rf"(?iu):(?P<mask>\S+!\S+@\S+) PRIVMSG (?P<target>#\S+) :(?P<data>.*{_url_regex.pattern}).*"
    )
    async def on_url(self, mask, target, data):  # noqa: C901
        if mask.nick in self._ignore_nicks or data.startswith(
            (self.bot.config.cmd, f"{self.bot.nick}: ")
        ):
            return

        urls = [_clean_url(url) for url in set(self._url_regex.findall(data))] or []
        for url in urls:
            if urlparse(url).hostname in self._ignore_hostnames:
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
                    if (size and mimetype) and mimetype not in self._html_mimetypes:
                        size = naturalsize(size)
                        reply = f"{reply} ({size} - {mimetype})"
                    messages.append(reply)

        if messages:
            pipe_character = style(" | ", fg=Color.LIGHT_GRAY)
            self.bot.privmsg(target, pipe_character.join(messages))

    async def _stream_response(self, response) -> str:
        content = StringIO()
        async for chunk in await response.iter_content(self._request_chunk_size):
            if not chunk:
                continue
            content_length = content.write(chunk.decode("UTF-8", errors="ignore"))
            if content_length > self._max_bytes:
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

        user_agent = (
            self._fake_user_agent
            if any(
                f".{hostname}".endswith(f".{host}")
                for host in self._fake_useragent_hostnames
            )
            else self._real_user_agent
        )

        response = await self._session.get(
            url,
            stream=True,
            timeout=self._request_timeout,
            headers={"User-Agent": user_agent},
        )
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
            if main_type not in self._allowed_content_types:
                raise ContentTypeNotAllowedError(
                    f"{main_type} not in {self._allowed_content_types}"
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
        elif mimetype in self._html_mimetypes or mimetype == "text/plain":
            content = await self._stream_response(response)
            if content and not size:
                size = len(content.encode("UTF-8"))

            soup = bs4.BeautifulSoup(content, "html5lib")
            title = _extract_title_from_soup(soup)

            site_name = _extract_site_name_from_soup(soup)
            if (site_name and len(site_name) < (site_name_max_size := 16)) and (
                len(site_name) > site_name_max_size
            ):
                site_name = truncate_with_ellipsis(title, site_name_max_size)

            if not title and (content and mimetype not in self._html_mimetypes):
                title = re.sub(r"\s+", " ", " ".join(content.split("\n")))

        if title:
            title = unstyle(html.unescape(title).strip())
            if len(title) > self._max_title_length:
                title = truncate_with_ellipsis(title, self._max_title_length)

        return title, size
