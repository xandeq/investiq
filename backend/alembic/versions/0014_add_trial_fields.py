"""add trial fields to users

Revision ID: 0014_add_trial_fields
Revises: 0013_add_screener_runs
Create Date: 2026-03-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0014_add_trial_fields"
down_revision = "0013_add_screener_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column(
        "trial_ends_at", sa.DateTime(timezone=True), nullable=True
    ))
    op.add_column("users", sa.Column(
        "trial_used", sa.Boolean(), nullable=False, server_default="false"
    ))
    op.add_column("users", sa.Column(
        "trial_warning_sent", sa.Boolean(), nullable=False, server_default="false"
    ))
    op.create_index("ix_users_trial_ends_at", "users", ["trial_ends_at"])


def downgrade() -> None:
    op.drop_index("ix_users_trial_ends_at", table_name="users")
    op.drop_column("users", "trial_warning_sent")
    op.drop_column("users", "trial_used")
    op.drop_column("users", "trial_ends_at")
