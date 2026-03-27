"""add_billing_columns

Revision ID: 0006_add_billing_columns
Revises: 0005_add_import_tables
Create Date: 2026-03-17 01:11:00.000000

Adds Stripe billing infrastructure: columns on users + subscriptions table.

What this migration does:

Part A: Add billing columns to users table
  - stripe_customer_id (String 50, nullable, indexed) — Stripe cus_... ID
  - stripe_subscription_id (String 50, nullable, indexed) — Stripe sub_... ID
  - subscription_status (String 30, nullable) — active/canceled/past_due/trialing
  - subscription_current_period_end (DateTime tz, nullable) — for grace period display

Part B: Create subscriptions table
  - Billing history per user (one active row per user in v1)
  - Columns: user_id, stripe_customer_id, stripe_subscription_id, plan, status,
    current_period_end, created_at
  - Written by webhook handlers only — never from checkout redirect responses

Design notes:
- User.plan remains the canonical access-control field (no join needed on auth check).
- Subscriptions table provides billing history and admin queries.
- stripe_customer_id and stripe_subscription_id are indexed for efficient
  webhook lookup (Stripe sends IDs, not user IDs).
- No RLS changes needed — webhook writes use the service role (unscoped).
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic
revision = "0006_add_billing_columns"
down_revision = "0005_add_import_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # -------------------------------------------------------------------------
    # Part A: Add billing columns to users table
    # -------------------------------------------------------------------------
    op.add_column(
        "users",
        sa.Column("stripe_customer_id", sa.String(50), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("stripe_subscription_id", sa.String(50), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("subscription_status", sa.String(30), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "subscription_current_period_end",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    # -------------------------------------------------------------------------
    # Part B: Indexes on users for webhook lookup
    # -------------------------------------------------------------------------
    op.create_index(
        "ix_users_stripe_customer_id",
        "users",
        ["stripe_customer_id"],
    )
    op.create_index(
        "ix_users_stripe_subscription_id",
        "users",
        ["stripe_subscription_id"],
    )

    # -------------------------------------------------------------------------
    # Part C: Create subscriptions table — billing history per user
    # -------------------------------------------------------------------------
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(36),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stripe_customer_id", sa.String(50), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(50), nullable=False),
        sa.Column("plan", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index(
        "ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"]
    )
    op.create_unique_constraint(
        "uq_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )


def downgrade() -> None:
    # Drop subscriptions first (FK to users)
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_constraint(
        "uq_subscriptions_stripe_subscription_id", "subscriptions", type_="unique"
    )
    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")

    op.drop_index("ix_users_stripe_subscription_id", table_name="users")
    op.drop_index("ix_users_stripe_customer_id", table_name="users")
    op.drop_column("users", "subscription_current_period_end")
    op.drop_column("users", "subscription_status")
    op.drop_column("users", "stripe_subscription_id")
    op.drop_column("users", "stripe_customer_id")
