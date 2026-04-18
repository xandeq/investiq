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

get_complementary_assets() (Phase 25 — ADVI-03):
  - Identifies portfolio sectors by joining transactions with screener_snapshots
  - Queries screener universe for tickers NOT in portfolio sectors
  - Scores by relevance (DY-weighted, inverse variacao_12m)
  - Returns ranked list capped at `limit`

get_portfolio_entry_signals() (Phase 26 — ADVI-04):
  - Fetches user's portfolio tickers from tenant DB
  - Calls compute_signals() from swing_trade to get technical signals
  - Maps SwingSignalItem → EntrySignal
  - Caches result for 5 minutes

get_universe_entry_signals() (Phase 26 — ADVI-04):
  - Reads nightly-refreshed batch from Redis key "entry_signals:universe"
  - No DB query — pure cache read
  - Returns [] if batch hasn't run yet
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.advisor.schemas import EntrySignal, PortfolioHealth
from app.modules.market_universe.models import ScreenerSnapshot
from app.modules.portfolio.models import Transaction
from app.modules.swing_trade.service import compute_signals

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


# ── Smart Screener (Phase 25 — ADVI-03) ──────────────────────────────────────

class ComplementaryAssetRow(BaseModel):
    """One row returned by GET /advisor/screener.

    Represents a B3 asset whose sector is NOT currently held by the user,
    ranked by relevance to portfolio health gaps.

    Field names map to ScreenerSnapshot columns:
      preco_atual     → ScreenerSnapshot.regular_market_price
      dy_12m_pct      → ScreenerSnapshot.dy
    """
    ticker: str
    sector: Optional[str]
    preco_atual: Optional[Decimal]       # ScreenerSnapshot.regular_market_price
    dy_12m_pct: Optional[Decimal]        # ScreenerSnapshot.dy
    variacao_12m_pct: Optional[Decimal]  # ScreenerSnapshot.variacao_12m_pct
    market_cap: Optional[int]            # ScreenerSnapshot.market_cap (BigInteger)
    relevance_score: float               # 0–100, higher = more relevant to portfolio gaps


async def get_complementary_assets(
    tenant_db: AsyncSession,
    global_db: AsyncSession,
    tenant_id: str,
    limit: int = 100,
) -> list[ComplementaryAssetRow]:
    """Return screener universe filtered to assets NOT in user's portfolio sectors.

    Algorithm:
    1. Load all buy/sell transactions to find portfolio tickers.
    2. Join portfolio tickers with screener_snapshots to identify held sectors.
    3. Query latest screener snapshot for tickers whose sector is NOT held.
    4. Score each result by relevance (DY × 2 + inverse variacao) and sort.

    When the portfolio is empty, returns the full screener universe (all sectors
    are "complementary" to an empty portfolio) with a neutral relevance_score=50.
    """
    # ── 1. Identify portfolio tickers ─────────────────────────────────────────
    tx_result = await tenant_db.execute(
        select(Transaction.ticker).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type.in_(["buy", "sell"]),
            Transaction.deleted_at.is_(None),
        )
    )
    portfolio_tickers: set[str] = {row[0] for row in tx_result.all()}

    # ── 2. Latest snapshot date ───────────────────────────────────────────────
    date_result = await global_db.execute(
        select(func.max(ScreenerSnapshot.snapshot_date))
    )
    latest_date = date_result.scalar()

    if latest_date is None:
        # No screener data at all — return empty list
        return []

    # ── 3. Empty portfolio → return full universe ─────────────────────────────
    if not portfolio_tickers:
        snap_result = await global_db.execute(
            select(ScreenerSnapshot).where(
                ScreenerSnapshot.snapshot_date == latest_date,
            ).limit(limit)
        )
        snaps = snap_result.scalars().all()
        return [
            ComplementaryAssetRow(
                ticker=s.ticker,
                sector=s.sector,
                preco_atual=s.regular_market_price,
                dy_12m_pct=s.dy,
                variacao_12m_pct=s.variacao_12m_pct,
                market_cap=s.market_cap,
                relevance_score=50.0,  # Neutral — no gaps to optimise for
            )
            for s in snaps
        ]

    # ── 4. Identify sectors already held ──────────────────────────────────────
    sector_result = await global_db.execute(
        select(ScreenerSnapshot.sector).where(
            ScreenerSnapshot.ticker.in_(list(portfolio_tickers)),
            ScreenerSnapshot.snapshot_date == latest_date,
        )
    )
    portfolio_sectors: set[str] = {row[0] for row in sector_result.all() if row[0]}

    # ── 5. Query complementary assets (sector NOT in portfolio_sectors) ────────
    if portfolio_sectors:
        query = select(ScreenerSnapshot).where(
            ScreenerSnapshot.snapshot_date == latest_date,
            ScreenerSnapshot.sector.notin_(portfolio_sectors),
        )
    else:
        # Portfolio exists but no sector info available → return full universe
        query = select(ScreenerSnapshot).where(
            ScreenerSnapshot.snapshot_date == latest_date,
        )

    snap_result = await global_db.execute(query)
    snaps = snap_result.scalars().all()

    # ── 6. Score by relevance and rank ────────────────────────────────────────
    rows: list[ComplementaryAssetRow] = []
    for s in snaps:
        # Higher DY → more relevant (income gap)
        # Lower variacao_12m → might be attractively priced (inverse score)
        dy_score = float(s.dy or 0) * 200        # dy is fractional (e.g. 0.12 = 12%)
        var_score = 50.0 - float(s.variacao_12m_pct or 0) * 100  # invert: lower = better entry
        score = min(100.0, max(0.0, dy_score + var_score))
        rows.append(
            ComplementaryAssetRow(
                ticker=s.ticker,
                sector=s.sector,
                preco_atual=s.regular_market_price,
                dy_12m_pct=s.dy,
                variacao_12m_pct=s.variacao_12m_pct,
                market_cap=s.market_cap,
                relevance_score=score,
            )
        )

    rows.sort(key=lambda x: x.relevance_score, reverse=True)
    return rows[:limit]


