"""add_variacao_12m_pct

Revision ID: 0024_add_variacao_12m_pct
Revises: 0023_add_swing_trade_operations
Create Date: 2026-04-12

Adds variacao_12m_pct column to screener_snapshots table.
This stores the 52-week price change percentage extracted from brapi.dev
defaultKeyStatistics.52WeekChange. Required by SCRA-01 (Screener de Ações
Var. 12m% column).
"""
from alembic import op
import sqlalchemy as sa

revision = "0024_add_variacao_12m_pct"
down_revision = "0023_add_swing_trade_operations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "screener_snapshots",
        sa.Column("variacao_12m_pct", sa.Numeric(10, 6), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("screener_snapshots", "variacao_12m_pct")
