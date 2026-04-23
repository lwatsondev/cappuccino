from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from cappuccino.db.models.userdb import RiceDB

PLUGINS = ["cappuccino.plugins.userdb", "cappuccino.plugins.seen"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_seen_records_activity(bot, db_session):
    bot.test(":seenuser!user@host PRIVMSG #channel :hello there", show=False)
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "seenuser"))
    assert row is not None
    assert isinstance(row.last_seen, datetime)
    assert row.last_seen.tzinfo is not None
    assert row.last_seen <= datetime.now(UTC)


def test_seen_unknown_user(bot, db_session):
    bot.test(
        f":nick!user@host PRIVMSG #channel :{bot.config.cmd}seen unseennick", show=False
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "unseennick"))
    assert row is None
    assert any("haven't seen" in line for line in bot.sent)


def test_seen_known_user(bot):
    bot.test(":knownuser!user@host PRIVMSG #channel :hello there", show=False)
    bot.test(
        f":querynick!user@host PRIVMSG #channel :{bot.config.cmd}seen knownuser",
        show=False,
    )
    assert any("knownuser" in line and "last seen" in line for line in bot.sent)