# ── Entry Signals (Phase 26 — ADVI-04) ───────────────────────────────────────

_ENTRY_SIGNAL_CACHE_TTL = 300        # 5 minutes for portfolio signals
_ENTRY_UNIVERSE_CACHE_TTL = 86400    # 24 hours for universe batch
_ENTRY_SIGNALS_DEFAULT_AMOUNT_BRL = "1000.00"  # default suggested amount when no position size info
_ENTRY_SIGNALS_TIMEFRAME_DAYS = 90   # standard swing-trade horizon
_ENTRY_SIGNALS_STOP_LOSS_PCT = 8.0   # standard stop-loss %


def _get_sync_redis_for_signals():
    """Sync Redis client for caching entry signals."""
    import redis as sync_redis
    return sync_redis.from_url(
        os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
    )


async def get_portfolio_entry_signals(
    tenant_db: AsyncSession,
    global_db: AsyncSession,
    tenant_id: str,
) -> list[EntrySignal]:
    """On-demand entry signals for user's owned assets.

    Algorithm:
    1. Check Redis cache (5-min TTL).
    2. Load portfolio tickers from tenant DB (buy transactions, distinct).
    3. If no tickers → return [].
    4. Call compute_signals() from swing_trade with async Redis client.
    5. Map portfolio_signals (SwingSignalItem) → EntrySignal.
    6. Cache result and return.

    Mapping:
      ticker           → ticker
      discount_pct     → target_upside_pct (negated: discount is negative, upside is positive)
      signal           → ma_signal
      signal_strength  → proxy for RSI magnitude (rsi=None — RSI not available without full TA)
      suggested_amount → hardcoded R$1,000 default (no position-size context in test env)
      timeframe_days   → 90 (fixed swing-trade horizon)
      stop_loss_pct    → 8.0 (fixed standard stop)
    """
    cache_key = f"entry_signals:portfolio:{tenant_id}"

    # ── 1. Try cache ──────────────────────────────────────────────────────
    try:
        r = _get_sync_redis_for_signals()
        cached = r.get(cache_key)
        if cached:
            return [EntrySignal(**item) for item in json.loads(cached)]
    except Exception as exc:
        logger.warning("get_portfolio_entry_signals: cache read failed: %s", exc)

    # ── 2. Load portfolio tickers ─────────────────────────────────────────
    tx_result = await tenant_db.execute(
        select(Transaction.ticker).where(
            Transaction.tenant_id == tenant_id,
            Transaction.transaction_type == "buy",
            Transaction.deleted_at.is_(None),
        ).distinct()
    )
    tickers = [row[0] for row in tx_result.all()]

    if not tickers:
        return []

    # ── 3. Compute swing signals via Redis-cached market data ─────────────
    signals: list[EntrySignal] = []
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(
            os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
        )
        try:
            sw_response = await compute_signals(redis_client, tickers)
        finally:
            await redis_client.aclose()

        # ── 4. Map SwingSignalItem → EntrySignal ──────────────────────────
        now = datetime.now(timezone.utc)
        for item in sw_response.portfolio_signals:
            # target_upside_pct: discount_pct is negative (below 30d high).
            # Negate so upside = expected recovery if price returns to 30d high.
            target_upside = -item.discount_pct if item.discount_pct < 0 else 0.0
            signals.append(EntrySignal(
                ticker=item.ticker,
                suggested_amount_brl=_ENTRY_SIGNALS_DEFAULT_AMOUNT_BRL,
                target_upside_pct=round(target_upside, 2),
                timeframe_days=_ENTRY_SIGNALS_TIMEFRAME_DAYS,
                stop_loss_pct=_ENTRY_SIGNALS_STOP_LOSS_PCT,
                rsi=None,  # RSI not computed by compute_signals — would need separate TA call
                ma_signal=item.signal,
                generated_at=now,
            ))

    except Exception as exc:
        logger.warning("get_portfolio_entry_signals: compute_signals failed: %s", exc)
        # Return empty list on Redis/market-data failure — graceful degradation

    # ── 5. Cache result ───────────────────────────────────────────────────
    if signals:
        try:
            r = _get_sync_redis_for_signals()
            data = [s.model_dump(mode="json") for s in signals]
            r.setex(cache_key, _ENTRY_SIGNAL_CACHE_TTL, json.dumps(data, default=str))
        except Exception as exc:
            logger.error("get_portfolio_entry_signals: cache write failed: %s", exc)

    return signals


async def get_universe_entry_signals() -> list[EntrySignal]:
    """Batch entry signals for universe (from nightly Celery job).

    Reads from Redis cache key "entry_signals:universe".
    Returns [] if the Celery batch task hasn't run yet.
    No DB query — pure cache read for maximum performance.
    """
    cache_key = "entry_signals:universe"

    try:
        r = _get_sync_redis_for_signals()
        cached = r.get(cache_key)
        if cached:
            return [EntrySignal(**item) for item in json.loads(cached)]
    except Exception as exc:
        logger.warning("get_universe_entry_signals: cache read failed: %s", exc)

    return []
