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

import sentry_sdk
from niquests import RequestException
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from cappuccino.settings import settings
from cappuccino.util import meta

_log = logging.getLogger(__name__)


def _before_send(event, hint):
    if "exc_info" in hint:
        _, exc_value, _ = hint["exc_info"]
        if isinstance(exc_value, RequestException | TimeoutError):
            return None

    return event


def init() -> None:
    dsn = settings.get("sentry.dsn", {})
    if not dsn:
        _log.info("Missing Sentry DSN, Sentry is disabled.")
        return

    sentry_sdk.init(
        dsn,
        before_send=_before_send,
        release=meta.FULL_VERSION,
        integrations=[SqlalchemyIntegration()],
    )
