"""FII Scored Screener endpoint — read-only from pre-calculated scores.

GET /fii-screener/ranked — returns all FIIs with composite score, sorted desc.
No pagination needed (universe ~400 rows). Filtering done client-side.

Score formula (nightly Celery task):
  score = DY_rank*0.5 + PVP_rank_inverted*0.3 + liquidity_rank*0.2

FIIs with NULL scores (missing data) appear at the bottom (NULLS LAST).
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func as sa_func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.fii_screener.schemas import FIIScoredResponse, FIIScoredRow
from app.modules.market_universe.models import FIIMetadata, ScreenerSnapshot

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/ranked",
    response_model=FIIScoredResponse,
    summary="FIIs ranqueados por score composto (DY 12m + P/VP + Liquidez)",
    tags=["fii-screener"],
)
@limiter.limit("30/minute")
async def get_ranked_fiis(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> FIIScoredResponse:
    """Return all FIIs ordered by composite score descending (NULLS LAST).

    Results come exclusively from the pre-built fii_metadata table — no external
    API calls at request time. Score is updated nightly by the calculate_fii_scores
    Celery task at 08:00 BRT.

    Client-side filtering by segmento and dy_12m is expected (no server-side filtering).
    """
    # Subquery for latest snapshot date (to get short_name from screener_snapshots)
    latest_sub = select(
        sa_func.max(ScreenerSnapshot.snapshot_date)
    ).scalar_subquery()

    stmt = (
        select(FIIMetadata, ScreenerSnapshot.short_name)
        .outerjoin(
            ScreenerSnapshot,
            (FIIMetadata.ticker == ScreenerSnapshot.ticker)
            & (ScreenerSnapshot.snapshot_date == latest_sub),
        )
        .order_by(
            FIIMetadata.score.desc().nullslast(),
            FIIMetadata.ticker.asc(),
        )
    )

    result = await global_db.execute(stmt)
    rows = result.all()

    scored_rows: list[FIIScoredRow] = []
    has_scores = False

    for fii, short_name in rows:
        if fii.score is not None:
            has_scores = True

        scored_rows.append(
            FIIScoredRow(
                ticker=fii.ticker,
                short_name=short_name,
                segmento=fii.segmento,
                dy_12m=str(fii.dy_12m) if fii.dy_12m is not None else None,
                pvp=str(fii.pvp) if fii.pvp is not None else None,
                daily_liquidity=fii.daily_liquidity,
                score=str(fii.score) if fii.score is not None else None,
                dy_rank=fii.dy_rank,
                pvp_rank=fii.pvp_rank,
                liquidity_rank=fii.liquidity_rank,
                score_updated_at=(
                    fii.score_updated_at.isoformat()
                    if fii.score_updated_at is not None
                    else None
                ),
            )
        )

    logger.info("get_ranked_fiis: returning %d FII rows (scores available: %s)", len(scored_rows), has_scores)

    return FIIScoredResponse(
        score_available=has_scores,
        total=len(scored_rows),
        results=scored_rows,
    )
