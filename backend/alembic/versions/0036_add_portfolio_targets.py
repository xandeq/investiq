"""add portfolio_targets table

Revision ID: 0036
Revises: 0035
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0036"
down_revision = "0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "portfolio_targets",
        sa.Column("id", sa.UUID(), nullable=False, server_default=sa.text("gen_random_uuid()")),
        sa.Column("tenant_id", sa.String(length=64), nullable=False),
        sa.Column("asset_class", sa.String(length=32), nullable=False),
        sa.Column("target_pct", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "asset_class", name="uq_portfolio_targets_tenant_class"),
    )
    op.create_index("ix_portfolio_targets_tenant", "portfolio_targets", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("ix_portfolio_targets_tenant", "portfolio_targets")
    op.drop_table("portfolio_targets")
