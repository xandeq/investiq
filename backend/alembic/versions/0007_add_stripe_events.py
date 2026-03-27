"""add_stripe_events

Revision ID: 0007_add_stripe_events
Revises: 0006_add_billing_columns
Create Date: 2026-03-17 02:00:00.000000

Creates the stripe_events table for webhook idempotency.

Design notes:
- Primary key is the Stripe event ID (evt_...) — guaranteed unique by Stripe.
- Before processing a webhook, the router checks for an existing row.
  If found, returns 200 immediately without re-running the handler.
- status column ("success" | "error") lets ops identify failed events for replay.
- No FK to users — events are recorded even when no user can be found.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0007_add_stripe_events"
down_revision = "0006_add_billing_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stripe_events",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
    )
    op.create_index("ix_stripe_events_event_type", "stripe_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_stripe_events_event_type", table_name="stripe_events")
    op.drop_table("stripe_events")
