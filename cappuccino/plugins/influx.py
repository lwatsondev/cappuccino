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

from datetime import UTC, datetime

import irc3
from influxdb_client import InfluxDBClient, Point
from irc3 import rfc

from cappuccino.plugins import Plugin
from cappuccino.util.irc import is_channel, is_server, is_user


@irc3.plugin
class Influx(Plugin):
    requires = ["irc3.plugins.userlist"]

    def __init__(self, bot):
        super().__init__(bot)
        self._influx_client: InfluxDBClient | None = None
        self._influx_config_key: tuple | None = None

    def after_reload(self):
        self._influx_client = None
        self._influx_config_key = None

    @property
    def _client(self) -> InfluxDBClient | None:
        url = self.config.get("url")
        org = self.config.get("org")
        bucket = self.config.get("bucket")
        token = self.config.get("token")
        config_key = (url, org, bucket, token)
        if not all(config_key):
            self.logger.error("InfluxDB requires *all* config keys to be set.")
            return None
        if config_key != self._influx_config_key:
            self._influx_client = InfluxDBClient(url=url, token=token, org=org)
            self._influx_config_key = config_key
        return self._influx_client

    def _record_event(
        self,
        event: str,
        data: str | None = None,
        user: str | None = None,
        channel: str | None = None,
        target: str | None = None,
    ):
        if not channel or not is_channel(channel) or not user or is_server(user):
            return

        if is_user(user):
            user = user.split("!", 1)[0]

        data = data.replace("\x00", "") if data else ""

        client = self._client
        if not client:
            return

        with client.write_api() as write_api:
            point = (
                Point("channel_activity")
                .tag("channel", channel)
                .tag("target", target)
                .tag("user", user)
                .tag("event", event)
                .field("data", data or "")
                .time(datetime.now(UTC))
            )
            write_api.write(
                bucket=self.config.get("bucket"),
                org=self.config.get("org"),
                record=point,
            )

    def _record_user_count(self, channel):
        client = self._client
        if not client:
            return

        with client.write_api() as write_api:
            point = (
                Point("channel_members")
                .tag("channel", channel)
                .field("user_count", len(self.bot.channels.get(channel)))
                .time(datetime.now(UTC))
            )
            write_api.write(
                bucket=self.config.get("bucket"),
                org=self.config.get("org"),
                record=point,
            )

    @irc3.event(rfc.PRIVMSG)
    @irc3.event(rfc.PRIVMSG, iotype="out")
    def on_privmsg(self, mask=None, event=None, target=None, data=None):
        if event == "NOTICE" or data.startswith("\x01VERSION") or not target.is_channel:
            return

        self._record_event(event, user=mask, data=data, channel=target)

    @irc3.event(rfc.JOIN_PART_QUIT)
    @irc3.event(rfc.JOIN_PART_QUIT, iotype="out")
    def on_join_part_quit(self, mask=None, event=None, channel=None, data=None):
        self._record_event(event, user=mask, data=data, channel=channel)
        if event in ("QUIT", "PART") and mask.nick == self.bot.nick:
            return
        self._record_user_count(channel)

    @irc3.event(rfc.KICK)
    @irc3.event(rfc.KICK, iotype="out")
    def on_kick(self, mask=None, event=None, channel=None, target=None, data=None):
        if data == mask:
            data = None

        self._record_event(event, data=data, user=mask, channel=channel, target=target)
        self._record_user_count(channel)

    def on_kick_out(self, *args, **kwargs):
        yield self.on_kick(*args, **kwargs)

    @irc3.event(rfc.TOPIC)
    @irc3.event(rfc.TOPIC, iotype="out")
    def on_topic(self, mask=None, channel=None, data=None):
        if not mask:
            mask = self.bot.nick

        self._record_event("TOPIC", user=mask, data=data, channel=channel)

    def on_topic_out(self, *args, **kwargs):
        yield self.on_topic(*args, **kwargs)

    @irc3.event(rfc.MODE)
    @irc3.event(rfc.MODE, iotype="out")
    def on_mode(self, mask=None, event=None, target=None, modes=None, data=None):
        self._record_event(event, data=modes, user=mask, channel=target, target=data)

    def on_mode_out(self, *args, **kwargs):
        yield self.on_mode(*args, **kwargs)

    @irc3.event(rfc.RPL_NAMREPLY)
    def names(self, channel=None, data=None, **kwargs):
        self._record_user_count(channel)
