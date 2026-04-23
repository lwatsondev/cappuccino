from unittest.mock import patch

import pytest
from sqlalchemy import select

from cappuccino.db.models.triggers import Trigger

PLUGINS = ["cappuccino.plugins.triggers"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_trigger_set(bot, db_session):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger set hello world",
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


def test_trigger_set_not_chanop(bot):
    bot.test(
        f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger set hello world",
        show=False,
    )
    assert any("channel operators" in line for line in bot.sent)


def test_trigger_delete(bot, db_session):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger set deltrigger goodbye",
            show=False,
        )
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger del deltrigger",
            show=False,
        )
    row = db_session.scalar(
        select(Trigger)
        .where(Trigger.name == "deltrigger")
        .where(Trigger.channel == "#channel")
    )
    assert row is None
    assert any("Deleted trigger" in line for line in bot.sent)


def test_trigger_list(bot):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger set listtrigger a response",
            show=False,
        )
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger list",
            show=False,
        )
    assert any("listtrigger" in line for line in bot.sent)


def test_trigger_response(bot, db_session):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger set greet Hello there!",
            show=False,
        )
    bot.test(":otheruser!user@host PRIVMSG #channel :?greet", show=False)
    row = db_session.scalar(
        select(Trigger)
        .where(Trigger.name == "greet")
        .where(Trigger.channel == "#channel")
    )
    assert row.response == "Hello there!"
    assert any("Hello there!" in line for line in bot.sent)


def test_trigger_response_inline(bot):
    with patch("cappuccino.plugins.triggers.is_chanop", return_value=True):
        bot.test(
            f":nick!user@host PRIVMSG #channel :{bot.config.cmd}trigger set inline Inline response!",
            show=False,
        )
    bot.test(
        ":otheruser!user@host PRIVMSG #channel :hey can someone explain ?inline to me?",
        show=False,
    )
    assert any("Inline response!" in line for line in bot.sent)
