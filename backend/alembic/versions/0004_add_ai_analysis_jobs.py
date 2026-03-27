"""add_ai_analysis_jobs

Revision ID: 0004_add_ai_analysis_jobs
Revises: 0003_add_transaction_schema
Create Date: 2026-03-14 19:00:00.000000

Adds the ai_analysis_jobs table for the async AI analysis pipeline.

What this migration does:
Part A: Create table
  - ai_analysis_jobs: tracks async AI analysis requests with status, result, and error storage.

Part B: Indexes
  - ix_ai_jobs_tenant_status: composite index for filtering by tenant + status
  - ix_ai_jobs_tenant_created: composite index for listing jobs ordered by created_at

Part C: RLS policies
  - ENABLE ROW LEVEL SECURITY on ai_analysis_jobs
  - FORCE ROW LEVEL SECURITY (prevents table-owner bypass)
  - CREATE POLICY tenant_isolation using same NULLIF pattern as other tenant tables

Part D: Grants
  - GRANT SELECT, INSERT, UPDATE, DELETE on ai_analysis_jobs TO app_user

Design notes:
- result_json is TEXT (not JSONB) for maximum compatibility and simplicity.
  The Celery task serializes the result dict to JSON string before storing.
- completed_at is nullable — set when status transitions to "completed" or "failed".
- tenant_id stored directly (no FK to users) — RLS enforces isolation at the DB level.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic
revision = "0004_add_ai_analysis_jobs"
down_revision = "0003_add_transaction_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Part A: Create table
    # -------------------------------------------------------------------------
    op.create_table(
        "ai_analysis_jobs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("job_type", sa.String(20), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # -------------------------------------------------------------------------
    # Part B: Indexes
    # -------------------------------------------------------------------------
    op.create_index(
        "ix_ai_jobs_tenant_status",
        "ai_analysis_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_ai_jobs_tenant_created",
        "ai_analysis_jobs",
        ["tenant_id", "created_at"],
    )

    # -------------------------------------------------------------------------
    # Part C: RLS policies (written manually — autogenerate cannot detect RLS)
    # -------------------------------------------------------------------------
    op.execute("ALTER TABLE ai_analysis_jobs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE ai_analysis_jobs FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY ai_jobs_tenant_isolation ON ai_analysis_jobs
        USING (
            tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')
        )
        """
    )

    # -------------------------------------------------------------------------
    # Part D: Grants
    # -------------------------------------------------------------------------
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON ai_analysis_jobs TO app_user"
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS ai_jobs_tenant_isolation ON ai_analysis_jobs")
    op.drop_index("ix_ai_jobs_tenant_created", table_name="ai_analysis_jobs")
    op.drop_index("ix_ai_jobs_tenant_status", table_name="ai_analysis_jobs")
    op.drop_table("ai_analysis_jobs")
