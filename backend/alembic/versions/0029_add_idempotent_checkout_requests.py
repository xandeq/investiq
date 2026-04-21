"""add_idempotent_checkout_requests

Revision ID: 0029_add_idempotent_checkout_requests
Revises: 0028_add_unique_active_subscription_constraint
Create Date: 2026-04-18

P1 hardening: API-level idempotency cache for POST /billing/checkout.

Prevents duplicate checkout sessions if the user double-clicks the upgrade button
or if the browser retries the request. The primary key is the idempotency key
from the frontend (timestamp_nonce).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0029_add_idempotent_checkout_requests"
down_revision = "0028_add_unique_active_subscription_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "idempotent_checkout_requests",
        sa.Column("idempotency_key", sa.String(100), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("checkout_url", sa.String(2048), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("idempotency_key"),
    )
    op.create_index("ix_idempotent_checkout_requests_user_id", "idempotent_checkout_requests", ["user_id"])


def downgrade() -> None:
    op.drop_table("idempotent_checkout_requests")
