"""Rename ricedb table to users

Revision ID: e3f1a2b4c5d6
Revises: 15a2d5ea1971
Create Date: 2026-05-13 00:00:00.000000

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "e3f1a2b4c5d6"
down_revision = "15a2d5ea1971"
branch_labels = None
depends_on = None


def upgrade():
    op.rename_table("ricedb", "users")


def downgrade():
    op.rename_table("users", "ricedb")
