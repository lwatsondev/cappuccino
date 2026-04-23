import pytest

PLUGINS = ["cappuccino.plugins.userdb"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_set_user_value(bot):
    bot.set_user_value("dbuser", "lastfm", "testaccount")
    assert bot.get_user_value("dbuser", "lastfm") == "testaccount"


def test_set_user_value_upsert(bot):
    bot.set_user_value("upsertuser", "lastfm", "original")
    bot.set_user_value("upsertuser", "lastfm", "updated")
    assert bot.get_user_value("upsertuser", "lastfm") == "updated"


def test_del_user_value(bot):
    bot.set_user_value("deluser", "lastfm", "todelete")
    bot.del_user_value("deluser", "lastfm")
    assert bot.get_user_value("deluser", "lastfm") is None


def test_get_user_value_missing(bot):
    assert bot.get_user_value("nosuchuser", "lastfm") is None
