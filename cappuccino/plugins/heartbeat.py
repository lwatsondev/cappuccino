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
from dataclasses import dataclass, field
from http import HTTPMethod

import irc3
from irc3 import rfc
from niquests.exceptions import HTTPError

from cappuccino.plugins import Plugin


@dataclass
class HeartbeatEndpoint:
    url: str
    method: str = HTTPMethod.GET
    headers: dict = field(default_factory=dict)
    params: dict = field(default_factory=dict)
    interval: int = 30


@irc3.plugin
class Heartbeat(Plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self._ping_tasks: list[asyncio.Task] = []
        self._endpoints: list[HeartbeatEndpoint] = self._load_endpoints()

    def _load_endpoints(self) -> list[HeartbeatEndpoint]:
        endpoints_config = self.config.get("endpoints", [])
        return [
            HeartbeatEndpoint(
                url=endpoint.get("url"),
                method=endpoint.get("method", HTTPMethod.GET),
                headers=endpoint.get("headers", {}),
                params=endpoint.get("params", {}),
                interval=endpoint.get("interval", 30),
            )
            for endpoint in endpoints_config
        ]

    @irc3.event(rfc.CONNECTED)
    def _on_connect(
        self, srv: str | None = None, me: str | None = None, data: str | None = None
    ):
        self._start_ping_loops()

    def _start_ping_loops(self):
        for endpoint in self._endpoints:
            self.logger.info(f"Starting heartbeat ping loop for {endpoint.url}.")
            self._ping_tasks.append(self.bot.create_task(self._ping_loop(endpoint)))

    def _stop_ping_loops(self):
        for task in self._ping_tasks:
            task.cancel()

        self._ping_tasks.clear()

    def before_reload(self):
        self._stop_ping_loops()

    def after_reload(self):
        self._endpoints = self._load_endpoints()
        self._start_ping_loops()

    async def ping(self, endpoint: HeartbeatEndpoint):
        self.logger.debug(f"Pinging {endpoint.url}")
        try:
            response = await self._http.request(
                endpoint.method,
                endpoint.url,
                params=endpoint.params or None,
                headers=endpoint.headers or None,
                timeout=5,
            )
            response.raise_for_status()
            self.logger.debug("Ping succeeded.")
        except HTTPError:
            self.logger.exception("Ping failed.")

    async def _ping_loop(self, endpoint: HeartbeatEndpoint):
        self.logger.info(f"Pinging {endpoint.url} every {endpoint.interval} seconds.")
        while True:
            try:
                await self.ping(endpoint)
            except Exception:
                self.logger.exception("Unhandled exception in ping loop.")

            await asyncio.sleep(endpoint.interval)
