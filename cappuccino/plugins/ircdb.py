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

import irc3
import orjson
from aiohttp import web
from irc3 import rfc
from sqlalchemy import (
    desc,
    inspect,
    nullslast,
    select,
)
from sqlalchemy.exc import IntegrityError

from cappuccino.db.models.ircdb import Channel, User
from cappuccino.plugins import Plugin
from cappuccino.util.formatting import unstyle


def _serialize_user(user: User) -> dict:
    def _coerce(column: str, value):
        if isinstance(value, list):
            return [unstyle(v) for v in value]
        if isinstance(value, str):
            return unstyle(value)
        if column == "last_seen":
            return value.timestamp()
        return value

    return {
        column: _coerce(column, attr.value)
        for column, attr in inspect(user).attrs.items()
        if attr.value is not None
    }


@irc3.plugin
class IrcDB(Plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self._server_task: asyncio.Task | None = None

    @irc3.event(rfc.CONNECTED)
    def _on_connect(self, **kwargs):
        self._start_server()

    @irc3.event(irc3.rfc.JOIN)
    def _create_channel_on_join(self, mask, channel, **kwargs):
        if mask.nick == self.bot.nick:
            with (
                contextlib.suppress(IntegrityError),
                self.bot.ircdb.session.begin() as session,
            ):
                session.add(Channel(name=channel))

    def _start_server(self):
        if self.config.get("enable_http_server", False):
            host = self.config.get("http_host", "127.0.0.1")
            port = int(self.config.get("http_port", 8080))
            self.logger.info(f"Starting HTTP server on {host}:{port}.")
            self._server_task = self.bot.create_task(self._run_server())

    def _stop_server(self):
        if self._server_task:
            self.logger.info("Stopping HTTP server.")
            self._server_task.cancel()
            self._server_task = None

    def before_reload(self):
        self._stop_server()

    def after_reload(self):
        self._start_server()

    async def _run_server(self):
        host = self.config.get("http_host", "127.0.0.1")
        port = int(self.config.get("http_port", 8080))
        app = web.Application()
        app.router.add_get("/", self._json_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        try:
            await asyncio.Future()
        finally:
            await runner.cleanup()

    async def _json_handler(self, request: web.Request) -> web.Response:
        loop = asyncio.get_running_loop()
        data = await loop.run_in_executor(None, self._build_json)
        return web.Response(body=data, content_type="application/json")

    def _build_json(self) -> bytes:
        with self.bot.ircdb.session() as session:
            users = session.scalars(
                select(User).order_by(nullslast(desc(User.last_seen)))
            ).all()
        return orjson.dumps([_serialize_user(user) for user in users])
