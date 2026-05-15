"""Swing Trade service layer (Phase 20).

Pure read-side + CRUD for manual swing trade operations.

Signal computation is Redis-ONLY — it never makes new calls to brapi, yfinance,
CoinGecko, etc. It reuses the cache keys already populated by Phase 6
(market_data tasks):
  market:quote:{TICKER}          — QuoteCache
  market:historical:{TICKER}     — HistoricalCache
  market:fundamentals:{TICKER}   — FundamentalsCache (for DY)

Signal rules:
  BUY    — current price is >12% below the 30-day high AND DY > 5%
           (dividend-focused filter so we don't flag value traps without income)
  SELL   — open operation whose current price is >10% above entry_price
  NEUTRO — otherwise

The radar universe is imported from opportunity_detector.radar.RADAR_ACOES —
duplicating the list would drift over time.
"""
from __future__ import annotations

import logging
import math
import statistics
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.market_data.service import MarketDataService
from app.modules.opportunity_detector.radar import RADAR_ACOES
from app.modules.swing_trade.models import SwingTradeOperation
from app.modules.swing_trade.schemas import (
    OperationClose,
    OperationCreate,
    OperationListResponse,
    OperationResponse,
    SwingSignalItem,
    SwingSignalsResponse,
)

logger = logging.getLogger(__name__)

# --- Signal thresholds ---------------------------------------------------
BUY_DISCOUNT_THRESHOLD_PCT = -12.0  # must be at least 12% below 30d high
BUY_DY_FLOOR_PCT = 5.0              # DY must be above 5% (when known)
SELL_GAIN_THRESHOLD_PCT = 10.0      # close winners at +10%
HIGH_WINDOW_DAYS = 30


def _thirty_days_ago_epoch(now: datetime | None = None) -> int:
    now = now or datetime.now(timezone.utc)
    return int((now - timedelta(days=HIGH_WINDOW_DAYS)).timestamp())


def _compute_30d_high(historical_points: Iterable) -> Decimal | None:
    """Return max high over the last HIGH_WINDOW_DAYS, or None if no points."""
    cutoff = _thirty_days_ago_epoch()
    highs = [p.high for p in historical_points if getattr(p, "date", 0) >= cutoff]
    if not highs:
        return None
    return max(highs)


def _classify_signal(discount_pct: float, dy: Decimal | None) -> str:
    """BUY when deep discount + decent DY, otherwise NEUTRAL."""
    if discount_pct <= BUY_DISCOUNT_THRESHOLD_PCT:
        # If DY is unknown we still allow BUY — data_stale fundamentals shouldn't
        # mask a genuine dip. If DY is known it must clear the floor.
        if dy is None or float(dy) >= BUY_DY_FLOOR_PCT:
            return "buy"
    return "neutral"


async def compute_signals(
    redis_client,
    portfolio_tickers: list[str],
    portfolio_quantities: dict[str, Decimal] | None = None,
) -> SwingSignalsResponse:
    """Build portfolio + radar swing signal lists from Redis cache only.

    Args:
        redis_client: async Redis client (aioredis / redis.asyncio).
        portfolio_tickers: tickers the user currently holds (from PortfolioService).
        portfolio_quantities: optional map ticker -> quantity for enrichment.

    Returns:
        SwingSignalsResponse with generated_at=now and two sorted lists.
    """
    mds = MarketDataService(redis_client)
    quantities = portfolio_quantities or {}
    held = {t.upper() for t in portfolio_tickers}

    # Radar universe = RADAR_ACOES ∪ portfolio_tickers (so users see signals
    # for stocks they hold even if they're not in the curated radar).
    radar_by_ticker: dict[str, dict] = {a["ticker"]: a for a in RADAR_ACOES}
    for t in held:
        if t not in radar_by_ticker:
            radar_by_ticker[t] = {"ticker": t, "name": t, "setor": "-"}

    portfolio_signals: list[SwingSignalItem] = []
    radar_signals: list[SwingSignalItem] = []

    for ticker, meta in radar_by_ticker.items():
        quote = await mds.get_quote(ticker)
        if quote.data_stale or quote.price <= 0:
            continue

        historical = await mds.get_historical(ticker)
        high_30d = _compute_30d_high(historical.points) if not historical.data_stale else None
        if not high_30d or high_30d <= 0:
            continue

        fundamentals = await mds.get_fundamentals(ticker)
        dy = fundamentals.dy if not fundamentals.data_stale else None

        discount_pct = float(((quote.price - high_30d) / high_30d) * 100)
        signal = _classify_signal(discount_pct, dy)

        in_portfolio = ticker in held
        item = SwingSignalItem(
            ticker=ticker,
            name=meta.get("name", ticker),
            sector=meta.get("setor", "-"),
            current_price=quote.price,
            high_30d=high_30d,
            discount_pct=round(discount_pct, 2),
            dy=dy,
            signal=signal,
            signal_strength=round(abs(discount_pct), 2),
            in_portfolio=in_portfolio,
            quantity=quantities.get(ticker) if in_portfolio else None,
        )

        if in_portfolio:
            portfolio_signals.append(item)
        else:
            radar_signals.append(item)

    # Sort radar by deepest discount first (most negative at the top)
    radar_signals.sort(key=lambda x: x.discount_pct)
    portfolio_signals.sort(key=lambda x: x.discount_pct)

    return SwingSignalsResponse(
        portfolio_signals=portfolio_signals,
        radar_signals=radar_signals,
        generated_at=datetime.now(timezone.utc),
    )


