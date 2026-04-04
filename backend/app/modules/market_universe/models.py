"""SQLAlchemy 2.x models for the market_universe module.

These are GLOBAL tables — no tenant_id column, no RLS policies.
All 4 tables store universe-level data shared across all tenants.

Tables:
    screener_snapshots   — daily snapshot of B3 equity fundamentals
    fii_metadata         — FII segment + vacancy data (weekly CVM)
    fixed_income_catalog — reference rate ranges for CDB/LCI/LCA/TD (seeded)
    tax_config           — IR regressivo tiers + exemptions (seeded, drives TaxEngine)
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, Date, DateTime, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.modules.auth.models import Base


class ScreenerSnapshot(Base):
    """Daily snapshot of B3 equity fundamentals from brapi.dev.

    One row per (ticker, snapshot_date). Upserted by refresh_screener_universe
    Celery task (Mon–Fri at 07:00 BRT).
    """

    __tablename__ = "screener_snapshots"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(100), nullable=True)
    regular_market_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 6), nullable=True)
    regular_market_change_percent: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    regular_market_volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    market_cap: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    pl: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    pvp: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    dy: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    ev_ebitda: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class FIIMetadata(Base):
    """FII segment and vacancy data sourced from CVM informe mensal.

    One row per FII ticker. Upserted by refresh_fii_metadata Celery task
    (Monday at 06:00 BRT weekly).
    """

    __tablename__ = "fii_metadata"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    segmento: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vacancia_financeira: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    num_cotistas: Mapped[int | None] = mapped_column(Integer, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # Phase 17: pre-calculated score columns (updated nightly by calculate_fii_scores task)
    dy_12m: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
    pvp: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    daily_liquidity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    dy_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pvp_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    liquidity_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class FixedIncomeCatalog(Base):
    """Reference rate ranges for CDB, LCI, LCA, Tesouro Direto.

    Seeded via Alembic migration 0015. Updated via direct SQL when CDI shifts
    significantly (monthly at most). UI must label these as 'taxas de referencia
    de mercado' — never as live rates.
    """

    __tablename__ = "fixed_income_catalog"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    instrument_type: Mapped[str] = mapped_column(String(20), nullable=False)  # CDB, LCI, LCA, TD_SELIC
    indexer: Mapped[str] = mapped_column(String(20), nullable=False)           # CDI, IPCA, PREFIXADO, SELIC
    min_months: Mapped[int] = mapped_column(Integer, nullable=False)
    max_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_rate_pct: Mapped[Decimal] = mapped_column(Numeric(8, 4), nullable=False)
    max_rate_pct: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
    is_reference: Mapped[bool] = mapped_column(Boolean, server_default="true", nullable=False)


class TaxConfig(Base):
    """IR regressivo rate tiers and asset class exemptions.

    Seeded via Alembic migration 0015. Loaded once per TaxEngine instantiation.
    Rate changes require direct SQL + process restart (D-12).

    Scope: IR regressivo + LCI/LCA PF exemption + FII dividend exemption.
    NOT the full IR matrix (acoes monthly exemption, day-trade 20%).
    """

    __tablename__ = "tax_config"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    asset_class: Mapped[str] = mapped_column(String(30), nullable=False)  # renda_fixa, FII, LCI, LCA
    holding_days_min: Mapped[int] = mapped_column(Integer, nullable=False)
    holding_days_max: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = no upper bound
    rate_percent: Mapped[Decimal] = mapped_column(Numeric(6, 4), nullable=False)
    is_exempt: Mapped[bool] = mapped_column(Boolean, server_default="false", nullable=False)
    label: Mapped[str] = mapped_column(String(100), nullable=False)
