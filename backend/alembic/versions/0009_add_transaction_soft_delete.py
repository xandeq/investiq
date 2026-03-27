"""add_transaction_soft_delete

Revision ID: 0009_add_transaction_soft_delete
Revises: 0008_add_app_logs
Create Date: 2026-03-18

Adds deleted_at column to transactions for soft delete support.
Active rows have deleted_at IS NULL; deleted rows have a timestamp.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0009_add_transaction_soft_delete"
down_revision = "0008_add_app_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "deleted_at")
