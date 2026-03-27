"""add wizard_jobs table for Phase 11 Wizard Onde Investir

Revision ID: 0016_add_wizard_jobs
Revises: 0015_add_market_universe_tables
Create Date: 2026-03-22
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0016_add_wizard_jobs"
down_revision = "0015_add_market_universe_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wizard_jobs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("perfil", sa.String(20), nullable=False),
        sa.Column("prazo", sa.String(5), nullable=False),
        sa.Column("valor", sa.Numeric(20, 2), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("result_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_wizard_jobs_tenant_status", "wizard_jobs", ["tenant_id", "status"])
    op.create_index("ix_wizard_jobs_tenant_created", "wizard_jobs", ["tenant_id", "created_at"])

    # RLS policy — tenants see only their own wizard jobs
    op.execute("ALTER TABLE wizard_jobs ENABLE ROW LEVEL SECURITY;")
    op.execute("""CREATE POLICY wizard_jobs_tenant_isolation ON wizard_jobs
        USING (tenant_id = current_setting('rls.tenant_id', true));""")
    op.execute("GRANT SELECT, INSERT, UPDATE ON wizard_jobs TO app_user;")


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS wizard_jobs_tenant_isolation ON wizard_jobs;")
    op.drop_table("wizard_jobs")
