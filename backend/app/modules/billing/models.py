"""SQLAlchemy model for Subscription — billing history per user.

Design notes:
- One active Subscription per user max (v1 constraint).
  Multiple rows can exist over time (cancel + resubscribe creates a new row).
- user_id + stripe_subscription_id together identify a billing period.
- stripe_customer_id is denormalized here for fast admin queries
  without joining to users.
- All writes come from webhook handlers only — never from checkout redirect.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stripe_customer_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stripe_subscription_id: Mapped[str] = mapped_column(
        String(50), nullable=False, unique=True, index=True
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False)  # "free" | "pro"
    status: Mapped[str] = mapped_column(String(30), nullable=False)  # active/canceled/past_due/trialing
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    def __repr__(self) -> str:
        return f"<Subscription id={self.id} user_id={self.user_id} status={self.status}>"


class StripeEvent(Base):
    """Idempotency log — one row per processed Stripe event ID.

    The primary key is the Stripe event ID (evt_...). Before processing any
    webhook, the router checks for an existing row. If found, the event is
    returned 200 immediately without re-running the handler. This prevents
    duplicate side-effects from Stripe retries or accidental replays.

    status: "success" | "error" — lets ops identify failed events for replay.
    """
    __tablename__ = "stripe_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Stripe evt_...
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | error

    def __repr__(self) -> str:
        return f"<StripeEvent id={self.id} type={self.event_type} status={self.status}>"
