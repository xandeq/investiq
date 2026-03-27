"""add_import_tables

Revision ID: 0005_add_import_tables
Revises: 0004_add_ai_analysis_jobs
Create Date: 2026-03-15 19:00:00.000000

Adds tables for the broker import pipeline.

What this migration does:

Part A: Create tables
  - import_files: stores raw uploaded file bytes permanently for re-parsing
  - import_jobs: tracks the parse/review lifecycle for each import
  - import_staging: parsed rows awaiting user confirmation

Part B: Add import_hash column to transactions
  - import_hash (String 64, nullable) — used for duplicate detection on confirm

Part C: Indexes
  - ix_import_files_tenant: filter files by tenant
  - ix_import_jobs_tenant_status: filter jobs by tenant + status
  - ix_import_staging_job: filter staging rows by job_id
  - ix_import_staging_tenant_hash: unique constraint on (tenant_id, import_hash)
    for fast duplicate detection at confirm time

Part D: RLS policies (same pattern as existing migrations)
  - ENABLE ROW LEVEL SECURITY on all three new tables
  - FORCE ROW LEVEL SECURITY (prevents table-owner bypass)
  - CREATE POLICY using NULLIF(current_setting('rls.tenant_id', TRUE), '')

Part E: Grants
  - GRANT SELECT, INSERT, UPDATE, DELETE on all new tables TO app_user

Design notes:
- file_bytes is stored as bytea (PostgreSQL LargeBinary) — never passed as Celery
  task argument. Tasks read bytes from DB by file_id.
- import_hash on import_staging uses SHA-256(tenant|ticker|type|date|qty|price).
  UniqueConstraint on (tenant_id, import_hash) makes duplicate detection trivial.
- import_hash on transactions is nullable — only set for imported transactions,
  not manually entered ones.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic
revision = "0005_add_import_tables"
down_revision = "0004_add_ai_analysis_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Part A: Create import_files table
    # -------------------------------------------------------------------------
    op.create_table(
        "import_files",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_bytes", sa.LargeBinary, nullable=False),
        sa.Column("file_size_bytes", sa.Integer, nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # -------------------------------------------------------------------------
    # Part A: Create import_jobs table
    # -------------------------------------------------------------------------
    op.create_table(
        "import_jobs",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("file_id", sa.String(36), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("staging_count", sa.Integer, nullable=True),
        sa.Column("confirmed_count", sa.Integer, nullable=True),
        sa.Column("duplicate_count", sa.Integer, nullable=True),
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
    # Part A: Create import_staging table
    # -------------------------------------------------------------------------
    op.create_table(
        "import_staging",
        sa.Column("id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("job_id", sa.String(36), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("asset_class", sa.String(20), nullable=False),
        sa.Column("transaction_type", sa.String(20), nullable=False),
        sa.Column("transaction_date", sa.Date, nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("unit_price", sa.Numeric(20, 8), nullable=False),
        sa.Column("total_value", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "brokerage_fee",
            sa.Numeric(20, 8),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "irrf_withheld",
            sa.Numeric(20, 8),
            nullable=False,
            server_default="0",
        ),
        sa.Column("notes", sa.String(500), nullable=False, server_default=""),
        sa.Column("parser_source", sa.String(20), nullable=False),
        sa.Column("import_hash", sa.String(64), nullable=False),
        sa.Column(
            "is_duplicate",
            sa.Boolean,
            nullable=False,
            server_default="false",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "import_hash",
            name="uq_import_staging_tenant_hash",
        ),
    )

    # -------------------------------------------------------------------------
    # Part B: Add import_hash to transactions table
    # -------------------------------------------------------------------------
    op.add_column(
        "transactions",
        sa.Column("import_hash", sa.String(64), nullable=True),
    )

    # -------------------------------------------------------------------------
    # Part C: Indexes
    # -------------------------------------------------------------------------
    op.create_index(
        "ix_import_files_tenant",
        "import_files",
        ["tenant_id"],
    )
    op.create_index(
        "ix_import_jobs_tenant_status",
        "import_jobs",
        ["tenant_id", "status"],
    )
    op.create_index(
        "ix_import_staging_job",
        "import_staging",
        ["job_id"],
    )
    op.create_index(
        "ix_import_staging_tenant_hash",
        "import_staging",
        ["tenant_id", "import_hash"],
    )

    # -------------------------------------------------------------------------
    # Part D: RLS policies
    # -------------------------------------------------------------------------
    for table in ("import_files", "import_jobs", "import_staging"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (
                tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')
            )
            """
        )

    # -------------------------------------------------------------------------
    # Part E: Grants
    # -------------------------------------------------------------------------
    for table in ("import_files", "import_jobs", "import_staging"):
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO app_user"
        )


def downgrade() -> None:
    for table in ("import_files", "import_jobs", "import_staging"):
        op.execute(
            f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}"
        )

    op.drop_index("ix_import_staging_tenant_hash", table_name="import_staging")
    op.drop_index("ix_import_staging_job", table_name="import_staging")
    op.drop_index("ix_import_jobs_tenant_status", table_name="import_jobs")
    op.drop_index("ix_import_files_tenant", table_name="import_files")

    op.drop_column("transactions", "import_hash")
    op.drop_table("import_staging")
    op.drop_table("import_jobs")
    op.drop_table("import_files")
