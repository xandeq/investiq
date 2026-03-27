"""add_ai_usage_logs

Revision ID: 0019_add_ai_usage_logs
Revises: 0018_normalize_assetclass_enum_lowercase
Create Date: 2026-03-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_add_ai_usage_logs"
down_revision = "0018_normalize_assetclass_enum_lowercase"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("tenant_id", sa.String(36), nullable=True),
        sa.Column("job_id", sa.String(36), nullable=True),
        sa.Column("tier", sa.String(20), nullable=False),
        sa.Column("provider", sa.String(30), nullable=False),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("success", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("error", sa.String(300), nullable=True),
    )
    op.create_index("ix_ai_usage_created", "ai_usage_logs", ["created_at"])
    op.create_index("ix_ai_usage_tenant", "ai_usage_logs", ["tenant_id"])
    op.create_index("ix_ai_usage_tier", "ai_usage_logs", ["tier"])


def downgrade() -> None:
    op.drop_table("ai_usage_logs")
