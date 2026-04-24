from alembic import command
from sqlalchemy import create_engine, inspect


def test_migrations(alembic_cfg, migration_db_url):
    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(migration_db_url)
    tables = inspect(engine).get_table_names()
    engine.dispose()

    assert "ai_channels" in tables
    assert "ai_corpus" in tables
    assert "triggers" in tables
    assert "ricedb" in tables
