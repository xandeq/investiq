"""Performance indexes: signal_outcomes, sentiment_snapshots, users telegram.

Revision ID: 0041
Revises: 0040
Create Date: 2026-05-22

Adds missing indexes found in post-audit:
  1. signal_outcomes(tenant_id, pattern) — composite for RLS + hourly calibration GROUP BY
  2. sentiment_snapshots(source, created_at) — filter by source in aggregation queries
  3. users(telegram_chat_id) where not null — notification lookup by chat_id
"""
from __future__ import annotations

from alembic import op

revision = "0041"
down_revision = "0040"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index for calibration query: GROUP BY pattern WHERE tenant_id = $1
    op.create_index(
        "ix_signal_outcomes_tenant_pattern",
        "signal_outcomes",
        ["tenant_id", "pattern"],
        unique=False,
    )

    # Source + created_at for sentiment aggregation filtering
    op.create_index(
        "ix_sentiment_snapshots_source_ts",
        "sentiment_snapshots",
        ["source", "created_at"],
        unique=False,
        postgresql_ops={"created_at": "DESC"},
    )

    # Telegram chat_id lookup — partial index (only rows with a value)
    op.execute(
        "CREATE INDEX ix_users_telegram_chat_id "
        "ON users (telegram_chat_id) "
        "WHERE telegram_chat_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_users_telegram_chat_id")
    op.drop_index("ix_sentiment_snapshots_source_ts", table_name="sentiment_snapshots")
    op.drop_index("ix_signal_outcomes_tenant_pattern", table_name="signal_outcomes")
