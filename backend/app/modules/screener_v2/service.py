"""Business logic for screener_v2 endpoints.

All screener queries read from global tables (screener_snapshots, fii_metadata,
fixed_income_catalog) or Redis (tesouro:rates:*). NEVER calls external APIs.

Key design constraints:
- Use get_global_db (not get_db) — global tables have no RLS policy
- TaxEngine instantiated per-request (not module-level singleton) — D-13
- Tesouro rates served from Redis tesouro:rates:* keys (set by refresh_tesouro_rates task)
"""
from __future__ import annotations

import json
import logging
import os
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_universe.models import FixedIncomeCatalog, FIIMetadata, ScreenerSnapshot, TaxConfig
from app.modules.market_universe.tax_engine import TaxEngine
from app.modules.screener_v2.schemas import (
    AcaoRow,
    AcaoScreenerParams,
    FIIRow,
    FIIScreenerParams,
    FixedIncomeCatalogRow,
    IRBreakdown,
    MacroRatesResponse,
    ScreenerUniverseRow,
    TesouroRateRow,
    HOLDING_PERIODS,
)

logger = logging.getLogger(__name__)


def _safe_decimal(val) -> Decimal | None:
    """Convert value to Decimal or return None."""
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


async def _get_portfolio_tickers(
    db: AsyncSession, tenant_id: str
) -> set[str]:
    """Return the set of ticker symbols in the user's portfolio.

    Queries the positions view / transactions table to find owned assets.
    Falls back to empty set on any error to avoid blocking screener results.
    """
    try:
        from sqlalchemy import text
        result = await db.execute(
            text(
                """
                SELECT DISTINCT ticker
                FROM transactions
                WHERE tenant_id = :tenant_id
                  AND asset_class IN ('acao', 'FII', 'BDR', 'ETF')
                  AND ticker IS NOT NULL
                """
            ),
            {"tenant_id": tenant_id},
        )
        return {row[0].upper() for row in result.fetchall()}
    except Exception as exc:
        logger.warning("_get_portfolio_tickers: failed — excluding nothing: %s", exc)
        return set()


async def query_acoes(
    db: AsyncSession,
    params: AcaoScreenerParams,
    tenant_db: AsyncSession | None = None,
    tenant_id: str | None = None,
) -> tuple[int, list[AcaoRow]]:
    """Query screener_snapshots for acoes matching the given filter params.

    Returns (total_count, rows_for_page).

    Uses the latest snapshot_date across the table. Filters applied:
        - min_dy, max_pl, max_pvp, max_ev_ebitda: numeric comparisons (NULL rows excluded)
        - sector: case-insensitive ILIKE match
        - min_volume, min_market_cap: lower bound on volume / market_cap
        - exclude_portfolio: excludes tickers already in user's portfolio
    """
    # Latest snapshot date
    latest_date_result = await db.execute(
        select(func.max(ScreenerSnapshot.snapshot_date))
    )
    latest_date = latest_date_result.scalar_one_or_none()

    if latest_date is None:
        return 0, []

    # Build base query for the latest snapshot
    stmt = select(ScreenerSnapshot).where(
        ScreenerSnapshot.snapshot_date == latest_date
    )

    # Apply filters — only apply if value provided and column is NOT NULL
    if params.min_dy is not None:
        stmt = stmt.where(
            ScreenerSnapshot.dy.isnot(None),
            ScreenerSnapshot.dy >= params.min_dy,
        )
    if params.max_pl is not None:
        stmt = stmt.where(
            ScreenerSnapshot.pl.isnot(None),
            ScreenerSnapshot.pl <= params.max_pl,
        )
    if params.max_pvp is not None:
        stmt = stmt.where(
            ScreenerSnapshot.pvp.isnot(None),
            ScreenerSnapshot.pvp <= params.max_pvp,
        )
    if params.max_ev_ebitda is not None:
        stmt = stmt.where(
            ScreenerSnapshot.ev_ebitda.isnot(None),
            ScreenerSnapshot.ev_ebitda <= params.max_ev_ebitda,
        )
    if params.sector is not None:
        stmt = stmt.where(
            ScreenerSnapshot.sector.ilike(f"%{params.sector}%")
        )
    if params.min_volume is not None:
        stmt = stmt.where(
            ScreenerSnapshot.regular_market_volume.isnot(None),
            ScreenerSnapshot.regular_market_volume >= params.min_volume,
        )
    if params.min_market_cap is not None:
        stmt = stmt.where(
            ScreenerSnapshot.market_cap.isnot(None),
            ScreenerSnapshot.market_cap >= params.min_market_cap,
        )

    # Count total before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Exclude portfolio tickers if requested
    excluded_tickers: set[str] = set()
    if params.exclude_portfolio and tenant_id and tenant_db:
        excluded_tickers = await _get_portfolio_tickers(tenant_db, tenant_id)

    if excluded_tickers:
        stmt = stmt.where(ScreenerSnapshot.ticker.notin_(excluded_tickers))
        # Recount after exclusion
        count_stmt2 = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt2)).scalar_one()

    # Pagination + ordering (by market_cap desc — most liquid first)
    stmt = (
        stmt
        .order_by(ScreenerSnapshot.market_cap.desc().nullslast())
        .limit(params.limit)
        .offset(params.offset)
    )

    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    rows = [
        AcaoRow(
            ticker=s.ticker,
            short_name=s.short_name,
            sector=s.sector,
            price=_safe_decimal(s.regular_market_price),
            change_pct=_safe_decimal(s.regular_market_change_percent),
            volume=s.regular_market_volume,
            market_cap=s.market_cap,
            pl=_safe_decimal(s.pl),
            pvp=_safe_decimal(s.pvp),
            dy=_safe_decimal(s.dy),
            ev_ebitda=_safe_decimal(s.ev_ebitda),
            snapshot_date=str(s.snapshot_date),
        )
        for s in snapshots
    ]

    return total, rows


