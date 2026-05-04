"""FastAPI router for /signals endpoints.

GET  /signals/active            — list active A+ signals from Redis (auth required)
GET  /signals/{ticker}/evaluate — on-demand evaluation for a specific ticker
POST /signals/sizing            — calculate Kelly fractional position size
"""
import logging
import os

import redis.asyncio as aioredis
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.chart_analyzer.analyzer import analyze
from app.modules.signal_engine.gates import evaluate_signal
from app.modules.signal_engine.kelly import calculate_position_size
from app.modules.signal_engine.scanner import get_active_signals

logger = logging.getLogger(__name__)

router = APIRouter()


def _get_async_redis():
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    try:
        return aioredis.from_url(url, decode_responses=True)
    except Exception as exc:
        logger.warning("signal_engine router: Redis unavailable: %s", exc)
        return None


@router.get("/active")
@limiter.limit("30/minute")
async def list_active_signals(
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """Return current A+ signals cached in Redis.

    Returns an empty list if no signals are available (scanner hasn't run yet
    or market is closed).
    """
    redis_client = _get_async_redis()
    try:
        signals = await get_active_signals(redis_client)
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    return {"signals": signals, "count": len(signals)}


@router.get("/{ticker}/evaluate")
@limiter.limit("20/minute")
async def evaluate_ticker_signal(
    request: Request,
    ticker: str,
    current_user: dict = Depends(get_current_user),
):
    """On-demand A+ gate evaluation for a specific B3 ticker.

    Runs a full chart analysis and applies all 10 gates. Useful for
    evaluating tickers outside the default UNIVERSE.
    """
    ticker = ticker.upper()
    if not ticker or len(ticker) > 10:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ticker")

    brapi_token = os.environ.get("BRAPI_TOKEN", "")

    redis_client = _get_async_redis()
    try:
        analysis = await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
    finally:
        if redis_client is not None:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    if analysis.get("error") and not analysis.get("indicators"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to analyze {ticker}: {analysis['error']}",
        )

    evaluation = evaluate_signal(ticker, analysis)

    return {
        "ticker": ticker,
        "grade": evaluation.grade,
        "score": evaluation.score,
        "passed_gates": evaluation.passed_gates,
        "total_gates": evaluation.total_gates,
        "is_a_plus": evaluation.is_a_plus,
        "setup": evaluation.setup,
        "gates": [
            {
                "gate_name": g.gate_name,
                "passed": g.passed,
                "value": g.value,
                "threshold": g.threshold,
                "reason": g.reason,
            }
            for g in evaluation.gates
        ],
    }


class SizingRequest(BaseModel):
    book_value: Decimal
    entry: Decimal
    stop: Decimal
    win_rate: float = 0.5
    avg_win_r: float = 2.5
    open_positions: int = 0
    daily_pnl_pct: float = 0.0


@router.post("/sizing")
@limiter.limit("20/minute")
async def calculate_sizing(
    request: Request,
    body: SizingRequest,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Calculate Kelly fractional position size with risk guardrails.

    Returns allocation fraction, BRL amount, share count, and any blocking
    reasons (drawdown limit, max open positions).
    """
    result = calculate_position_size(
        book_value=body.book_value,
        entry=body.entry,
        stop=body.stop,
        win_rate=body.win_rate,
        avg_win_r=body.avg_win_r,
        open_positions=body.open_positions,
        daily_pnl_pct=body.daily_pnl_pct,
    )
    # Convert Decimal to float for JSON serialization
    result["amount_brl"] = float(result["amount_brl"])
    return result
