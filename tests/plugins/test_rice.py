import pytest
from sqlalchemy import select

from cappuccino.db.models.userdb import RiceDB

PLUGINS = ["cappuccino.plugins.userdb", "cappuccino.plugins.rice"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_add(bot, db_session):
    bot.test(
        ":nick!user@host PRIVMSG #channel :!dtop --add https://test.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "nick"))
    assert row.dtops == ["https://test.local"]


def test_set(bot, db_session):
    bot.test(
        ":setuser!user@host PRIVMSG #channel :!dtop --set https://test.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "setuser"))
    assert row.dtops == ["https://test.local"]


def test_delete(bot, db_session):
    bot.test(
        ":deleteuser!user@host PRIVMSG #channel :!dtop --set https://test.local",
        show=False,
    )
    bot.test(
        ":deleteuser!user@host PRIVMSG #channel :!dtop --delete 1",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "deleteuser"))
    assert row.dtops == []


def test_show(bot, db_session):
    bot.test(
        ":targetuser!user@host PRIVMSG #channel :!dtop --set https://target.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "targetuser"))
    assert row.dtops == ["https://target.local"]

    bot.test(
        ":queryuser!user@host PRIVMSG #channel :!dtop targetuser",
        show=False,
    )
    assert any("https://target.local" in line for line in bot.sent)


def test_delete_by_index_multiple(bot, db_session):
    bot.test(
        ":multiuser!user@host PRIVMSG #channel :!dtop --set"
        " https://a.local https://b.local https://c.local",
        show=False,
    )
    bot.test(
        ":multiuser!user@host PRIVMSG #channel :!dtop --delete 2",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "multiuser"))
    assert row.dtops == ["https://a.local", "https://c.local"]


def test_delete_wildcard(bot, db_session):
    bot.test(
        ":wildcarduser!user@host PRIVMSG #channel :!dtop --set"
        " https://a.local https://b.local",
        show=False,
    )
    bot.test(
        ":wildcarduser!user@host PRIVMSG #channel :!dtop --delete *",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "wildcarduser"))
    assert row.dtops is None


def test_replace(bot, db_session):
    bot.test(
        ":replaceuser!user@host PRIVMSG #channel :!dtop --set https://original.local",
        show=False,
    )
    bot.test(
        ":replaceuser!user@host PRIVMSG #channel :!dtop --replace 1 https://replaced.local",
        show=False,
    )
    row = db_session.scalar(select(RiceDB).where(RiceDB.nick == "replaceuser"))
    assert row.dtops == ["https://replaced.local"]