async def query_fiis(
    db: AsyncSession,
    params: FIIScreenerParams,
    tenant_db: AsyncSession | None = None,
    tenant_id: str | None = None,
) -> tuple[int, list[FIIRow]]:
    """Query screener_snapshots + fii_metadata for FIIs matching the given filter params.

    Returns (total_count, rows_for_page).

    Joins screener_snapshots with fii_metadata on ticker. Filters applied:
        - min_dy, max_pvp: from screener_snapshots
        - segmento, max_vacancia, min_cotistas: from fii_metadata
        - min_volume: from screener_snapshots
    """
    from sqlalchemy import join
    from sqlalchemy.orm import aliased

    latest_date_result = await db.execute(
        select(func.max(ScreenerSnapshot.snapshot_date))
    )
    latest_date = latest_date_result.scalar_one_or_none()

    if latest_date is None:
        return 0, []

    # Join screener_snapshots with fii_metadata on ticker
    # Use outerjoin so FIIs without metadata still appear (segmento = null)
    snap = aliased(ScreenerSnapshot)
    fii = aliased(FIIMetadata)

    stmt = (
        select(snap, fii)
        .outerjoin(fii, snap.ticker == fii.ticker)
        .where(snap.snapshot_date == latest_date)
    )

    # FII-specific filter: tickers ending in 11 (standard FII suffix)
    stmt = stmt.where(snap.ticker.like("%11"))

    if params.min_dy is not None:
        stmt = stmt.where(
            snap.dy.isnot(None),
            snap.dy >= params.min_dy,
        )
    if params.max_pvp is not None:
        stmt = stmt.where(
            snap.pvp.isnot(None),
            snap.pvp <= params.max_pvp,
        )
    if params.min_volume is not None:
        stmt = stmt.where(
            snap.regular_market_volume.isnot(None),
            snap.regular_market_volume >= params.min_volume,
        )
    if params.segmento is not None:
        stmt = stmt.where(
            fii.segmento.ilike(f"%{params.segmento}%")
        )
    if params.max_vacancia is not None:
        stmt = stmt.where(
            fii.vacancia_financeira.isnot(None),
            fii.vacancia_financeira <= params.max_vacancia,
        )
    if params.min_cotistas is not None:
        stmt = stmt.where(
            fii.num_cotistas.isnot(None),
            fii.num_cotistas >= params.min_cotistas,
        )

    # Count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar_one()

    # Exclude portfolio tickers if requested
    excluded_tickers: set[str] = set()
    if params.exclude_portfolio and tenant_id and tenant_db:
        excluded_tickers = await _get_portfolio_tickers(tenant_db, tenant_id)

    if excluded_tickers:
        stmt = stmt.where(snap.ticker.notin_(excluded_tickers))
        count_stmt2 = select(func.count()).select_from(stmt.subquery())
        total = (await db.execute(count_stmt2)).scalar_one()

    # Pagination
    stmt = (
        stmt
        .order_by(snap.regular_market_volume.desc().nullslast())
        .limit(params.limit)
        .offset(params.offset)
    )

    result = await db.execute(stmt)
    pairs = result.all()

    rows = [
        FIIRow(
            ticker=s.ticker,
            short_name=s.short_name,
            segmento=f.segmento if f else None,
            price=_safe_decimal(s.regular_market_price),
            change_pct=_safe_decimal(s.regular_market_change_percent),
            volume=s.regular_market_volume,
            pvp=_safe_decimal(s.pvp),
            dy=_safe_decimal(s.dy),
            vacancia_financeira=_safe_decimal(f.vacancia_financeira) if f else None,
            num_cotistas=f.num_cotistas if f else None,
            snapshot_date=str(s.snapshot_date),
        )
        for s, f in pairs
    ]

    return total, rows


