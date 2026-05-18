"""add portfolio_goals table

Revision ID: 0039
Revises: 0038
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "0039"
down_revision = "0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_goals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False, index=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("target_amount", sa.Numeric(20, 2), nullable=False),
        sa.Column("current_amount", sa.Numeric(20, 2), nullable=False, server_default="0"),
        sa.Column("asset_class", sa.String(50), nullable=True),
        sa.Column("deadline", sa.Date, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("portfolio_goals")
