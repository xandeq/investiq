"""SQLAlchemy 2.x models for the auth module.

Models:
- User: account with bcrypt password, email verification, plan tier
- RefreshToken: rotation-tracked refresh tokens (stored as SHA256 hash)
- VerificationToken: one-time email verification and password-reset tokens

Design notes:
- tenant_id = user.id for v1 (one portfolio per user = one tenant).
  This is a deliberate v1 simplification. Multi-user tenants are Phase 2+ concern.
- token_hash stores SHA256(token) — the raw token is only ever in the JWT payload
  sent to the user; we never store raw tokens.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class Base(DeclarativeBase):
    pass


class TokenStatus(str, PyEnum):
    active = "active"
    used = "used"
    revoked = "revoked"


class User(Base):
    __tablename__ = "users"

    # SQLite-compatible UUID: use String(36); PostgreSQL gets UUID via migration
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # v1: tenant_id = user.id — one tenant per user for the single-portfolio MVP
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # EXT-02: DB-configurable plan — "free" | "pro" | "enterprise"
    plan: Mapped[str] = mapped_column(String(50), default="free", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )
    # Trial fields — set on registration, cleared after expiry
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")
    trial_warning_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, server_default="false")

    # Email notification preferences — LGPD opt-out
    email_digest_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, server_default="true")

    # Stripe billing columns — set by webhooks, never from checkout redirect
    stripe_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    subscription_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    subscription_current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    verification_tokens: Mapped[list["VerificationToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email} verified={self.is_verified}>"


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[TokenStatus] = mapped_column(
        Enum(TokenStatus, name="token_status"), default=TokenStatus.active, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="refresh_tokens")


class VerificationToken(Base):
    __tablename__ = "verification_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    # Stores SHA256 hash of the token JWT — raw token is never persisted
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    purpose: Mapped[str] = mapped_column(String(20), nullable=False)  # "verify" | "reset"
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="verification_tokens")
