"""add_watchlist_alert_triggered_at

Revision ID: 0025_add_watchlist_alert_triggered_at
Revises: 0024_add_variacao_12m_pct
Create Date: 2026-04-15

Adds alert_triggered_at to watchlist_items so the Celery price-alert task
can record when it last fired an alert for a (tenant, ticker) pair.
Frontend uses this to display "Alerta disparado em DD/MM HH:MM" badge.
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_add_watchlist_alert_triggered_at"
down_revision = "0024_add_variacao_12m_pct"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "watchlist_items",
        sa.Column("alert_triggered_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("watchlist_items", "alert_triggered_at")
