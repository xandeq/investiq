"""PortfolioService — assembles CMP engine + market data service + DB persistence.

This module bridges:
- app.modules.portfolio.cmp (pure CMP calculation)
- app.modules.market_data.service (Redis cache reads)
- SQLAlchemy AsyncSession (DB persistence)

RLS is enforced at the DB level via get_authed_db — service receives
a pre-scoped session and does NOT call SET LOCAL itself.

Design: Methods accept redis_client=None — when None, positions are returned
without price enrichment (current_price_stale=True). This enables tests and
offline use without a running Redis.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.portfolio.models import Transaction, CorporateAction
from app.modules.portfolio.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    TransactionListParams,
    PositionResponse,
    PnLResponse,
    AllocationItem,
    BenchmarkResponse,
    DividendResponse,
)
from app.modules.portfolio.cmp import build_position_from_history


async def calculate(data: dict) -> dict:
    """EXT-03 interface: financial skill adapter entry point.

    Phase 1 skeleton — kept for backward compatibility with test_schema.py.
    Phase 4 will dispatch to skill-specific calculators based on data["skill"].

    Args:
        data: Dict containing transaction data and skill identifier.

    Returns:
        Dict with calculation results.
    """
    return {"status": "not_implemented", "input": data}


class PortfolioService:
    """Service layer for portfolio operations.

    All public methods are async and accept an AsyncSession that has
    already been RLS-scoped by get_authed_db. Never call SET LOCAL here.
    """

    async def create_transaction(
        self,
        db: AsyncSession,
        tenant_id: str,
        data: TransactionCreate,
    ) -> Transaction:
        """Insert transaction row. Returns the persisted Transaction.

        Computes total_value from quantity × unit_price + brokerage_fee.
        tenant_id and portfolio_id (v1: same value) are set server-side.
        """
        total_value = data.quantity * data.unit_price
        if data.brokerage_fee:
            total_value += data.brokerage_fee

        tx = Transaction(
            tenant_id=tenant_id,
            portfolio_id=tenant_id,  # v1: portfolio_id == tenant_id
            ticker=data.ticker.upper(),
            asset_class=data.asset_class,
            transaction_type=data.transaction_type,
            transaction_date=data.transaction_date,
            quantity=data.quantity,
            unit_price=data.unit_price,
            total_value=total_value,
            brokerage_fee=data.brokerage_fee,
            coupon_rate=data.coupon_rate,
            maturity_date=data.maturity_date,
            is_exempt=data.is_exempt,
            notes=data.notes,
        )
        db.add(tx)
        await db.flush()  # assign ID without committing (session commits on exit)
        return tx

    async def get_positions(
        self,
        db: AsyncSession,
        tenant_id: str,
        redis_client=None,
    ) -> list[PositionResponse]:
        """Calculate current positions for the tenant's portfolio.

        Loads all buy/sell transactions from DB, applies CMP engine,
        enriches with current price from Redis (data_stale=True if cache empty).

        Tickers with zero quantity after sells are excluded from the response.
        """
        # Load all buy + sell transactions ordered chronologically (exclude soft-deleted)
        result = await db.execute(
            select(Transaction).where(
                Transaction.transaction_type.in_(["buy", "sell"]),
                Transaction.deleted_at.is_(None),
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()

        # Load corporate actions for CMP calculation
        ca_result = await db.execute(
            select(CorporateAction).order_by(CorporateAction.action_date)
        )
        corporate_actions = ca_result.scalars().all()

        # Group transactions by ticker
        tickers: dict[str, list] = {}
        for tx in txs:
            tickers.setdefault(tx.ticker, []).append(tx)

        positions: list[PositionResponse] = []

        for ticker, ticker_txs in tickers.items():
            ticker_cas = [ca for ca in corporate_actions if ca.ticker == ticker]
            asset_class = ticker_txs[0].asset_class

            try:
                pos = build_position_from_history(
                    ticker,
                    str(asset_class.value) if hasattr(asset_class, "value") else str(asset_class),
                    ticker_txs,
                    ticker_cas,
                )
            except ValueError as exc:
                import logging as _logging
                _logging.getLogger(__name__).warning(
                    "Skipping ticker %s — CMP calculation error: %s", ticker, exc
                )
                continue

            # Skip fully-sold positions
            if pos.quantity <= Decimal("0"):
                continue

            # Enrich with Redis price if available
            current_price: Decimal | None = None
            price_stale = True
            unrealized_pnl: Decimal | None = None
            unrealized_pnl_pct: Decimal | None = None

            if redis_client is not None:
                from app.modules.market_data.service import MarketDataService
                mds = MarketDataService(redis_client)
                quote = await mds.get_quote(ticker)
                if not quote.data_stale:
                    current_price = quote.price
                    price_stale = False
                    unrealized_pnl = (quote.price - pos.cmp) * pos.quantity
                    if pos.total_cost > Decimal("0"):
                        unrealized_pnl_pct = (unrealized_pnl / pos.total_cost) * Decimal("100")

            positions.append(PositionResponse(
                ticker=ticker,
                asset_class=pos.asset_class,
                quantity=pos.quantity,
                cmp=pos.cmp,
                total_cost=pos.total_cost,
                current_price=current_price,
                current_price_stale=price_stale,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
            ))

        return positions

    async def get_pnl(
        self,
        db: AsyncSession,
        tenant_id: str,
        redis_client=None,
    ) -> PnLResponse:
        """Compute portfolio-level P&L and allocation breakdown by asset class.

        Realized P&L = sum of gross_profit stored on sell transactions.
        Unrealized P&L = sum of (current_price - cmp) × quantity per position.
        Allocation = percentage of total portfolio value per asset class.
        """
        positions = await self.get_positions(db, tenant_id, redis_client)

        # Realized P&L from sell transactions (gross_profit stored at write time, exclude deleted)
        sell_result = await db.execute(
            select(Transaction).where(
                Transaction.transaction_type == "sell",
                Transaction.deleted_at.is_(None),
            )
        )
        sell_txs = sell_result.scalars().all()
        realized_total = sum(
            (tx.gross_profit or Decimal("0")) for tx in sell_txs
        )

        unrealized_total = sum(
            (p.unrealized_pnl or Decimal("0")) for p in positions
        )

        # Total portfolio value: use current_price if available, else fall back to CMP
        total_portfolio_value = sum(
            (p.current_price or p.cmp) * p.quantity for p in positions
        )

        # Allocation breakdown by asset class
        class_totals: dict[str, Decimal] = {}
        for p in positions:
            val = (p.current_price or p.cmp) * p.quantity
            class_totals[p.asset_class] = class_totals.get(p.asset_class, Decimal("0")) + val

        allocation: list[AllocationItem] = []
        for ac, val in class_totals.items():
            pct = (
                (val / total_portfolio_value * Decimal("100"))
                if total_portfolio_value > Decimal("0")
                else Decimal("0")
            )
            allocation.append(AllocationItem(asset_class=ac, total_value=val, percentage=pct))

        return PnLResponse(
            positions=positions,
            realized_pnl_total=realized_total,
            unrealized_pnl_total=unrealized_total,
            total_portfolio_value=total_portfolio_value,
            allocation=allocation,
        )

    async def get_benchmarks(self, redis_client) -> BenchmarkResponse:
        """Read CDI and IBOVESPA benchmark values from Redis.

        Returns BenchmarkResponse with None values when cache is stale.
        data_stale=True if either the macro cache or IBOVESPA quote is stale.
        """
        from app.modules.market_data.service import MarketDataService
        mds = MarketDataService(redis_client)
        macro = await mds.get_macro()
        ibov = await mds.get_quote("IBOV")

        return BenchmarkResponse(
            cdi=macro.cdi if not macro.data_stale else None,
            ibovespa_price=ibov.price if not ibov.data_stale else None,
            data_stale=macro.data_stale or ibov.data_stale,
            fetched_at=macro.fetched_at if not macro.data_stale else None,
        )

    async def list_transactions(
        self,
        db: AsyncSession,
        tenant_id: str,
        params: TransactionListParams,
    ) -> list[Transaction]:
        """Return all non-deleted transactions with optional filters."""
        stmt = select(Transaction).where(Transaction.deleted_at.is_(None))

        if params.ticker:
            stmt = stmt.where(Transaction.ticker == params.ticker.upper())
        if params.asset_class:
            stmt = stmt.where(Transaction.asset_class == params.asset_class)
        if params.transaction_type:
            stmt = stmt.where(Transaction.transaction_type == params.transaction_type)
        if params.date_from:
            stmt = stmt.where(Transaction.transaction_date >= params.date_from)
        if params.date_to:
            stmt = stmt.where(Transaction.transaction_date <= params.date_to)

        stmt = stmt.order_by(Transaction.transaction_date.desc()).limit(params.limit).offset(params.offset)
        result = await db.execute(stmt)
        return result.scalars().all()

    async def update_transaction(
        self,
        db: AsyncSession,
        tenant_id: str,
        transaction_id: str,
        data: TransactionUpdate,
    ) -> Transaction | None:
        """Partially update an existing transaction. Returns None if not found."""
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.deleted_at.is_(None),
            )
        )
        tx = result.scalar_one_or_none()
        if tx is None:
            return None

        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(tx, field, value)

        # Recompute total_value if price or quantity changed
        if data.quantity is not None or data.unit_price is not None:
            tx.total_value = tx.quantity * tx.unit_price
            if tx.brokerage_fee:
                tx.total_value += tx.brokerage_fee

        await db.flush()
        return tx

    async def delete_transaction(
        self,
        db: AsyncSession,
        tenant_id: str,
        transaction_id: str,
    ) -> bool:
        """Soft-delete a transaction. Returns True if found and deleted."""
        result = await db.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.deleted_at.is_(None),
            )
        )
        tx = result.scalar_one_or_none()
        if tx is None:
            return False

        tx.deleted_at = datetime.now(tz=timezone.utc)
        await db.flush()
        return True

    async def bulk_delete_transactions(
        self,
        db: AsyncSession,
        ids: list[str],
    ) -> int:
        """Soft-delete multiple transactions. Returns count of deleted rows."""
        from sqlalchemy import update
        result = await db.execute(
            update(Transaction)
            .where(
                Transaction.id.in_(ids),
                Transaction.deleted_at.is_(None),
            )
            .values(deleted_at=datetime.now(tz=timezone.utc))
        )
        await db.commit()
        return result.rowcount

    async def get_dividends(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> list[DividendResponse]:
        """Return dividend, JSCP, and amortization transactions ordered by date desc."""
        result = await db.execute(
            select(Transaction).where(
                Transaction.transaction_type.in_(["dividend", "jscp", "amortization"]),
                Transaction.deleted_at.is_(None),
            ).order_by(Transaction.transaction_date.desc())
        )
        txs = result.scalars().all()
        return [DividendResponse.model_validate(tx) for tx in txs]
