"""add_analysis_tables

Revision ID: 0020_add_analysis_tables
Revises: 0019_add_ai_usage_logs
Create Date: 2026-03-31

Creates three tables for the AI Analysis module (Phase 12):
- analysis_jobs: Async analysis job tracking
- analysis_quota_logs: Per-tenant monthly quota enforcement
- analysis_cost_logs: Per-analysis LLM cost tracking
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_add_analysis_tables"
down_revision = "0019_add_ai_usage_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- analysis_jobs ---
    op.create_table(
        "analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("data_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_version_id", sa.String(100), nullable=False),
        sa.Column("data_sources", sa.Text, nullable=True),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_analysis_jobs_tenant_status",
        "analysis_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_analysis_jobs_tenant_ticker",
        "analysis_jobs",
        ["tenant_id", "ticker"],
    )
    op.create_index(
        "ix_analysis_jobs_created",
        "analysis_jobs",
        ["created_at"],
    )
    op.create_index(
        "ix_analysis_jobs_data_version",
        "analysis_jobs",
        ["data_version_id"],
    )

    # --- analysis_quota_logs ---
    op.create_table(
        "analysis_quota_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("year_month", sa.String(7), nullable=False),
        sa.Column("plan_tier", sa.String(20), nullable=False),
        sa.Column("quota_limit", sa.Integer, nullable=False),
        sa.Column("quota_used", sa.Integer, nullable=False, server_default="0"),
    )
    op.create_index(
        "ix_quota_tenant_month",
        "analysis_quota_logs",
        ["tenant_id", "year_month"],
        unique=True,
    )

    # --- analysis_cost_logs ---
    op.create_table(
        "analysis_cost_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("analysis_type", sa.String(50), nullable=False),
        sa.Column("ticker", sa.String(10), nullable=False),
        sa.Column("llm_provider", sa.String(50), nullable=True),
        sa.Column("llm_model", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer, nullable=True),
        sa.Column("output_tokens", sa.Integer, nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(10, 4), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_cost_tenant_created",
        "analysis_cost_logs",
        ["tenant_id", "created_at"],
    )
    op.create_index(
        "ix_cost_analysis_type",
        "analysis_cost_logs",
        ["analysis_type"],
    )


def downgrade() -> None:
    op.drop_table("analysis_cost_logs")
    op.drop_table("analysis_quota_logs")
    op.drop_table("analysis_jobs")
