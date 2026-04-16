"""Portfolio health computation service (Phase 23 — ADVI-01).

compute_portfolio_health():
  - Reads buy/sell/dividend/jscp transactions from tenant DB (RLS-scoped)
  - Joins with screener_snapshots (global DB) to get sector + variacao_12m_pct
  - Returns PortfolioHealth with 4 metrics + health_score (deterministic formula)
  - No AI, no Redis, no external calls — pure SQL, target <200ms

Score formula (starts at 100, deductions additive):
  biggest_sector_pct > 50%    → -20
  biggest_asset_pct   > 30%   → -25
  distinct_assets     < 5     → -15
  underperformer cost > 30%   → -20
  passive_income_ttm  == 0    → -10
  (floor: 10)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advisor.schemas import PortfolioHealth
from app.modules.market_universe.models import ScreenerSnapshot
from app.modules.portfolio.models import Transaction

logger = logging.getLogger(__name__)

_UNDERPERFORM_THRESHOLD = Decimal("-10")   # variacao_12m_pct < -10% = underperformer
_CONCENTRATION_SECTOR = 50.0               # sector > 50% triggers biggest_risk
_CONCENTRATION_ASSET = 30.0               # single asset > 30% triggers biggest_risk
_MIN_ASSETS = 5                           # fewer than 5 distinct assets → alert


async def compute_portfolio_health(
    tenant_db: AsyncSession,
    global_db: AsyncSession,
    tenant_id: str,
) -> PortfolioHealth:
    """Compute portfolio health synchronously.

    tenant_db: RLS-scoped session (reads only this tenant's transactions)
    global_db: unscoped session (reads screener_snapshots — global table)
    """
    # ── 1. Load buy/sell transactions ──────────────────────────────────────
    tx_result = await tenant_db.execute(
        select(
            Transaction.ticker,
            Transaction.transaction_type,
            Transaction.total_value,
            Transaction.asset_class,
        ).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type.in_(["buy", "sell"]),
            Transaction.deleted_at.is_(None),
        )
    )
    txs = tx_result.all()

    if not txs:
        return PortfolioHealth(
            health_score=0,
            biggest_risk=None,
            passive_income_monthly_brl=Decimal("0"),
            underperformers=[],
            data_as_of=None,
            total_assets=0,
            has_portfolio=False,
        )

    # ── 2. Net cost-basis position per ticker ──────────────────────────────
    positions: dict[str, Decimal] = {}
    for row in txs:
        delta = Decimal(str(row.total_value))
        if row.transaction_type == "sell":
            delta = -delta
        positions[row.ticker] = positions.get(row.ticker, Decimal("0")) + delta

    active = {t: v for t, v in positions.items() if v > Decimal("0")}
    if not active:
        return PortfolioHealth(
            health_score=0,
            biggest_risk=None,
            passive_income_monthly_brl=Decimal("0"),
            underperformers=[],
            data_as_of=None,
            total_assets=0,
            has_portfolio=True,
        )

    total_cost = sum(active.values())

    # ── 3. Passive income TTM (dividends + jscp, last 12 months) ──────────
    ttm_cutoff = date.today() - timedelta(days=365)
    income_result = await tenant_db.execute(
        select(func.sum(Transaction.total_value)).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type.in_(["dividend", "jscp"]),
            Transaction.transaction_date >= ttm_cutoff,
            Transaction.deleted_at.is_(None),
        )
    )
    passive_ttm = income_result.scalar() or Decimal("0")
    passive_monthly = (Decimal(str(passive_ttm)) / 12).quantize(Decimal("0.01"))

    # ── 4. Fetch screener snapshots for active tickers ─────────────────────
    tickers = list(active.keys())

    # Subquery: latest snapshot_date per ticker
    latest_dates_sq = (
        select(
            ScreenerSnapshot.ticker,
            func.max(ScreenerSnapshot.snapshot_date).label("max_date"),
        )
        .where(ScreenerSnapshot.ticker.in_(tickers))
        .group_by(ScreenerSnapshot.ticker)
        .subquery()
    )

    snap_result = await global_db.execute(
        select(ScreenerSnapshot).join(
            latest_dates_sq,
            (ScreenerSnapshot.ticker == latest_dates_sq.c.ticker)
            & (ScreenerSnapshot.snapshot_date == latest_dates_sq.c.max_date),
        )
    )
    snaps = {s.ticker: s for s in snap_result.scalars().all()}
    data_as_of: datetime | None = None
    if snaps:
        latest_snap = max(snaps.values(), key=lambda s: s.snapshot_date)
        data_as_of = datetime.combine(latest_snap.snapshot_date, datetime.min.time()).replace(
            tzinfo=timezone.utc
        )

    # ── 5. Sector exposure ─────────────────────────────────────────────────
    sector_map: dict[str, Decimal] = {}
    for ticker, cost in active.items():
        snap = snaps.get(ticker)
        sector = (snap.sector or "Outros") if snap else "Outros"
        sector_map[sector] = sector_map.get(sector, Decimal("0")) + cost

    biggest_sector, biggest_sector_val = max(sector_map.items(), key=lambda x: x[1])
    biggest_sector_pct = float(biggest_sector_val / total_cost * 100)

    # ── 6. Asset concentration ─────────────────────────────────────────────
    biggest_ticker, biggest_asset_val = max(active.items(), key=lambda x: x[1])
    biggest_asset_pct = float(biggest_asset_val / total_cost * 100)

    # ── 7. Underperformers (variacao_12m_pct < -10%) ──────────────────────
    underperformer_entries: list[tuple[str, Decimal]] = []
    underperformer_cost = Decimal("0")
    for ticker, cost in active.items():
        snap = snaps.get(ticker)
        if snap and snap.variacao_12m_pct is not None:
            if snap.variacao_12m_pct < _UNDERPERFORM_THRESHOLD:
                underperformer_entries.append((ticker, snap.variacao_12m_pct))
                underperformer_cost += cost

    # Sort by worst performance, cap at 3
    underperformer_entries.sort(key=lambda x: x[1])
    underperformers = [
        f"{t} ({float(v):.1f}%)" for t, v in underperformer_entries[:3]
    ]
    underperformer_ratio = float(underperformer_cost / total_cost) if total_cost > 0 else 0.0

    # ── 8. Health score (deterministic) ───────────────────────────────────
    score = 100
    if biggest_sector_pct > _CONCENTRATION_SECTOR:
        score -= 20
    if biggest_asset_pct > _CONCENTRATION_ASSET:
        score -= 25
    if len(active) < _MIN_ASSETS:
        score -= 15
    if underperformer_ratio > 0.30:
        score -= 20
    if passive_ttm == 0:
        score -= 10
    score = max(score, 10)

    # ── 9. Biggest risk (single sentence) ─────────────────────────────────
    biggest_risk: str | None = None
    if biggest_sector_pct > _CONCENTRATION_SECTOR:
        biggest_risk = f"{biggest_sector_pct:.0f}% concentrado em {biggest_sector}"
    elif biggest_asset_pct > _CONCENTRATION_ASSET:
        biggest_risk = f"{biggest_asset_pct:.0f}% em um único ativo ({biggest_ticker})"
    elif len(active) < _MIN_ASSETS:
        biggest_risk = f"Apenas {len(active)} ativo(s) distinto(s) — baixa diversificação"

    return PortfolioHealth(
        health_score=score,
        biggest_risk=biggest_risk,
        passive_income_monthly_brl=passive_monthly,
        underperformers=underperformers,
        data_as_of=data_as_of,
        total_assets=len(active),
        has_portfolio=True,
    )
