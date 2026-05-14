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

from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from irc3 import IrcBot


class ChannelMode(Enum):
    VOICE = "+"
    HALF_OP = "%"
    OP = "@"
    SUPER_OP = "&"
    OWNER = "~"


def is_channel(name: str) -> bool:
    return name.startswith(("#", "&"))


def is_server(name: str) -> bool:
    return "." in name and "!" not in name


def is_user(name: str) -> bool:
    return "!" in name


def is_chanop(bot: IrcBot, channel: str, nick: str) -> bool:
    """Checks whether a user is a chanop (has mode +h or above)."""
    for mode in ChannelMode:
        # Voiced users aren't channel operators.
        if mode is ChannelMode.VOICE:
            continue

        try:
            if nick in bot.channels[channel].modes[mode.value]:
                return True
        except KeyError, AttributeError:
            continue

    return False