# ---------------------------------------------------------------------------
# Operation CRUD
# ---------------------------------------------------------------------------


def _enrich_operation(
    op_row: SwingTradeOperation, current_price: Decimal | None
) -> OperationResponse:
    """Return OperationResponse with computed P&L / progress / live_signal."""
    resp = OperationResponse.model_validate(op_row)

    if current_price is None or current_price <= 0:
        return resp

    resp.current_price = current_price

    entry = Decimal(str(op_row.entry_price))
    qty = Decimal(str(op_row.quantity))

    pnl_brl = (current_price - entry) * qty
    resp.pnl_brl = float(pnl_brl)
    if entry > 0:
        resp.pnl_pct = float(((current_price - entry) / entry) * Decimal("100"))

    if op_row.entry_date is not None:
        now = datetime.now(timezone.utc)
        entry_dt = op_row.entry_date
        if entry_dt.tzinfo is None:
            entry_dt = entry_dt.replace(tzinfo=timezone.utc)
        resp.days_open = max(0, (now - entry_dt).days)

    target = op_row.target_price
    if target is not None:
        target_dec = Decimal(str(target))
        if target_dec > entry:
            resp.target_progress_pct = float(
                ((current_price - entry) / (target_dec - entry)) * Decimal("100")
            )

    # Live signal: sell on +10% gain, stop if price breached stop_price
    stop = op_row.stop_price
    if stop is not None and current_price <= Decimal(str(stop)):
        resp.live_signal = "stop"
    elif resp.pnl_pct is not None and resp.pnl_pct >= SELL_GAIN_THRESHOLD_PCT:
        resp.live_signal = "sell"
    else:
        resp.live_signal = "hold"

    return resp


