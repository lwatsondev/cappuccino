from unittest.mock import patch

import pytest
from sqlalchemy import select

from cappuccino.db.models.triggers import Trigger

PLUGINS = ["cappuccino.plugins.triggers"]


@pytest.fixture
def bot(make_bot):
    bot = make_bot(PLUGINS)
    bot.test(f":{bot.nick}!{bot.nick}@host JOIN :#channel", show=False)
    return bot


def test_set(bot, db_session):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger set hello world",
            show=False,
        )
    row = db_session.scalar(
        select(Trigger)
        .where(Trigger.name == "hello")
        .where(Trigger.channel == "#channel")
    )
    assert row is not None
    assert row.response == "world"
    assert any("Trigger 'hello' set." in line for line in bot.sent)


def test_delete(bot, db_session):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger set deltrigger goodbye",
            show=False,
        )
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger del deltrigger",
            show=False,
        )
    row = db_session.scalar(
        select(Trigger)
        .where(Trigger.name == "deltrigger")
        .where(Trigger.channel == "#channel")
    )
    assert row is None
    assert any("Deleted trigger 'deltrigger'." in line for line in bot.sent)


def test_list(bot):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger set listtrigger a response",
            show=False,
        )
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger set listtrigger2 another response",
            show=False,
        )
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger list",
            show=False,
        )
    assert any("listtrigger" in line and "listtrigger2" in line for line in bot.sent)


def test_response(bot, db_session):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger set greet Hello there!",
            show=False,
        )
    row = db_session.scalar(
        select(Trigger)
        .where(Trigger.name == "greet")
        .where(Trigger.channel == "#channel")
    )
    assert row.response == "Hello there!"
    bot.test(":otheruser!user@host PRIVMSG #channel :?greet", show=False)
    assert any("Hello there!" in line for line in bot.sent)


def test_response_inline(bot):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            ":nick!user@host PRIVMSG #channel :!trigger set inline Inline response!",
            show=False,
        )
    bot.test(
        ":otheruser!user@host PRIVMSG #channel :hey can someone explain ?inline to me?",
        show=False,
    )
    assert any("Inline response!" in line for line in bot.sent)
