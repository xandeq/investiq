"""add news_events table

Revision ID: 0034
Revises: 0033
Create Date: 2026-05-04
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision = "0034"
down_revision = "0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("headline", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=True),
        sa.Column("tickers", ARRAY(sa.Text), nullable=False, server_default="{}"),
        sa.Column("sentiment", sa.Numeric(4, 3), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("indexed_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source", "url", name="uq_news_events_source_url"),
    )
    op.create_index(
        "ix_news_events_tickers",
        "news_events",
        ["tickers"],
        postgresql_using="gin",
    )
    op.create_index(
        "ix_news_events_published",
        "news_events",
        [sa.text("published_at DESC")],
    )


def downgrade() -> None:
    op.drop_index("ix_news_events_published", table_name="news_events")
    op.drop_index("ix_news_events_tickers", table_name="news_events")
    op.drop_table("news_events")
