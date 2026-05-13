"""Migrate ai_channels into channels and repoint ai_corpus FK

Revision ID: d4e9f1a2b3c4
Revises: 38e47afd4586
Create Date: 2026-05-13 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "d4e9f1a2b3c4"
down_revision = "38e47afd4586"
branch_labels = None
depends_on = None

_ai_channels = sa.table(
    "ai_channels",
    sa.column("name", sa.Text),
    sa.column("enabled", sa.Boolean),
)

_ai_corpus = sa.table("ai_corpus", sa.column("channel_name", sa.Text))

_channels = sa.table(
    "channels",
    sa.column("name", sa.Text),
    sa.column("ai_enabled", sa.Boolean),
)


def upgrade():
    conn = op.get_bind()
    rows = conn.execute(sa.select(_ai_channels)).all()
    if rows:
        conn.execute(
            sa.insert(_channels),
            [{"name": row.name, "ai_enabled": row.enabled} for row in rows],
        )

    existing_names = {
        row.name for row in conn.execute(sa.select(_channels.c.name)).all()
    }
    corpus_channels = {
        row.channel_name
        for row in conn.execute(sa.select(_ai_corpus.c.channel_name)).all()
    }
    orphaned = [
        {"name": channel_name}
        for channel_name in corpus_channels
        if channel_name not in existing_names
    ]
    if orphaned:
        conn.execute(sa.insert(_channels), orphaned)

    op.drop_constraint("fk_ai_corpus.channel_name", "ai_corpus", type_="foreignkey")
    op.create_foreign_key(
        "fk_ai_corpus.channel_name",
        "ai_corpus",
        "channels",
        ["channel_name"],
        ["name"],
    )

    op.drop_table("ai_channels")


def downgrade():
    op.create_table(
        "ai_channels",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.PrimaryKeyConstraint("name"),
    )

    conn = op.get_bind()
    rows = conn.execute(sa.select(_channels)).all()
    if rows:
        conn.execute(
            sa.insert(_ai_channels),
            [{"name": row.name, "enabled": row.ai_enabled} for row in rows],
        )

    op.drop_constraint("fk_ai_corpus.channel_name", "ai_corpus", type_="foreignkey")
    op.create_foreign_key(
        "fk_ai_corpus.channel_name",
        "ai_corpus",
        "ai_channels",
        ["channel_name"],
        ["name"],
    )
