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

import irc3
from irc3 import rfc
from niquests.exceptions import HTTPError

from cappuccino.plugins import Plugin


@irc3.plugin
class UptimeKuma(Plugin):
    def __init__(self, bot):
        super().__init__(bot)
        self._ping_task: asyncio.Task | None = None

    @irc3.event(rfc.CONNECTED)
    def _on_connect(
        self, srv: str | None = None, me: str | None = None, data: str | None = None
    ):
        self._start_ping_loop()

    def _start_ping_loop(self):
        if self.config.get("webhook"):
            self.logger.info("Starting Uptime Kuma ping loop.")
            self._ping_task = self.bot.create_task(self._ping_loop())

    def _stop_ping_loop(self):
        if self._ping_task:
            self.logger.info("Stopping Uptime Kuma ping loop.")
            self._ping_task.cancel()
            self._ping_task = None

    def before_reload(self):
        self._stop_ping_loop()

    def after_reload(self):
        self._start_ping_loop()

    async def ping(self, message: str = "OK", status: str = "up"):
        webhook = self.config.get("webhook")
        request_params = {"status": status, "msg": message}
        self.logger.debug(f"Pinging {webhook}")
        try:
            response = await self._requests.get(
                webhook, params=request_params, timeout=5
            )
            response.raise_for_status()
            self.logger.debug("Ping succeeded.")
        except HTTPError:
            self.logger.exception("Ping failed.")

    async def _ping_loop(self):
        interval = self.config.get("interval", 30)
        self.logger.info(f"Pinging Uptime Kuma every {interval} seconds.")
        while True:
            try:
                await self.ping()
            except Exception:
                self.logger.exception("Unhandled exception in ping loop.")
            await asyncio.sleep(interval)
