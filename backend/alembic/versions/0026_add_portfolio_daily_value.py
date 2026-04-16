"""add_portfolio_daily_value

Revision ID: 0026_add_portfolio_daily_value
Revises: 0025_add_watchlist_alert_triggered_at
Create Date: 2026-04-15

Creates portfolio_daily_value table to store EOD portfolio value snapshots
per tenant per day. Populated by Celery task at 18h30 BRT (after B3 close).

Used by GET /dashboard/portfolio-history to power the historical performance
chart on the portfolio page with benchmark comparison (CDI, IBOVESPA).
"""
from alembic import op
import sqlalchemy as sa

revision = "0026_add_portfolio_daily_value"
down_revision = "0025_add_watchlist_alert_triggered_at"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_daily_value",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("total_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("total_invested", sa.Numeric(18, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    # Unique constraint: one snapshot per tenant per day
    op.create_unique_constraint(
        "uq_portfolio_daily_tenant_date",
        "portfolio_daily_value",
        ["tenant_id", "snapshot_date"],
    )
    # Composite index for range queries: tenant_id + date range
    op.create_index(
        "ix_portfolio_daily_tenant_date",
        "portfolio_daily_value",
        ["tenant_id", "snapshot_date"],
    )


def downgrade() -> None:
    op.drop_table("portfolio_daily_value")
