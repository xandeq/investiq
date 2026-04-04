"""add_fii_score_columns

Revision ID: 0021_add_fii_score_columns
Revises: 0020_add_analysis_tables
Create Date: 2026-04-04

Adds pre-calculated score columns to fii_metadata table for Phase 17
FII Scored Screener. Scores are computed nightly by the calculate_fii_scores
Celery task using percentile-based composite formula:
  score = DY_rank*0.5 + PVP_rank_inverted*0.3 + liquidity_rank*0.2
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_add_fii_score_columns"
down_revision = "0020_add_analysis_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fii_metadata", sa.Column("dy_12m", sa.Numeric(10, 6), nullable=True))
    op.add_column("fii_metadata", sa.Column("pvp", sa.Numeric(10, 4), nullable=True))
    op.add_column("fii_metadata", sa.Column("daily_liquidity", sa.BigInteger, nullable=True))
    op.add_column("fii_metadata", sa.Column("score", sa.Numeric(8, 4), nullable=True))
    op.add_column("fii_metadata", sa.Column("dy_rank", sa.Integer, nullable=True))
    op.add_column("fii_metadata", sa.Column("pvp_rank", sa.Integer, nullable=True))
    op.add_column("fii_metadata", sa.Column("liquidity_rank", sa.Integer, nullable=True))
    op.add_column("fii_metadata", sa.Column("score_updated_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("fii_metadata", "score_updated_at")
    op.drop_column("fii_metadata", "liquidity_rank")
    op.drop_column("fii_metadata", "pvp_rank")
    op.drop_column("fii_metadata", "dy_rank")
    op.drop_column("fii_metadata", "score")
    op.drop_column("fii_metadata", "daily_liquidity")
    op.drop_column("fii_metadata", "pvp")
    op.drop_column("fii_metadata", "dy_12m")
