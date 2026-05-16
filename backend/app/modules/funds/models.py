"""SQLAlchemy models for the funds module.

FundInfo: metadata from CVM fund registration (cad_fi.csv).
FundQuote: daily NAV per quota from CVM inf_diario CSV.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


def _utcnow() -> datetime:
    return datetime.now(tz=timezone.utc)


class FundInfo(Base):
    """CVM-registered fund metadata.

    CNPJ stored as 14 raw digits (no formatting). Populated/refreshed
    by the daily refresh_fund_registry Celery task.
    """
    __tablename__ = "fund_info"

    cnpj: Mapped[str] = mapped_column(String(14), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    admin: Mapped[str] = mapped_column(String(128), nullable=True)
    fund_class: Mapped[str] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class FundQuote(Base):
    """Daily NAV per quota for a fund (from CVM inf_diario CSV).

    One row per (cnpj, quote_date). Updated daily by refresh_fund_quotes task.
    """
    __tablename__ = "fund_quotes"
    __table_args__ = (
        UniqueConstraint("cnpj", "quote_date", name="uq_fund_quotes_cnpj_date"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True,
        server_default="gen_random_uuid()::text",
    )
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False, index=True)
    quote_date: Mapped[date] = mapped_column(Date, nullable=False)
    nav_per_quota: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    net_assets_brl: Mapped[float] = mapped_column(Numeric(20, 2), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )
