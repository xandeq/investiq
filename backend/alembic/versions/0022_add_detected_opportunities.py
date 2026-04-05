"""add_detected_opportunities

Revision ID: 0022_add_detected_opportunities
Revises: 0021_add_fii_score_columns
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_add_detected_opportunities"
down_revision = "0021_add_fii_score_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "detected_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("drop_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("current_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("is_opportunity", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cause_category", sa.String(50), nullable=True),
        sa.Column("cause_explanation", sa.Text, nullable=True),
        sa.Column("risk_rationale", sa.Text, nullable=True),
        sa.Column("recommended_amount_brl", sa.Numeric(12, 2), nullable=True),
        sa.Column("target_upside_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("telegram_message", sa.Text, nullable=True),
        sa.Column("followed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_detected_opportunities_ticker", "detected_opportunities", ["ticker"]
    )
    op.create_index(
        "ix_detected_opportunities_asset_type", "detected_opportunities", ["asset_type"]
    )
    op.create_index(
        "ix_detected_opportunities_detected_at", "detected_opportunities", ["detected_at"]
    )


def downgrade() -> None:
    op.drop_table("detected_opportunities")
