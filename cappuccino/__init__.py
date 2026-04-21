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

import logging
import os
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

if TYPE_CHECKING:
    from irc3 import IrcBot


class Plugin:
    def __init__(self, bot: IrcBot):
        plugin_module = self.__class__.__module__
        self.bot = bot
        self.config: dict = self.bot.config.get(plugin_module, {})
        self.logger = logging.getLogger(f"irc3.{plugin_module}")

        db_config = self.bot.config.get("database", {})
        db = create_engine(
            db_config.get("uri"),
            pool_size=db_config.get("pool_size", os.cpu_count()),
            max_overflow=db_config.get("max_overflow", os.cpu_count()),
        )
        self.db_session = sessionmaker(db)

        if self.config:
            # I have no idea where these are coming from but whatever.
            weird_keys = ["#", "hash"]
            for key in weird_keys:
                if key in self.config:
                    self.config.pop(key)

            self.logger.debug(f"Configuration for {plugin_module}: {self.config}")
