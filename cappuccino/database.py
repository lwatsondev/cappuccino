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

import os
from typing import Any

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.orm import sessionmaker

from cappuccino.db.models.ircdb import Channel, User


class IrcDatabase:
    def __init__(self, config: dict):
        engine = create_engine(
            config.get("uri"),
            pool_size=config.get("pool_size", os.cpu_count()),
            max_overflow=config.get("max_overflow", os.cpu_count()),
        )
        self.session = sessionmaker(engine)

    def get_user_value(self, nick: str, key: str):
        with self.session() as session:
            return session.scalar(
                select(User.__table__.columns[key]).where(
                    func.lower(User.nick) == nick.lower()
                )
            )

    def del_user_value(self, nick: str, key: str):
        self.set_user_value(nick, key, None)

    def set_user_value(self, nick: str, key: str, value: Any = None):
        with self.session.begin() as session:
            user = session.scalar(
                update(User)
                .returning(User)
                .where(func.lower(User.nick) == nick.lower())
                .values({key: value})
            )
            if user is None:
                user = User(nick=nick, **{key: value})
                session.add(user)

    def get_channel_value(self, channel: str, key: str):
        with self.session() as session:
            return session.scalar(
                select(Channel.__table__.columns[key]).where(
                    func.lower(Channel.name) == channel.lower()
                )
            )

    def del_channel_value(self, channel: str, key: str):
        self.set_channel_value(channel, key, None)

    def set_channel_value(self, channel: str, key: str, value: Any = None):
        with self.session.begin() as session:
            row = session.scalar(
                update(Channel)
                .returning(Channel)
                .where(func.lower(Channel.name) == channel.lower())
                .values({key: value})
            )
            if row is None:
                row = Channel(name=channel, **{key: value})
                session.add(row)
