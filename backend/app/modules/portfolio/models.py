"""SQLAlchemy 2.x models for the portfolio module.

Models:
- Transaction: polymorphic single table covering all asset classes
- CorporateAction: corporate events (splits, bonuses, groupings) in a separate table

Design notes:
- tenant_id stored directly on both tables — RLS policy uses it directly.
  No FK to users table — tenant isolation is via RLS, not FK constraints.
- Polymorphic single table: all asset classes share one table; asset-class-specific
  columns (coupon_rate, maturity_date) are nullable — populated only when relevant.
- IR fields (irrf_withheld, gross_profit) stored at transaction time, never computed.
  Tax authority requires exact stored values; on-the-fly computation causes drift.
- Uses the shared Base from app.modules.auth.models so all models share one metadata
  object (required for Alembic autogenerate to detect all tables).

EXT-01 proof: This module imports NOTHING from app.core.security or app.modules.auth.
Only the shared Base is imported — and Base is a plain DeclarativeBase with no
auth-domain logic. Adding this module required zero changes in app/core/ or app/modules/auth/.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Enum as SAEnum, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

# Import Base from auth.models — the shared declarative base for ALL modules.
# This is NOT a dependency on auth domain logic; Base is a plain DeclarativeBase.
# All modules must share the same Base so Alembic can detect them in one metadata.
from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class AssetClass(str, enum.Enum):
    acao = "acao"
    fii = "fii"
    renda_fixa = "renda_fixa"
    bdr = "bdr"
    etf = "etf"


class TransactionType(str, enum.Enum):
    buy = "buy"
    sell = "sell"
    dividend = "dividend"
    jscp = "jscp"
    amortization = "amortization"


class CorporateActionType(str, enum.Enum):
    desdobramento = "desdobramento"
    grupamento = "grupamento"
    bonificacao = "bonificacao"


class Transaction(Base):
    """Single polymorphic table covering all asset classes.

    Asset-class-specific columns are nullable — only populated when relevant:
    - coupon_rate, maturity_date: renda_fixa only
    - is_exempt: FII dividends (Brazilian tax exemption rule)

    IR-required fields (irrf_withheld, gross_profit) are stored at transaction
    time. Never compute them on-the-fly — stored values are authoritative for IR.
    """
    __tablename__ = "transactions"

    # SQLite-compatible: String(36); PostgreSQL gets UUID natively via migration
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    portfolio_id: Mapped[str] = mapped_column(String(36), nullable=False)  # v1: same as tenant_id

    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(
        SAEnum(AssetClass, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)

    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    total_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    brokerage_fee: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)

    # IR-required fields — stored at transaction time, never computed on-the-fly
    irrf_withheld: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)
    gross_profit: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=True)

    # Asset-class-specific nullable columns (polymorphic single table)
    coupon_rate: Mapped[Decimal] = mapped_column(Numeric(10, 6), nullable=True)   # renda_fixa
    maturity_date: Mapped[date] = mapped_column(Date, nullable=True)              # renda_fixa
    is_exempt: Mapped[bool] = mapped_column(Boolean, default=False)               # FII dividends

    notes: Mapped[str] = mapped_column(String(500), nullable=True)

    # Import tracking — set only for transactions created via the import pipeline.
    # Used for duplicate detection at confirm time (hash = SHA-256 of key fields).
    # Nullable — manually entered transactions do not have an import hash.
    import_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, server_default=func.now()
    )
    # Tracks which import job created this transaction (for revert/undo).
    # NULL = manually entered or imported before migration 0031.
    import_job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)

    # Soft delete — NULL means active; timestamp means deleted.
    # All read queries must filter WHERE deleted_at IS NULL.
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Transaction id={self.id} ticker={self.ticker} "
            f"asset_class={self.asset_class} type={self.transaction_type}>"
        )


class CorporateAction(Base):
    """Corporate events table — separate from user transactions (clean EXT-01 separation).

    Stores B3 corporate events: stock splits (desdobramento), reverse splits (grupamento),
    stock bonuses (bonificacao). These affect cost basis calculations in Phase 2.

    Kept separate from transactions to avoid polluting the transaction history
    with system-generated events. Phase 2 CMP engine reads both tables.
    """
    __tablename__ = "corporate_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)

    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    action_type: Mapped[CorporateActionType] = mapped_column(
        SAEnum(CorporateActionType, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    action_date: Mapped[date] = mapped_column(Date, nullable=False)
    factor: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)  # split/bonus ratio
    source: Mapped[str] = mapped_column(String(100), nullable=True)          # "B3" | "manual"

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, server_default=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<CorporateAction id={self.id} ticker={self.ticker} "
            f"type={self.action_type} factor={self.factor}>"
        )
