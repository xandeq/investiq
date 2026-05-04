"""Portfolio API router.

All endpoints require authentication (get_authed_db enforces JWT + RLS).
Market data enrichment uses Redis via MarketDataService — never calls external APIs.

Endpoints:
  POST /portfolio/transactions         — record buy/sell/dividend/renda_fixa/BDR/ETF
  GET  /portfolio/positions            — current holdings with CMP + Redis price
  GET  /portfolio/pnl                  — portfolio P&L and allocation by asset class
  GET  /portfolio/benchmarks           — CDI + IBOVESPA from Redis
  GET  /portfolio/dividends            — dividend/JSCP history

Design: _get_redis() is a separate dependency function so tests can override it
via app.dependency_overrides[_get_redis]. Never import redis at module level —
import lazily inside the factory to avoid startup errors when Redis is not
configured (e.g., test environments with fakeredis).
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.plan_gate import get_user_plan, require_transaction_slot
from app.modules.portfolio.models import AssetClass, TransactionType
from app.modules.portfolio.schemas import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
    TransactionListParams,
    BulkDeleteRequest,
    PositionResponse,
    PnLResponse,
    BenchmarkResponse,
    DividendResponse,
)
from app.modules.portfolio.service import PortfolioService

router = APIRouter()


def _get_service() -> PortfolioService:
    """Dependency: return a PortfolioService instance (stateless, no deps)."""
    return PortfolioService()


def _get_redis():
    """Dependency: async Redis client for market data enrichment.

    Override this in tests via app.dependency_overrides[_get_redis].
    Returns an async Redis client connected to settings.REDIS_URL.
    """
    import redis.asyncio as aioredis
    from app.core.config import settings
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


@router.post(
    "/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_transaction(
    data: TransactionCreate,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    plan: str = Depends(get_user_plan),
    service: PortfolioService = Depends(_get_service),
) -> TransactionResponse:
    """Record a new portfolio transaction.

    Supports all asset types: acao, FII, renda_fixa, BDR, ETF.
    Transaction types: buy, sell, dividend, jscp, amortization.

    Free tier: limited to 50 total transactions. Returns 403 when limit reached.

    CMP recalculation is performed on GET /positions (stateless read path),
    not at write time — this keeps the write path simple and consistent.
    """
    await require_transaction_slot(plan, tenant_id, db)
    tx = await service.create_transaction(db, tenant_id, data)
    return TransactionResponse.model_validate(tx)


@router.get("/positions", response_model=list[PositionResponse])
async def get_positions(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
    redis=Depends(_get_redis),
) -> list[PositionResponse]:
    """Return all current holdings with CMP and live Redis price enrichment.

    Positions with zero quantity (fully sold) are excluded.
    When Redis cache is empty, current_price_stale=True and current_price=None.
    Transaction recording is NEVER blocked by a missing Redis quote.
    """
    return await service.get_positions(db, tenant_id, redis)


@router.get("/pnl", response_model=PnLResponse)
async def get_pnl(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
    redis=Depends(_get_redis),
) -> PnLResponse:
    """Return portfolio-level P&L and allocation breakdown by asset class.

    realized_pnl_total: sum of gross_profit from sell transactions.
    unrealized_pnl_total: sum of (current_price - cmp) × quantity.
    allocation: list of {asset_class, total_value, percentage} sorted by value.
    """
    return await service.get_pnl(db, tenant_id, redis)


@router.get("/benchmarks", response_model=BenchmarkResponse)
async def get_benchmarks(
    _authed_db: AsyncSession = Depends(get_authed_db),
    service: PortfolioService = Depends(_get_service),
    redis=Depends(_get_redis),
) -> BenchmarkResponse:
    """Return CDI rate and IBOVESPA price from Redis macro/quote cache.

    Requires authentication (market data is tenant-agnostic but auth-gated).
    Returns data_stale=True when the Celery cache has not been populated yet.
    """
    return await service.get_benchmarks(redis)


@router.get("/transactions", response_model=list[TransactionResponse])
async def list_transactions(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
    ticker: str | None = Query(None),
    asset_class: AssetClass | None = Query(None),
    transaction_type: TransactionType | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[TransactionResponse]:
    """List all transactions with optional filters.

    Supports filtering by ticker, asset_class, transaction_type, and date range.
    Excludes soft-deleted transactions. Ordered by transaction_date descending.
    """
    from datetime import date as date_type
    params = TransactionListParams(
        ticker=ticker,
        asset_class=asset_class,
        transaction_type=transaction_type,
        date_from=date_type.fromisoformat(date_from) if date_from else None,
        date_to=date_type.fromisoformat(date_to) if date_to else None,
        limit=limit,
        offset=offset,
    )
    txs = await service.list_transactions(db, tenant_id, params)
    return [TransactionResponse.model_validate(tx) for tx in txs]


@router.patch("/transactions/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
) -> TransactionResponse:
    """Partially update a transaction.

    Only provided fields are updated. Recalculates total_value when
    quantity or unit_price changes.
    """
    tx = await service.update_transaction(db, tenant_id, transaction_id, data)
    if tx is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return TransactionResponse.model_validate(tx)


@router.delete("/transactions/bulk", status_code=200)
async def bulk_delete_transactions(
    body: BulkDeleteRequest,
    db: AsyncSession = Depends(get_authed_db),
    service: PortfolioService = Depends(_get_service),
) -> dict:
    """Soft-delete multiple transactions by ID list.

    Accepts a JSON body with an 'ids' list of transaction UUIDs.
    Returns count of rows actually deleted (excludes already-deleted rows).
    Route declared BEFORE /{transaction_id} so FastAPI matches it first.
    """
    count = await service.bulk_delete_transactions(db, body.ids)
    return {"deleted": count}


@router.delete("/transactions/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
) -> Response:
    """Soft-delete a transaction.

    The transaction is not removed from the database — deleted_at is set.
    This preserves IR audit trail. Positions and P&L queries exclude deleted rows.
    """
    deleted = await service.delete_transaction(db, tenant_id, transaction_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return Response(status_code=204)


@router.delete("/transactions", status_code=200)
async def clear_all_transactions(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
) -> dict:
    """Soft-delete ALL active transactions for the authenticated tenant.

    This is the 'Limpar carteira' (clear portfolio) action. All transactions
    are soft-deleted (deleted_at set), preserving IR audit history.
    Returns the count of deleted transactions.
    """
    count = await service.clear_all_transactions(db, tenant_id)
    return {"deleted": count, "message": f"Carteira limpa: {count} transação(ões) removida(s)"}


@router.post("/transactions/revert-import/{import_job_id}", status_code=200)
async def revert_import(
    import_job_id: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
) -> dict:
    """Soft-delete all transactions created by a specific import job.

    Allows the user to undo a specific import without losing other data.
    Returns the count of deleted transactions.
    """
    count = await service.revert_import(db, tenant_id, import_job_id)
    return {"deleted": count, "message": f"Import revertido: {count} transação(ões) removida(s)"}


@router.get("/dividends", response_model=list[DividendResponse])
async def get_dividends(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    service: PortfolioService = Depends(_get_service),
) -> list[DividendResponse]:
    """Return dividend, JSCP, and amortization transaction history.

    Ordered by transaction_date descending (most recent first).
    Includes FII dividend exemption flag (is_exempt) for IR calculations.
    """
    return await service.get_dividends(db, tenant_id)
