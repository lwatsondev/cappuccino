import asyncio

import pytest
from alembic.config import Config as AlembicConfig
from irc3.testing import IrcBot
from pytest_postgresql.factories import postgresql_proc as postgresql_proc_factory
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from cappuccino.db.models import BaseModel
from cappuccino.db.models.ai import AIChannel, CorpusLine  # noqa: F401
from cappuccino.db.models.triggers import Trigger  # noqa: F401
from cappuccino.db.models.userdb import RiceDB  # noqa: F401

postgresql_proc = postgresql_proc_factory()


def _build_db_url(proc) -> str:
    auth = proc.user
    if proc.password:
        auth += f":{proc.password}"
    return f"postgresql+psycopg://{auth}@{proc.host}:{proc.port}/{proc.dbname}"


@pytest.fixture(scope="session")
def db(postgresql_proc):
    """Session-scoped engine with schema initialised via create_all."""
    url = _build_db_url(postgresql_proc)
    with DatabaseJanitor(
        user=postgresql_proc.user,
        host=postgresql_proc.host,
        port=postgresql_proc.port,
        dbname=postgresql_proc.dbname,
        version=postgresql_proc.version,
        password=postgresql_proc.password or None,
    ):
        engine = create_engine(url)
        BaseModel.metadata.create_all(engine)
        yield engine
        engine.dispose()


@pytest.fixture(scope="session")
def db_url(db) -> str:
    return str(db.url)


@pytest.fixture
def db_session(db):
    session_factory = sessionmaker(db)
    with session_factory() as session:
        yield session
        session.rollback()


@pytest.fixture
def migration_db_url(postgresql_proc):
    proc = postgresql_proc
    auth = proc.user + (f":{proc.password}" if proc.password else "")
    url = f"postgresql+psycopg://{auth}@{proc.host}:{proc.port}/test_migrations"

    with DatabaseJanitor(
        user=proc.user,
        host=proc.host,
        port=proc.port,
        dbname="test_migrations",
        version=proc.version,
        password=proc.password or None,
    ):
        yield url


@pytest.fixture
def alembic_cfg(migration_db_url):
    cfg = AlembicConfig("alembic.ini")
    cfg.attributes["sqlalchemy.url"] = migration_db_url
    return cfg


@pytest.fixture
def make_bot(db_url):
    """Factory that creates an irc3 test bot wired to the test database."""

    def _make(includes: list[str], **extra_config) -> IrcBot:
        asyncio.set_event_loop(asyncio.new_event_loop())
        return IrcBot(
            nick="cappuccino",
            includes=includes,
            cmd="!",
            database={"uri": db_url},
            **extra_config,
        )

    return _make
