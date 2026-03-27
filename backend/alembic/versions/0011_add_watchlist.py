"""add_watchlist

Revision ID: 0011_add_watchlist
Revises: 0010_add_investor_profile
Create Date: 2026-03-18

Adds watchlist_items table for user-tracked assets.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0011_add_watchlist"
down_revision = "0010_add_investor_profile"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("notes", sa.String(300), nullable=True),
        sa.Column("price_alert_target", sa.Numeric(18, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", "ticker", name="uq_watchlist_tenant_ticker"),
    )


def downgrade() -> None:
    op.drop_table("watchlist_items")
