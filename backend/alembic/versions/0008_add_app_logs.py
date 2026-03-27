"""add_app_logs

Revision ID: 0008_add_app_logs
Revises: 0007_add_stripe_events
Create Date: 2026-03-18

Centralized application logs table for admin monitoring.
No RLS — admin-only table not scoped by tenant.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0008_add_app_logs"
down_revision = "0007_add_stripe_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "app_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("level", sa.String(10), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("traceback", sa.Text, nullable=True),
        sa.Column("module", sa.String(255), nullable=True),
        sa.Column("request_path", sa.String(500), nullable=True),
        sa.Column("request_method", sa.String(10), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("extra", sa.JSON, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_app_logs_level", "app_logs", ["level"])
    op.create_index("ix_app_logs_created_at", "app_logs", ["created_at"])

    # Grant access to app_user (used by the application)
    op.execute("GRANT SELECT, INSERT, DELETE ON app_logs TO app_user")


def downgrade() -> None:
    op.drop_index("ix_app_logs_created_at", table_name="app_logs")
    op.drop_index("ix_app_logs_level", table_name="app_logs")
    op.drop_table("app_logs")
