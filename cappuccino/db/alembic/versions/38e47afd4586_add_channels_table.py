"""Add channels table

Revision ID: 38e47afd4586
Revises: e3f1a2b4c5d6
Create Date: 2026-05-13 00:00:00.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "38e47afd4586"
down_revision = "e3f1a2b4c5d6"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "channels",
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column(
            "ai_enabled", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.PrimaryKeyConstraint("name"),
    )


def downgrade():
    op.drop_table("channels")
