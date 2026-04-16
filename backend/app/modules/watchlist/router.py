"""Watchlist router.

Endpoints:
  GET    /watchlist            — list all watchlist items
  POST   /watchlist            — add a ticker to watchlist
  DELETE /watchlist/{ticker}   — remove a ticker from watchlist
  PATCH  /watchlist/{ticker}   — update notes or price alert
  GET    /watchlist/quotes     — get live quotes for watchlist items
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.watchlist.models import WatchlistItem
from app.modules.watchlist.schemas import WatchlistItemCreate, WatchlistItemResponse, WatchlistItemUpdate

router = APIRouter()


def _get_redis():
    import redis.asyncio as aioredis
    from app.core.config import settings
    return aioredis.from_url(settings.REDIS_URL, decode_responses=False)


@router.get("", response_model=list[WatchlistItemResponse])
async def list_watchlist(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> list[WatchlistItemResponse]:
    result = await db.execute(
        select(WatchlistItem)
        .where(WatchlistItem.tenant_id == tenant_id)
        .order_by(WatchlistItem.created_at.desc())
    )
    items = result.scalars().all()
    return [WatchlistItemResponse.model_validate(i) for i in items]


@router.post("", response_model=WatchlistItemResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    data: WatchlistItemCreate,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> WatchlistItemResponse:
    ticker = data.ticker.upper()
    # Check for duplicate
    existing = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.ticker == ticker,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"{ticker} já está na watchlist.")

    item = WatchlistItem(
        tenant_id=tenant_id,
        ticker=ticker,
        notes=data.notes,
        price_alert_target=data.price_alert_target,
    )
    db.add(item)
    await db.flush()
    return WatchlistItemResponse.model_validate(item)


@router.delete("/{ticker}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    ticker: str,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> Response:
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.ticker == ticker.upper(),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Ticker não encontrado na watchlist.")
    await db.delete(item)
    return Response(status_code=204)


@router.patch("/{ticker}", response_model=WatchlistItemResponse)
async def update_watchlist_item(
    ticker: str,
    data: WatchlistItemUpdate,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> WatchlistItemResponse:
    result = await db.execute(
        select(WatchlistItem).where(
            WatchlistItem.tenant_id == tenant_id,
            WatchlistItem.ticker == ticker.upper(),
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Ticker não encontrado na watchlist.")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.flush()
    return WatchlistItemResponse.model_validate(item)


@router.get("/quotes", response_model=list[dict])
async def get_watchlist_quotes(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
    redis=Depends(_get_redis),
) -> list[dict]:
    """Return live quotes + fundamentals for all watchlist items."""
    result = await db.execute(
        select(WatchlistItem).where(WatchlistItem.tenant_id == tenant_id)
    )
    items = result.scalars().all()
    if not items:
        return []

    from app.modules.market_data.service import MarketDataService
    mds = MarketDataService(redis)

    # Batch-fetch all quotes + fundamentals (one pipeline per data type)
    tickers = [item.ticker for item in items]
    quote_results = await mds.get_quotes_batch(tickers)
    fundamentals_results = await mds.get_fundamentals_batch(tickers)

    quotes = []
    for item in items:
        quote = quote_results.get(item.ticker)
        fundamentals = fundamentals_results.get(item.ticker)
        try:
            quotes.append({
                "ticker": item.ticker,
                "notes": item.notes,
                "price_alert_target": str(item.price_alert_target) if item.price_alert_target else None,
                "alert_triggered_at": item.alert_triggered_at.isoformat() if item.alert_triggered_at else None,
                "price": str(quote.price) if quote and not quote.data_stale else None,
                "data_stale": quote.data_stale if quote else True,
                "pl": str(fundamentals.pl) if fundamentals and not fundamentals.data_stale and fundamentals.pl else None,
                "dy": str(fundamentals.dy) if fundamentals and not fundamentals.data_stale and fundamentals.dy else None,
                "pvp": str(fundamentals.pvp) if fundamentals and not fundamentals.data_stale and fundamentals.pvp else None,
            })
        except Exception:
            quotes.append({
                "ticker": item.ticker,
                "notes": item.notes,
                "price_alert_target": str(item.price_alert_target) if item.price_alert_target else None,
                "alert_triggered_at": item.alert_triggered_at.isoformat() if item.alert_triggered_at else None,
                "price": None,
                "data_stale": True,
            })
    return quotes
