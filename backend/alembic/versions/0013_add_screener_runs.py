"""add screener_runs table

Revision ID: 0013_add_screener_runs
Revises: 0012_add_user_insights
Create Date: 2026-03-20
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0013_add_screener_runs"
down_revision = "0012_add_user_insights"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "screener_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("sector_filter", sa.String(100), nullable=True),
        sa.Column("custom_notes", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_screener_runs_tenant_created", "screener_runs", ["tenant_id", "created_at"])
    op.create_index("ix_screener_runs_tenant_status", "screener_runs", ["tenant_id", "status"])

    # Grant access to app_user (RLS)
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON screener_runs TO app_user")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")


def downgrade() -> None:
    op.drop_index("ix_screener_runs_tenant_status")
    op.drop_index("ix_screener_runs_tenant_created")
    op.drop_table("screener_runs")
