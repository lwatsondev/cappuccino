import asyncio
from http import HTTPStatus

import orjson
import pytest
import pytest_check as check
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from cappuccino.plugins.userdb import UserDB

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


def test_json_dump_includes_set_values(bot):
    bot.set_user_value("jsonuser", "lastfm", "scrobbler")
    bot.set_user_value("jsonuser", "dtops", ["http://dt.local/screenshot"])

    data = orjson.loads(bot.get_plugin(UserDB)._build_json())  # noqa: SLF001
    user = next(u for u in data if u["nick"] == "jsonuser")

    check.equal(user["lastfm"], "scrobbler")
    check.equal(user["dtops"], ["http://dt.local/screenshot"])


def test_json_dump_excludes_null_fields(bot):
    bot.set_user_value("nulluser", "lastfm", "scrobbler")

    data = orjson.loads(bot.get_plugin(UserDB)._build_json())  # noqa: SLF001
    user = next(u for u in data if u["nick"] == "nulluser")

    assert "dtops" not in user


def test_json_dump_last_seen_is_timestamp(bot):
    bot.set_user_value("tsuser", "lastfm", "scrobbler")

    data = orjson.loads(bot.get_plugin(UserDB)._build_json())  # noqa: SLF001
    user = next(u for u in data if u["nick"] == "tsuser")

    assert isinstance(user["last_seen"], float)


def test_http_server(bot):
    bot.set_user_value("serveruser", "lastfm", "scrobbler")
    plugin = bot.get_plugin(UserDB)

    async def _run():
        app = web.Application()
        app.router.add_get("/", plugin._json_handler)  # noqa: SLF001
        async with TestClient(TestServer(app)) as client:
            resp = await client.get("/")
            assert resp.status == HTTPStatus.OK
            assert resp.content_type == "application/json"
            data = await resp.json()
            user = next(u for u in data if u["nick"] == "serveruser")
            assert user["lastfm"] == "scrobbler"

    asyncio.run(_run())
