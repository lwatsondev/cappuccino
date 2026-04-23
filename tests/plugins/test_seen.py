from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from cappuccino.db.models.userdb import RiceDB

PLUGINS = ["cappuccino.plugins.userdb", "cappuccino.plugins.seen"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_records_activity(bot, db_session):
    bot.test(":seenuser!user@host PRIVMSG #channel :hello there", show=False)
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "seenuser"))
    assert row is not None
    assert isinstance(row.last_seen, datetime)
    assert row.last_seen.tzinfo is not None
    assert row.last_seen <= datetime.now(UTC)


def test_unknown_user(bot, db_session):
    bot.test(":nick!user@host PRIVMSG #channel :!seen unseennick", show=False)
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "unseennick"))
    assert row is None
    assert any(
        "I haven't seen any activity from unseennick yet." in line for line in bot.sent
    )


def test_known_user(bot):
    bot.test(":knownuser!user@host PRIVMSG #channel :hello there", show=False)
    bot.test(
        ":querynick!user@host PRIVMSG #channel :!seen knownuser",
        show=False,
    )
    assert any("knownuser was last seen" in line for line in bot.sent)
