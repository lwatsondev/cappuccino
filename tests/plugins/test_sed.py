import pytest

from cappuccino.plugins.sed import EditorError, _edit, _sed_wrapper

PLUGINS = ["cappuccino.plugins.sed"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_sed_wrapper_substitution():
    assert _sed_wrapper("hello world", "s/hello/goodbye/") == "goodbye world"


def test_sed_wrapper_invalid_command():
    with pytest.raises(EditorError):
        _sed_wrapper("hello", "s/(/replacement/")


def test_edit_no_match_returns_original():
    assert _edit("hello world", "s/xyz/abc/") == "hello world"


def test_self_correction(bot):
    bot.test(":nick!user@host PRIVMSG #channel :hello world", show=False)
    bot.test(":nick!user@host PRIVMSG #channel :s/hello/goodbye/", show=False)
    assert any("goodbye world" in line for line in bot.sent)


def test_other_user_correction(bot):
    bot.test(":alice!user@host PRIVMSG #channel :i like cats", show=False)
    bot.test(":bob!user@host PRIVMSG #channel :s/cats/dogs/", show=False)
    assert any("thinks alice" in line and "dogs" in line for line in bot.sent)


def test_no_match_no_output(bot):
    bot.test(":nick!user@host PRIVMSG #channel :hello world", show=False)
    bot.test(":nick!user@host PRIVMSG #channel :s/xyz/abc/", show=False)
    assert not bot.sent


def test_no_history_no_output(bot):
    bot.test(":nick!user@host PRIVMSG #channel :s/hello/world/", show=False)
    assert not bot.sent


def test_invalid_command_sends_notice(bot):
    bot.test(":nick!user@host PRIVMSG #channel :hello world", show=False)
    bot.test(":nick!user@host PRIVMSG #channel :s/(/replacement/", show=False)
    assert any("NOTICE" in line for line in bot.sent)


def test_replacement_too_long(bot):
    bot.test(":nick!user@host PRIVMSG #channel :x", show=False)
    bot.test(f":nick!user@host PRIVMSG #channel :s/x/${'a' * 300}/", show=False)
    assert any("too long" in line for line in bot.sent)
