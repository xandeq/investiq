"""add crypto to assetclass enum

Revision ID: 0035
Revises: 0034
Create Date: 2026-05-15
"""
from alembic import op

revision = "0035"
down_revision = "0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ADD VALUE requires a transaction commit first in Postgres — use COMMIT trick
    op.execute("ALTER TYPE assetclass ADD VALUE IF NOT EXISTS 'crypto'")


def downgrade() -> None:
    # PostgreSQL doesn't support removing enum values — would need a full type rebuild.
    # Safe to leave 'crypto' if rolling back other changes.
    pass
