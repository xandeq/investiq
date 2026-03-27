"""add_user_insights

Revision ID: 0012_add_user_insights
Revises: 0011_add_watchlist
Create Date: 2026-03-19
"""
from __future__ import annotations
import sqlalchemy as sa
from alembic import op

revision = "0012_add_user_insights"
down_revision = "0011_add_watchlist"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_insights",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),   # concentration|drop|opportunity|selic_alert
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="info"),  # info|warning|alert
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("seen", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_user_insights_tenant_seen", "user_insights", ["tenant_id", "seen"])


def downgrade() -> None:
    op.drop_table("user_insights")
