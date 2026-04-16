"""DashboardService — aggregates portfolio data for the dashboard summary endpoint.

Delegates to PortfolioService (single DB pass) and MarketDataService (Redis reads).
Does NOT own any data access logic — orchestrates existing services.

N+1 prevention: call get_pnl() ONCE, reuse pnl.positions for all derived metrics.
Do NOT call get_positions() separately — get_pnl() calls it internally.

Resilience: any internal failure returns an empty summary with data_stale=True
instead of propagating a 500 to the frontend.
"""
from __future__ import annotations
import logging
from collections import defaultdict
from decimal import Decimal
from datetime import date
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.service import PortfolioService
from app.modules.market_data.service import MarketDataService
from app.modules.portfolio.models import Transaction
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    AllocationSummary,
    TimeseriesPoint,
    RecentTransaction,
)

logger = logging.getLogger(__name__)


class DashboardService:
    async def get_summary(
        self,
        db: AsyncSession,
        tenant_id: str,
        redis_client,
    ) -> DashboardSummaryResponse:
        try:
            return await self._get_summary_inner(db, tenant_id, redis_client)
        except Exception as exc:
            logger.error("DashboardService.get_summary failed for tenant %s: %s", tenant_id, exc, exc_info=True)
            # Plan B: return empty stale summary so the frontend shows a degraded state
            # instead of a full-page 500 error
            return DashboardSummaryResponse(
                net_worth=Decimal("0"),
                total_invested=Decimal("0"),
                total_return=Decimal("0"),
                total_return_pct=Decimal("0"),
                daily_pnl=Decimal("0"),
                daily_pnl_pct=Decimal("0"),
                data_stale=True,
                asset_allocation=[],
                portfolio_timeseries=[],
                recent_transactions=[],
            )

    async def _get_summary_inner(
        self,
        db: AsyncSession,
        tenant_id: str,
        redis_client,
    ) -> DashboardSummaryResponse:
        portfolio_svc = PortfolioService()
        mds = MarketDataService(redis_client)

        # SINGLE DB call — reuse pnl.positions for all derived metrics
        pnl = await portfolio_svc.get_pnl(db, tenant_id, redis_client)
        positions = pnl.positions

        net_worth = pnl.total_portfolio_value
        total_invested = sum(p.total_cost for p in positions)

        total_return = net_worth - total_invested
        total_return_pct = (
            (total_return / total_invested * Decimal("100"))
            if total_invested > Decimal("0")
            else Decimal("0")
        )

        # data_stale: any position with stale price → mark summary stale
        data_stale = any(p.current_price_stale for p in positions)

        # Asset allocation — already grouped by class in pnl.allocation
        asset_allocation = [
            AllocationSummary(
                asset_class=item.asset_class,
                value=item.total_value,
                pct=item.percentage,
            )
            for item in pnl.allocation
        ]

        # Daily P&L: batch-fetch all quotes in ONE Redis round-trip
        enriched_tickers = [p.ticker for p in positions if p.current_price is not None]
        batch_quotes = await mds.get_quotes_batch(enriched_tickers) if enriched_tickers else {}

        daily_pnl = Decimal("0")
        for p in positions:
            if p.current_price is not None:
                quote = batch_quotes.get(p.ticker.upper())
                if quote and not quote.data_stale:
                    # previous_close = current_price - price_change
                    previous_close = quote.price - quote.change
                    daily_pnl += (quote.price - previous_close) * p.quantity

        daily_pnl_pct = (
            (daily_pnl / net_worth * Decimal("100"))
            if net_worth > Decimal("0")
            else Decimal("0")
        )

        # Recent transactions (last 10 buy/sell) — separate DB query (lightweight)
        result = await db.execute(
            select(Transaction)
            .where(Transaction.transaction_type.in_(["buy", "sell"]))
            .order_by(Transaction.transaction_date.desc())
            .limit(10)
        )
        recent_txs = [
            RecentTransaction(
                ticker=tx.ticker,
                type=str(tx.transaction_type.value) if hasattr(tx.transaction_type, "value") else str(tx.transaction_type),
                quantity=tx.quantity,
                unit_price=tx.unit_price,
                date=tx.transaction_date,
            )
            for tx in result.scalars().all()
        ]

        # Portfolio timeseries: monthly snapshots from earliest buy to today
        timeseries = await self._build_timeseries(db, positions)

        return DashboardSummaryResponse(
            net_worth=net_worth,
            total_invested=total_invested,
            total_return=total_return,
            total_return_pct=total_return_pct,
            daily_pnl=daily_pnl,
            daily_pnl_pct=daily_pnl_pct,
            data_stale=data_stale,
            asset_allocation=asset_allocation,
            portfolio_timeseries=timeseries,
            recent_transactions=recent_txs,
        )

    async def _build_timeseries(
        self,
        db: AsyncSession,
        positions,
    ) -> list[TimeseriesPoint]:
        """Build portfolio value timeseries for the dashboard chart.

        Strategy (two-tier):
        1. PRIMARY: read from portfolio_daily_value (populated nightly by Celery at 18h30 BRT).
           Returns last 90 days of real EOD market values.
        2. FALLBACK: if table is empty (user is new or Celery hasn't run yet), compute
           a cost-basis approximation from transaction history. Uses CMP as price proxy —
           shows cost trend rather than market value, but is honest about the limitation.
        """
        from sqlalchemy import text as _text
        from datetime import date as _date, timedelta as _timedelta

        # ── Primary: real EOD snapshots ───────────────────────────────────────
        since = _date.today() - _timedelta(days=90)
        snap_result = await db.execute(
            _text(
                "SELECT snapshot_date, total_value FROM portfolio_daily_value "
                "WHERE snapshot_date >= :since ORDER BY snapshot_date ASC"
            ),
            {"since": since},
        )
        snaps = snap_result.fetchall()

        if snaps:
            return [
                TimeseriesPoint(date=row[0], value=Decimal(str(row[1])))
                for row in snaps
            ]

        # ── Fallback: cost-basis approximation from transactions ───────────────
        # Used for new users whose first Celery snapshot hasn't run yet.
        result = await db.execute(
            select(Transaction)
            .where(Transaction.transaction_type.in_(["buy", "sell"]))
            .order_by(Transaction.transaction_date)
        )
        all_txs = result.scalars().all()
        if not all_txs:
            return []

        monthly_values: dict[str, Decimal] = {}
        running: dict[str, tuple[Decimal, Decimal]] = {}

        for tx in all_txs:
            month_key = tx.transaction_date.strftime("%Y-%m-01")
            ticker = tx.ticker
            qty = tx.quantity
            price = tx.unit_price
            prev_qty, prev_cost = running.get(ticker, (Decimal("0"), Decimal("0")))
            tx_type = str(tx.transaction_type.value) if hasattr(tx.transaction_type, "value") else str(tx.transaction_type)

            if tx_type == "buy":
                new_qty = prev_qty + qty
                new_cost = ((prev_qty * prev_cost) + (qty * price)) / new_qty if new_qty > 0 else price
                running[ticker] = (new_qty, new_cost)
            elif tx_type == "sell":
                running[ticker] = (max(Decimal("0"), prev_qty - qty), prev_cost)

            monthly_values[month_key] = sum(q * c for (q, c) in running.values())

        return [
            TimeseriesPoint(date=_date.fromisoformat(d), value=v)
            for d, v in sorted(monthly_values.items())
        ]
