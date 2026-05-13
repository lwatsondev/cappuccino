"""Add FK from triggers.channel to channels

Revision ID: e5f0a1b2c3d4
Revises: d4e9f1a2b3c4
Create Date: 2026-05-13 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "e5f0a1b2c3d4"
down_revision = "d4e9f1a2b3c4"
branch_labels = None
depends_on = None

_triggers = sa.table("triggers", sa.column("channel", sa.Text))
_channels = sa.table("channels", sa.column("name", sa.Text))


def upgrade():
    conn = op.get_bind()
    existing_names = {
        row.name for row in conn.execute(sa.select(_channels.c.name)).all()
    }
    trigger_channels = {
        row.channel for row in conn.execute(sa.select(_triggers.c.channel)).all()
    }
    new_channels = [
        {"name": channel}
        for channel in trigger_channels
        if channel not in existing_names
    ]
    if new_channels:
        conn.execute(sa.insert(_channels), new_channels)

    op.create_foreign_key(
        "fk_triggers.channel",
        "triggers",
        "channels",
        ["channel"],
        ["name"],
    )


def downgrade():
    op.drop_constraint("fk_triggers.channel", "triggers", type_="foreignkey")
