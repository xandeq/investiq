"""add import_job_id to transactions

Revision ID: 0031
Revises: 0030
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0031"
down_revision = "0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("import_job_id", sa.String(36), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "import_job_id")
