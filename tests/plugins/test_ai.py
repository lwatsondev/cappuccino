import pytest
from sqlalchemy import select

from cappuccino.db.models.ai import CorpusLine
from cappuccino.plugins.ai import _should_ignore_message

PLUGINS = ["cappuccino.plugins.ai"]


@pytest.fixture
def bot(make_bot):
    return make_bot(PLUGINS)


def test_corpus_line_stored(bot, db_session):
    bot.test(":nick!user@host PRIVMSG #channel :hello there corpus", show=False)
    row = db_session.scalar(
        select(CorpusLine).where(CorpusLine.line == "hello there corpus")
    )
    assert row is not None


@pytest.mark.parametrize(
    "message",
    [
        "https://corpustest.local",
        "!notacommand999",
        "s/foo/bar/",
        "[thing intensifies]",
        "\x01ACTION does something",
    ],
)
def test_not_stored_in_corpus(bot, db_session, message):
    assert _should_ignore_message(message)
    bot.test(f":nick!user@host PRIVMSG #channel :{message}", show=False)
    row = db_session.scalar(select(CorpusLine).where(CorpusLine.line == message))
    assert row is None