async def query_fixed_income_catalog(
    db: AsyncSession,
) -> list[FixedIncomeCatalogRow]:
    """Query fixed_income_catalog and calculate IR-adjusted net returns.

    TaxEngine is instantiated per-request from current tax_config rows.
    Returns all catalog rows enriched with IR breakdowns for 4 holding periods.
    """
    # Load TaxConfig rows for TaxEngine
    tax_rows = (await db.execute(select(TaxConfig))).scalars().all()
    engine = TaxEngine(tax_rows) if tax_rows else None

    # Load catalog rows
    catalog_rows = (await db.execute(select(FixedIncomeCatalog))).scalars().all()

    results = []
    for row in catalog_rows:
        ir_breakdowns: list[IRBreakdown] = []

        if engine is not None:
            # Determine asset class for TaxEngine
            if row.instrument_type in ("LCI",):
                asset_class = "LCI"
            elif row.instrument_type in ("LCA",):
                asset_class = "LCA"
            else:
                asset_class = "renda_fixa"

            # Use mid-rate for calculation (or min if no max)
            gross_pct = row.min_rate_pct
            if row.max_rate_pct is not None:
                gross_pct = (row.min_rate_pct + row.max_rate_pct) / Decimal("2")

            for period_label, holding_days in HOLDING_PERIODS.items():
                try:
                    ir_rate = engine.get_rate(asset_class, holding_days)
                    net_pct = engine.net_return(gross_pct, asset_class, holding_days)
                    is_exempt = engine.is_exempt(asset_class)
                    ir_breakdowns.append(IRBreakdown(
                        period_label=period_label,
                        holding_days=holding_days,
                        gross_pct=gross_pct,
                        ir_rate_pct=ir_rate,
                        net_pct=net_pct,
                        is_exempt=is_exempt,
                    ))
                except ValueError as exc:
                    logger.warning("TaxEngine: %s for %s holding_days=%d", exc, asset_class, holding_days)

        results.append(FixedIncomeCatalogRow(
            instrument_type=row.instrument_type,
            indexer=row.indexer,
            label=row.label,
            min_months=row.min_months,
            max_months=row.max_months,
            min_rate_pct=row.min_rate_pct,
            max_rate_pct=row.max_rate_pct,
            ir_breakdowns=ir_breakdowns,
        ))

    return results


async def query_screener_universe(db: AsyncSession) -> list[ScreenerUniverseRow]:
    """Return all tickers from the latest snapshot date, ordered by market_cap desc.

    No server-side filtering -- the frontend applies filters client-side with useMemo.
    """
    latest_date_result = await db.execute(
        select(func.max(ScreenerSnapshot.snapshot_date))
    )
    latest_date = latest_date_result.scalar_one_or_none()
    if latest_date is None:
        return []

    stmt = (
        select(ScreenerSnapshot)
        .where(ScreenerSnapshot.snapshot_date == latest_date)
        .order_by(ScreenerSnapshot.market_cap.desc().nullslast())
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        ScreenerUniverseRow(
            ticker=s.ticker,
            short_name=s.short_name,
            sector=s.sector,
            regular_market_price=_safe_decimal(s.regular_market_price),
            variacao_12m_pct=_safe_decimal(s.variacao_12m_pct),
            dy=_safe_decimal(s.dy),
            pl=_safe_decimal(s.pl),
            market_cap=s.market_cap,
        )
        for s in snapshots
    ]


async def query_tesouro_rates() -> list[TesouroRateRow]:
    """Fetch all Tesouro Direto rates from Redis tesouro:rates:* keys.

    Returns list sorted by tipo_titulo ascending.
    Falls back to empty list if Redis is unavailable.
    """
    try:
        import redis as redis_lib
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis_lib.Redis.from_url(redis_url, decode_responses=True)

        keys = r.keys("tesouro:rates:*")
        rows: list[TesouroRateRow] = []

        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            try:
                data = json.loads(raw)
                rows.append(TesouroRateRow(
                    tipo_titulo=data.get("tipo_titulo", ""),
                    vencimento=data.get("vencimento", ""),
                    taxa_indicativa=_safe_decimal(data.get("taxa_indicativa")),
                    pu=_safe_decimal(data.get("pu")),
                    data_base=data.get("data_base", ""),
                    source=data.get("source", ""),
                ))
            except Exception as exc:
                logger.warning("query_tesouro_rates: failed to parse key %s: %s", key, exc)

        rows.sort(key=lambda r: r.tipo_titulo)
        return rows

    except Exception as exc:
        logger.error("query_tesouro_rates: Redis unavailable: %s", exc)
        return []


async def query_macro_rates() -> MacroRatesResponse:
    """Fetch CDI and IPCA annual rates from Redis macro cache.

    Keys set by refresh_macro Celery beat task (every 7h).
    Falls back to None values if Redis unavailable.
    """
    try:
        import redis as redis_lib
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        cdi_raw = r.get("market:macro:cdi")
        ipca_raw = r.get("market:macro:ipca")
        selic_raw = r.get("market:macro:selic")
        return MacroRatesResponse(
            cdi=_safe_decimal(cdi_raw),
            ipca=_safe_decimal(ipca_raw),
            selic=_safe_decimal(selic_raw),
        )
    except Exception as exc:
        logger.error("query_macro_rates: Redis unavailable: %s", exc)
        return MacroRatesResponse(cdi=None, ipca=None, selic=None)
