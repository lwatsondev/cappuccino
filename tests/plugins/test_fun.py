from unittest.mock import patch

import pytest

PLUGINS = ["cappuccino.plugins.fun"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_decide_or_delimiter(bot):
    bot.test(
        ":nick!user@host PRIVMSG #channel :!decide cats or dogs",
        show=False,
    )
    assert any(
        ("cats" in line or "dogs" in line) and "nick" in line for line in bot.sent
    )


def test_decide_pipe_delimiter(bot):
    bot.test(
        ":nick!user@host PRIVMSG #channel :!decide cats|dogs|fish",
        show=False,
    )
    assert any(
        ("cats" in line or "dogs" in line or "fish" in line) and "nick" in line
        for line in bot.sent
    )


def test_decide_comma_delimiter(bot):
    bot.test(
        ":nick!user@host PRIVMSG #channel :!decide cats, dogs",
        show=False,
    )
    assert any(
        ("cats" in line or "dogs" in line) and "nick" in line for line in bot.sent
    )


def test_decide_single_option_fallback(bot):
    bot.test(
        ":nick!user@host PRIVMSG #channel :!decide onlyone",
        show=False,
    )
    assert any(
        ("Yes." in line or "Maybe." in line or "No." in line) for line in bot.sent
    )


def test_does_anybody_else(bot):
    bot.test(":nick!user@host PRIVMSG #channel :does anybody else do this?", show=False)
    assert any(
        "No, you are literally the only one in the world." in line for line in bot.sent
    )


def test_does_anyone_else(bot):
    bot.test(
        ":nick!user@host PRIVMSG #channel :does anyone else feel this way?", show=False
    )
    assert any(
        "No, you are literally the only one in the world." in line for line in bot.sent
    )


def test_am_i_the_only_one(bot):
    bot.test(
        ":nick!user@host PRIVMSG #channel :am i the only one who does this?", show=False
    )
    assert any("Statistically, probably not." in line for line in bot.sent)


def test_intensify(bot):
    bot.test(":nick!user@host PRIVMSG #channel :[thing]", show=False)
    assert any("[THING INTENSIFIES]" in line for line in bot.sent)


def test_intensify_already_has_intensifies(bot):
    bot.test(":nick!user@host PRIVMSG #channel :[thing intensifies]", show=False)
    assert any("[THING INTENSIFIES]" in line for line in bot.sent)


def test_intensify_too_long(bot):
    bot.test(f":nick!user@host PRIVMSG #channel :[{'a' * 33}]", show=False)
    assert not bot.sent


@pytest.mark.parametrize(
    "message",
    [
        "sup",
        "hey 'sup guys?",
        "so what's up with that?",
        "whats up everyone",
        "yo wassup dude",
        "wazzup fellas",
    ],
)
def test_gravity(bot, message):
    with patch("cappuccino.plugins.fun.random.random", return_value=0.0):
        bot.test(f":nick!user@host PRIVMSG #channel :{message}", show=False)
    assert any(
        '"Up" is a direction away from the center of gravity of a celestial object.'
        in line
        for line in bot.sent
    )
