"""add sentiment_snapshots table

Revision ID: 0033
Revises: 0032
Create Date: 2026-05-04
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = "0033"
down_revision = "0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sentiment_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("ticker", sa.String(12), nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("score", sa.Numeric(5, 3), nullable=False),
        sa.Column("mention_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sample_posts", JSONB, nullable=True),
        sa.Column("window_hours", sa.Integer, nullable=False, server_default="24"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_sentiment_snapshots_ticker_ts",
        "sentiment_snapshots",
        ["ticker", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_sentiment_snapshots_ticker_ts", table_name="sentiment_snapshots")
    op.drop_table("sentiment_snapshots")
