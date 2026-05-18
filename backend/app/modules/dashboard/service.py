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
import math
import statistics
from collections import defaultdict
from decimal import Decimal
from datetime import date, timedelta
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.service import PortfolioService
from app.modules.market_data.service import MarketDataService
from app.modules.portfolio.models import Transaction
from app.modules.dashboard.schemas import (
    DashboardSummaryResponse,
    AllocationSummary,
    TimeseriesPoint,
    RecentTransaction,
    RiskMetricsResponse,
    StressScenario,
    SectorAllocationItem,
    SectorAllocationResponse,
    DividendEventItem,
    DividendCalendarResponse,
    DividendRankingItem,
    DividendRankingResponse,
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
            .where(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_type.in_(["buy", "sell"]),
                Transaction.deleted_at.is_(None),
            )
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
        timeseries = await self._build_timeseries(db, tenant_id, positions)

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
        tenant_id: str,
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
                "WHERE tenant_id = :tid AND snapshot_date >= :since ORDER BY snapshot_date ASC"
            ),
            {"tid": tenant_id, "since": since},
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
            .where(
                Transaction.tenant_id == tenant_id,
                Transaction.transaction_type.in_(["buy", "sell"]),
                Transaction.deleted_at.is_(None),
            )
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

    async def get_risk_metrics(
        self,
        db: AsyncSession,
        tenant_id: str,
        redis_client=None,
    ) -> RiskMetricsResponse:
        """Compute annualised risk metrics from the last 252 trading days of
        portfolio_daily_value snapshots for the given tenant.

        Returns data_available=False (with zeroed metrics) when fewer than 5
        data points exist — not enough to produce meaningful statistics.
        Sharpe ratio uses CDI as risk-free rate (read from Redis when available).
        """
        since = date.today() - timedelta(days=365)  # ~252 trading days in 1 year

        result = await db.execute(
            text(
                "SELECT total_value FROM portfolio_daily_value "
                "WHERE tenant_id = :tid AND snapshot_date >= :since "
                "ORDER BY snapshot_date ASC "
                "LIMIT 252"
            ),
            {"tid": tenant_id, "since": since},
        )
        rows = result.fetchall()
        values = [float(row[0]) for row in rows]

        _zero = Decimal("0")
        if len(values) < 5:
            return RiskMetricsResponse(
                volatility_annual_pct=_zero,
                max_drawdown_pct=_zero,
                positive_days_pct=_zero,
                trading_days=len(values),
                data_available=False,
            )

        # Daily returns: (v[i] / v[i-1]) - 1
        daily_returns = [
            (values[i] / values[i - 1]) - 1.0
            for i in range(1, len(values))
            if values[i - 1] != 0.0
        ]

        # Annualised volatility: stdev(daily_returns) * sqrt(252) * 100
        vol_annual = statistics.stdev(daily_returns) * math.sqrt(252) * 100.0

        # Max drawdown: max((peak - current) / peak) over the full window
        peak = values[0]
        max_dd = 0.0
        for v in values[1:]:
            if v > peak:
                peak = v
            if peak > 0.0:
                dd = (peak - v) / peak
                if dd > max_dd:
                    max_dd = dd
        max_drawdown = max_dd * 100.0

        # Positive days
        positive = sum(1 for r in daily_returns if r > 0)
        pos_pct = (positive / len(daily_returns) * 100.0) if daily_returns else 0.0

        # Annualised portfolio return over the full window
        annual_return: float | None = None
        sharpe: float | None = None
        n = len(daily_returns)
        if n >= 10 and values[0] > 0.0:
            cumulative = (values[-1] / values[0]) - 1.0
            annual_return = ((1.0 + cumulative) ** (252.0 / n) - 1.0) * 100.0

            # CDI from Redis as risk-free rate (percent p.a.)
            rf_pct: float = 14.4  # sensible default
            if redis_client is not None:
                try:
                    raw = await redis_client.get("market:macro:cdi")
                    if raw:
                        rf_pct = float(raw.decode() if isinstance(raw, bytes) else raw)
                except Exception:
                    pass

            vol_decimal = vol_annual / 100.0
            if vol_decimal > 0.0:
                sharpe = (annual_return - rf_pct) / (vol_decimal * 100.0)

        # ── VaR 95% (parametric, daily) ───────────────────────────────────────
        portfolio_value = Decimal(str(round(values[-1], 2)))
        daily_vol_decimal = (vol_annual / 100.0) / math.sqrt(252)
        var_95_pct = Decimal(str(round(daily_vol_decimal * 1.6449 * 100.0, 2)))
        var_95_brl = (portfolio_value * Decimal(str(round(daily_vol_decimal * 1.6449, 6)))).quantize(Decimal("0.01"))

        # ── Stress tests: query current asset class composition ───────────────
        stress_sql = text(
            """
            WITH holdings AS (
                SELECT asset_class, ticker,
                       SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE 0 END) -
                       SUM(CASE WHEN transaction_type = 'sell' THEN quantity ELSE 0 END) AS net_qty
                FROM transactions
                WHERE tenant_id = :tid AND transaction_type IN ('buy','sell')
                  AND deleted_at IS NULL
                GROUP BY asset_class, ticker
                HAVING SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE 0 END) -
                       SUM(CASE WHEN transaction_type = 'sell' THEN quantity ELSE 0 END) > 0
            ),
            latest_snaps AS (
                SELECT DISTINCT ON (ticker) ticker, regular_market_price
                FROM screener_snapshots ORDER BY ticker, snapshot_date DESC
            )
            SELECT h.asset_class,
                   SUM(h.net_qty * COALESCE(ls.regular_market_price, 0)) AS class_value
            FROM holdings h
            LEFT JOIN latest_snaps ls ON ls.ticker = h.ticker
            GROUP BY h.asset_class
            """
        )
        srow = await db.execute(stress_sql, {"tid": tenant_id})
        equity_v = fii_v = fi_v = crypto_v = 0.0
        for ac, val in srow.fetchall():
            v = float(val or 0)
            ac_s = str(ac or "").lower()
            if ac_s in ("acao", "etf", "bdr"):
                equity_v += v
            elif ac_s == "fii":
                fii_v += v
            elif ac_s in ("renda_fixa", "tesouro_direto"):
                fi_v += v
            elif ac_s == "crypto":
                crypto_v += v

        pv = float(portfolio_value) or 1.0

        def _scenario(label: str, assumption: str, impact_brl: float) -> StressScenario:
            pct = (impact_brl / pv * 100.0) if pv else 0.0
            return StressScenario(
                label=label,
                assumption=assumption,
                impact_brl=Decimal(str(round(impact_brl, 2))),
                impact_pct=Decimal(str(round(pct, 2))),
            )

        stress_scenarios = [
            _scenario(
                "Ibov −20%",
                "Ações/ETFs −20%, FIIs −12%",
                -(equity_v * 0.20 + fii_v * 0.12),
            ),
            _scenario(
                "SELIC +200bps",
                "RF (duration 2a) −4%, FIIs −3%",
                -(fi_v * 0.04 + fii_v * 0.03),
            ),
            _scenario(
                "BRL −15%",
                "Cripto −5% (correlação parcial)",
                -(crypto_v * 0.05),
            ),
        ]

        return RiskMetricsResponse(
            volatility_annual_pct=Decimal(str(round(vol_annual, 2))),
            max_drawdown_pct=Decimal(str(round(max_drawdown, 2))),
            positive_days_pct=Decimal(str(round(pos_pct, 2))),
            annual_return_pct=Decimal(str(round(annual_return, 2))) if annual_return is not None else None,
            sharpe_ratio=Decimal(str(round(sharpe, 3))) if sharpe is not None else None,
            var_95_pct=var_95_pct,
            var_95_brl=var_95_brl,
            stress_scenarios=stress_scenarios,
            portfolio_value_brl=portfolio_value,
            trading_days=len(values),
            data_available=True,
        )

    async def get_sector_allocation(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> SectorAllocationResponse:
        """Compute sector allocation by joining current holdings with latest
        screener snapshot prices and fii_metadata for FII segmento labels.

        Falls back to asset_class when neither screener nor fii_metadata has a
        sector/segmento for a given ticker.
        """
        sql = text(
            """
            WITH holdings AS (
                SELECT ticker, asset_class,
                       SUM(CASE WHEN transaction_type IN ('buy') THEN quantity ELSE 0 END) -
                       SUM(CASE WHEN transaction_type IN ('sell') THEN quantity ELSE 0 END) AS shares
                FROM transactions
                WHERE tenant_id = :tid
                  AND transaction_type IN ('buy', 'sell')
                  AND deleted_at IS NULL
                GROUP BY ticker, asset_class
            ),
            latest_snap_date AS (
                SELECT MAX(snapshot_date) AS dt FROM screener_snapshots
            ),
            latest_snap AS (
                SELECT s.ticker, s.sector, s.regular_market_price
                FROM screener_snapshots s
                INNER JOIN latest_snap_date ON s.snapshot_date = latest_snap_date.dt
            )
            SELECT
                COALESCE(ls.sector, fm.segmento, h.asset_class::text) AS sector,
                SUM(h.shares * COALESCE(ls.regular_market_price, 0)) AS total_value
            FROM holdings h
            LEFT JOIN latest_snap ls ON ls.ticker = h.ticker
            LEFT JOIN fii_metadata fm ON fm.ticker = h.ticker
            WHERE h.shares > 0
            GROUP BY COALESCE(ls.sector, fm.segmento, h.asset_class::text)
            ORDER BY total_value DESC
            """
        )

        result = await db.execute(sql, {"tid": tenant_id})
        rows = result.fetchall()

        grand_total = sum(float(row[1]) for row in rows) if rows else 0.0

        sectors: list[SectorAllocationItem] = []
        for row in rows:
            sector_label = str(row[0]) if row[0] is not None else "Outros"
            val = float(row[1])
            pct = (val / grand_total * 100.0) if grand_total > 0.0 else 0.0
            sectors.append(
                SectorAllocationItem(
                    sector=sector_label,
                    value=Decimal(str(round(val, 2))),
                    pct=Decimal(str(round(pct, 2))),
                )
            )

        return SectorAllocationResponse(sectors=sectors)

    async def get_dividend_calendar(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> DividendCalendarResponse:
        """Return upcoming dividend payments (next 90 days) for the user's portfolio.

        Fetches dividend data from brapi.dev for each held ticker and merges with
        the user's actual share quantities to compute estimated income.
        Returns an empty response gracefully if brapi is unavailable.
        """
        import asyncio
        import os
        from datetime import date as _date
        from app.modules.market_data.adapters.brapi import BrapiClient

        # 1. Get current holdings (tickers with net positive shares)
        sql = text(
            """
            SELECT ticker, asset_class,
                   SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE 0 END) -
                   SUM(CASE WHEN transaction_type = 'sell' THEN quantity ELSE 0 END) AS shares
            FROM transactions
            WHERE tenant_id = :tid AND transaction_type IN ('buy', 'sell')
              AND deleted_at IS NULL
            GROUP BY ticker, asset_class
            HAVING SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE 0 END) -
                   SUM(CASE WHEN transaction_type = 'sell' THEN quantity ELSE 0 END) > 0
            """
        )
        result = await db.execute(sql, {"tid": tenant_id})
        rows = result.fetchall()

        if not rows:
            return DividendCalendarResponse(events=[], data_available=False)

        # Build holdings map: ticker -> (asset_class, shares)
        holdings: dict[str, tuple[str, Decimal]] = {}
        for row in rows:
            ticker = str(row[0])
            asset_class = str(row[1]) if row[1] else ""
            shares = Decimal(str(row[2]))
            holdings[ticker] = (asset_class, shares)

        # 2. Fetch dividend data from brapi for each ticker
        brapi = BrapiClient(token=os.environ.get("BRAPI_TOKEN", ""))
        today = _date.today()
        cutoff = _date.fromordinal(today.toordinal() + 90)

        events: list[DividendEventItem] = []

        for ticker, (asset_class, shares) in holdings.items():
            try:
                dividends = await asyncio.to_thread(brapi.fetch_dividends, ticker)
            except Exception as exc:
                logger.warning("get_dividend_calendar: brapi failed for %s — %s", ticker, exc)
                continue

            for d in dividends:
                payment_date_str = d.get("paymentDate", "") or ""
                ex_date_str = d.get("lastDatePrior", "") or ""

                # Filter to next 90 days (keep events with unparseable dates)
                if payment_date_str:
                    try:
                        payment_dt = _date.fromisoformat(payment_date_str)
                        # Skip past events and events beyond 90-day window
                        if payment_dt < today or payment_dt > cutoff:
                            continue
                    except (ValueError, TypeError):
                        pass  # Keep events with unparseable dates

                rate_per_share = Decimal(str(d.get("rate", 0) or 0))
                estimated_income = rate_per_share * shares

                events.append(
                    DividendEventItem(
                        ticker=ticker,
                        asset_class=asset_class,
                        payment_date=payment_date_str,
                        ex_date=ex_date_str,
                        rate_per_share=rate_per_share,
                        quantity=shares,
                        estimated_income=estimated_income,
                        label=d.get("label", "Dividendo") or "Dividendo",
                    )
                )

        # 3. Sort by payment_date ascending (empty dates go last)
        events.sort(key=lambda e: (e.payment_date == "", e.payment_date))

        return DividendCalendarResponse(events=events, data_available=len(events) > 0)

    async def get_dividend_ranking(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> DividendRankingResponse:
        """Return portfolio holdings ranked by dividend yield (DY from screener_snapshots).

        Uses the latest available screener snapshot for each ticker.
        Position value = quantity * screener price (same source as sector allocation).
        DY comes from screener_snapshots.dy (trailing 12m, in decimal: 0.12 = 12%).
        """
        sql = text(
            """
            WITH latest_snaps AS (
                SELECT DISTINCT ON (ticker)
                    ticker, dy, regular_market_price, sector
                FROM screener_snapshots
                ORDER BY ticker, snapshot_date DESC
            ),
            holdings AS (
                SELECT ticker,
                    SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE 0 END)
                  - SUM(CASE WHEN transaction_type = 'sell' THEN quantity ELSE 0 END) AS net_qty
                FROM transactions
                WHERE tenant_id = :tid
                  AND asset_class IN ('acao','fii','etf','bdr','crypto')
                  AND deleted_at IS NULL
                GROUP BY ticker
                HAVING SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE 0 END)
                     - SUM(CASE WHEN transaction_type = 'sell' THEN quantity ELSE 0 END) > 0
            )
            SELECT h.ticker,
                   COALESCE(s.dy, 0)                          AS dy,
                   h.net_qty * COALESCE(s.regular_market_price, 0) AS position_value,
                   s.sector
            FROM holdings h
            LEFT JOIN latest_snaps s ON s.ticker = h.ticker
            WHERE s.dy IS NOT NULL AND s.dy > 0
            ORDER BY s.dy DESC
            LIMIT 20
            """
        )
        result = await db.execute(sql, {"tid": tenant_id})
        rows = result.fetchall()

        if not rows:
            return DividendRankingResponse(items=[], total_estimated_annual=Decimal("0"), data_available=False)

        items = []
        total = Decimal("0")
        for ticker, dy_raw, pos_val_raw, sector in rows:
            dy = Decimal(str(dy_raw or 0))
            pos_val = Decimal(str(pos_val_raw or 0))
            # dy in screener is already a percentage (e.g., 12.5 = 12.5%)
            # Normalize: if dy > 1 treat as percent already; if < 1 treat as decimal fraction
            dy_pct = dy if dy > Decimal("1") else dy * Decimal("100")
            estimated_annual = (dy_pct / Decimal("100")) * pos_val
            total += estimated_annual
            items.append(DividendRankingItem(
                ticker=str(ticker),
                dy_pct=dy_pct.quantize(Decimal("0.01")),
                position_value=pos_val.quantize(Decimal("0.01")),
                estimated_annual=estimated_annual.quantize(Decimal("0.01")),
                sector=sector,
            ))

        return DividendRankingResponse(
            items=items,
            total_estimated_annual=total.quantize(Decimal("0.01")),
            data_available=True,
        )
