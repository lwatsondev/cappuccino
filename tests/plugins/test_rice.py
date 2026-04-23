import pytest
from sqlalchemy import select

from cappuccino.db.models.userdb import RiceDB

PLUGINS = ["cappuccino.plugins.userdb", "cappuccino.plugins.rice"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_dtop_add(bot, db_session):
    bot.test(
        f":nick!user@host PRIVMSG #channel :{bot.config.cmd}dtop --add https://test.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "nick"))
    assert row.dtops == ["https://test.local"]


def test_dtop_set(bot, db_session):
    bot.test(
        f":setuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop --set https://test.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "setuser"))
    assert row.dtops == ["https://test.local"]


def test_dtop_delete(bot, db_session):
    bot.test(
        f":deleteuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop --set https://test.local",
        show=False,
    )
    bot.test(
        f":deleteuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop --delete 1",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "deleteuser"))
    assert row.dtops == []


def test_dtop_show(bot, db_session):
    bot.test(
        f":targetuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop --set https://target.local",
        show=False,
    )

    bot.test(
        f":queryuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop targetuser",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "targetuser"))
    assert row.dtops == ["https://target.local"]
    assert any("https://target.local" in line for line in bot.sent)


def test_dtop_replace(bot, db_session):
    bot.test(
        f":replaceuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop --set https://original.local",
        show=False,
    )
    bot.test(
        f":replaceuser!user@host PRIVMSG #channel :{bot.config.cmd}dtop --replace 1 https://replaced.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "replaceuser"))
    assert row.dtops == ["https://replaced.local"]
