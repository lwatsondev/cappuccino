"""Add case-insensitive unique indexes

Revision ID: 14690defcb6f
Revises: e5f0a1b2c3d4
Create Date: 2026-07-23 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

revision = "14690defcb6f"
down_revision = "e5f0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_index(
        "ix_users_lower_nick", "users", [sa.text("lower(nick)")], unique=True
    )
    op.create_index(
        "ix_channels_lower_name", "channels", [sa.text("lower(name)")], unique=True
    )
    op.create_index(
        "ix_triggers_lower_name_lower_channel",
        "triggers",
        [sa.text("lower(name)"), sa.text("lower(channel)")],
        unique=True,
    )


def downgrade():
    op.drop_index("ix_triggers_lower_name_lower_channel", table_name="triggers")
    op.drop_index("ix_channels_lower_name", table_name="channels")
    op.drop_index("ix_users_lower_nick", table_name="users")
