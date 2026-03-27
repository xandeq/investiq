"""add_investor_profile

Revision ID: 0010_add_investor_profile
Revises: 0009_add_transaction_soft_delete
Create Date: 2026-03-18

Adds investor_profiles table for AI personalization context.
One row per tenant (unique constraint on tenant_id).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0010_add_investor_profile"
down_revision = "0009_add_transaction_soft_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "investor_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("idade", sa.Integer, nullable=True),
        sa.Column("renda_mensal", sa.Numeric(18, 2), nullable=True),
        sa.Column("patrimonio_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("objetivo", sa.String(50), nullable=True),
        sa.Column("horizonte_anos", sa.Integer, nullable=True),
        sa.Column("tolerancia_risco", sa.String(20), nullable=True),
        sa.Column("percentual_renda_fixa_alvo", sa.Numeric(5, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tenant_id", name="uq_investor_profiles_tenant"),
    )


def downgrade() -> None:
    op.drop_table("investor_profiles")
