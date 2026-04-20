"""add_unique_active_subscription_constraint

Revision ID: 0028_add_unique_active_subscription_constraint
Revises: 0027_add_email_preferences
Create Date: 2026-04-18

Enforce v1 design invariant at the database level: only one active or
trialing subscription per user at a time.

Uses a PostgreSQL partial unique constraint so canceled subscriptions
(which are kept for audit) are not included in the uniqueness check.
This is a backward-compatible, zero-downtime migration.
"""
from __future__ import annotations

from alembic import op


revision = "0028_add_unique_active_subscription_constraint"
down_revision = "0027_add_email_preferences"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS uq_user_one_active_subscription
        ON subscriptions (user_id)
        WHERE status IN ('active', 'trialing');
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_user_one_active_subscription;")
