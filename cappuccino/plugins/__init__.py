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

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from niquests import AsyncSession

from cappuccino.settings import settings
from cappuccino.util import meta

if TYPE_CHECKING:
    from cappuccino.bot import Bot


class Plugin:
    def __init__(self, bot: Bot):
        plugin_module = self.__class__.__module__
        self.bot = bot
        self._plugin_name = plugin_module.split(".")[-1]
        self.logger = logging.getLogger(f"irc3.{plugin_module}")
        self._http: AsyncSession = AsyncSession(
            timeout=5,
            headers={"User-Agent": f"cappuccino/{meta.VERSION} (+{meta.SOURCE})"},
        )

        if self.config:
            self.logger.debug(f"Configuration for {plugin_module}: {self.config}")

    @property
    def config(self) -> dict:
        plugins = settings.get("PLUGINS") or {}
        return getattr(plugins, self._plugin_name, {})