async def get_operations(
    db: AsyncSession,
    tenant_id: str,
    redis_client=None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> OperationListResponse:
    """Return the tenant's swing trade operations enriched with live P&L.

    Counts (open_count, closed_count, total) are computed over the full
    unfiltered set so the UI can display totals independently of pagination.
    """
    from sqlalchemy import func as sqlfunc

    base_where = [
        SwingTradeOperation.tenant_id == tenant_id,
        SwingTradeOperation.deleted_at.is_(None),
    ]
    if status_filter:
        base_where.append(SwingTradeOperation.status == status_filter)

    # Total count (unfiltered by page) — one round-trip
    total = await db.scalar(
        select(sqlfunc.count()).select_from(SwingTradeOperation).where(*base_where)
    ) or 0

    stmt = (
        select(SwingTradeOperation)
        .where(*base_where)
        .order_by(SwingTradeOperation.entry_date.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(stmt)
    rows = list(result.scalars().all())

    mds = MarketDataService(redis_client) if redis_client is not None else None

    enriched: list[OperationResponse] = []
    for row in rows:
        current_price: Decimal | None = None
        if mds is not None and row.status == "open":
            try:
                quote = await mds.get_quote(row.ticker)
                if not quote.data_stale and quote.price > 0:
                    current_price = quote.price
            except Exception as exc:
                logger.debug("Swing operation enrich miss %s: %s", row.ticker, exc)
        enriched.append(_enrich_operation(row, current_price))

    open_count = sum(1 for r in rows if r.status == "open")
    closed_count = sum(1 for r in rows if r.status in ("closed", "stopped"))

    return OperationListResponse(
        total=total,
        open_count=open_count,
        closed_count=closed_count,
        results=enriched,
    )


async def create_operation(
    db: AsyncSession,
    tenant_id: str,
    data: OperationCreate,
) -> SwingTradeOperation:
    """Insert a new swing trade operation for the given tenant."""
    op_row = SwingTradeOperation(
        tenant_id=tenant_id,
        ticker=data.ticker.upper(),
        asset_class=data.asset_class,
        quantity=data.quantity,
        entry_price=data.entry_price,
        entry_date=data.entry_date,
        target_price=data.target_price,
        stop_price=data.stop_price,
        status="open",
        notes=data.notes,
    )
    db.add(op_row)
    await db.flush()
    return op_row


async def close_operation(
    db: AsyncSession,
    tenant_id: str,
    op_id: str,
    data: OperationClose,
) -> SwingTradeOperation | None:
    """Mark an operation as closed with exit price/date. Returns None if missing."""
    stmt = select(SwingTradeOperation).where(
        SwingTradeOperation.id == op_id,
        SwingTradeOperation.tenant_id == tenant_id,
        SwingTradeOperation.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return None

    row.status = "closed"
    row.exit_price = data.exit_price
    row.exit_date = data.exit_date or datetime.now(timezone.utc)
    await db.flush()
    return row


async def delete_operation(
    db: AsyncSession,
    tenant_id: str,
    op_id: str,
) -> bool:
    """Soft-delete an operation. Returns True when a row was touched."""
    stmt = select(SwingTradeOperation).where(
        SwingTradeOperation.id == op_id,
        SwingTradeOperation.tenant_id == tenant_id,
        SwingTradeOperation.deleted_at.is_(None),
    )
    result = await db.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        return False

    row.deleted_at = datetime.now(timezone.utc)
    await db.flush()
    return True


def _max_streak(flags: list[bool]) -> int:
    """Return max consecutive True streak."""
    best = current = 0
    for f in flags:
        current = current + 1 if f else 0
        best = max(best, current)
    return best


async def get_performance_stats(db: AsyncSession, tenant_id: str) -> dict[str, Any]:
    """Compute performance analytics from closed/stopped swing trade operations.

    Returns zeros/nulls when no closed trades exist (never raises).
    """
    stmt = select(SwingTradeOperation).where(
        SwingTradeOperation.tenant_id == tenant_id,
        SwingTradeOperation.status.in_(["closed", "stopped"]),
        SwingTradeOperation.deleted_at.is_(None),
        SwingTradeOperation.exit_price.isnot(None),
        SwingTradeOperation.entry_price.isnot(None),
    ).order_by(SwingTradeOperation.exit_date)
    result = await db.execute(stmt)
    ops = list(result.scalars().all())

    if not ops:
        return {
            "total_closed": 0,
            "data_available": False,
            "winrate": None,
            "avg_return_pct": None,
            "profit_factor": None,
            "r_sharpe": None,
            "max_consecutive_losses": 0,
            "max_consecutive_wins": 0,
            "avg_holding_days": None,
            "best_trade_pct": None,
            "worst_trade_pct": None,
        }

    # Return % per operation: (exit - entry) / entry × 100
    returns: list[float] = []
    holding_days: list[int] = []
    for op in ops:
        entry = float(op.entry_price)
        exit_ = float(op.exit_price)
        ret_pct = (exit_ - entry) / entry * 100 if entry > 0 else 0.0
        returns.append(ret_pct)

        if op.entry_date and op.exit_date:
            entry_dt = op.entry_date if hasattr(op.entry_date, "date") else datetime.fromisoformat(str(op.entry_date))
            exit_dt = op.exit_date if hasattr(op.exit_date, "date") else datetime.fromisoformat(str(op.exit_date))
            delta = (exit_dt - entry_dt).days if hasattr(exit_dt - entry_dt, "days") else 0
            if delta >= 0:
                holding_days.append(delta)

    wins = [r for r in returns if r > 0]
    losses = [r for r in returns if r <= 0]
    win_flags = [r > 0 for r in returns]

    winrate = round(len(wins) / len(returns) * 100, 1) if returns else None
    avg_ret = round(sum(returns) / len(returns), 2) if returns else None

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else None

    r_sharpe: float | None = None
    if len(returns) >= 3:
        stdev = statistics.stdev(returns)
        if stdev > 0 and avg_ret is not None:
            r_sharpe = round(avg_ret / stdev, 2)

    return {
        "total_closed": len(ops),
        "data_available": True,
        "winrate": winrate,
        "avg_return_pct": avg_ret,
        "profit_factor": profit_factor,
        "r_sharpe": r_sharpe,
        "max_consecutive_losses": _max_streak([not f for f in win_flags]),
        "max_consecutive_wins": _max_streak(win_flags),
        "avg_holding_days": round(sum(holding_days) / len(holding_days), 1) if holding_days else None,
        "best_trade_pct": round(max(returns), 2) if returns else None,
        "worst_trade_pct": round(min(returns), 2) if returns else None,
    }
