from alembic import command
from sqlalchemy import create_engine, inspect


def test_migrations(alembic_cfg, migration_db_url):
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(migration_db_url)
    indexes = {
        table: {idx["name"] for idx in inspect(engine).get_indexes(table)}
        for table in ("users", "channels", "triggers")
    }
    engine.dispose()

    assert "ix_users_lower_nick" in indexes["users"]
    assert "ix_channels_lower_name" in indexes["channels"]
    assert "ix_triggers_lower_name_lower_channel" in indexes["triggers"]

    command.downgrade(alembic_cfg, "-1")

    engine = create_engine(migration_db_url)
    indexes_after_downgrade = {
        table: {idx["name"] for idx in inspect(engine).get_indexes(table)}
        for table in ("users", "channels", "triggers")
    }
    engine.dispose()

    assert "ix_users_lower_nick" not in indexes_after_downgrade["users"]
    assert "ix_channels_lower_name" not in indexes_after_downgrade["channels"]
    assert (
        "ix_triggers_lower_name_lower_channel"
        not in indexes_after_downgrade["triggers"]
    )

    command.upgrade(alembic_cfg, "head")
    command.downgrade(alembic_cfg, "base")
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(migration_db_url)
    tables = inspect(engine).get_table_names()
    engine.dispose()

    assert "ai_corpus" in tables
    assert "triggers" in tables
    assert "users" in tables
    assert "channels" in tables
