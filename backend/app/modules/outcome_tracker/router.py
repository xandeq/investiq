"""FastAPI router for /outcomes endpoints (Sprint 3 + Wave E Phase 32).

Endpoints:
  POST   /outcomes              — register a new signal entry
  GET    /outcomes              — list outcomes (filter ?status=open|closed|stopped)
  PATCH  /outcomes/{id}/close   — close with exit_price and exit_date, computes R
  GET    /outcomes/expectancy   — expectancy by pattern (n >= 3 closed trades)
  GET    /outcomes/stats        — aggregate stats: winrate, avg-R, grade_breakdown
"""

import logging
from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi import status as http_status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.outcome_tracker.service import (
    close_outcome,
    create_outcome,
    get_expectancy_by_pattern,
    get_stats,
    list_outcomes,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Schemas ──────────────────────────────────────────────────────────────────


class OutcomeCreate(BaseModel):
    ticker: str
    direction: str  # 'long' | 'short'
    entry_price: Decimal
    stop_price: Decimal
    pattern: str | None = None
    target_1: Decimal | None = None
    target_2: Decimal | None = None
    signal_grade: str | None = None
    signal_score: Decimal | None = None


class OutcomeCloseRequest(BaseModel):
    exit_price: Decimal
    exit_date: date | None = None
    status: str = Field(default="closed", pattern="^(closed|stopped)$")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _serialize(obj: Any) -> dict:
    return {
        c.name: (
            str(getattr(obj, c.name))
            if isinstance(getattr(obj, c.name), Decimal)
            else getattr(obj, c.name)
        )
        for c in obj.__table__.columns
    }


# ── Routes ────────────────────────────────────────────────────────────────────


@router.post("", status_code=http_status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_outcome_endpoint(
    request: Request,
    body: OutcomeCreate,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_authed_db),
) -> dict:
    """Register a new signal entry."""
    outcome = await create_outcome(db, tenant_id, body.model_dump())
    return _serialize(outcome)


@router.get("/expectancy")
@limiter.limit("20/minute")
async def get_expectancy(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_authed_db),
) -> dict:
    """Return expectancy per pattern (only patterns with n >= 3 closed trades)."""
    result = await get_expectancy_by_pattern(db, tenant_id)
    return {"expectancy": result}


@router.get("")
@limiter.limit("30/minute")
async def list_outcomes_endpoint(
    request: Request,
    filter_status: str | None = Query(default=None, alias="status", pattern="^(open|closed|stopped)$"),
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_authed_db),
) -> dict:
    """List signal outcomes, optionally filtered by status."""
    outcomes = await list_outcomes(db, tenant_id, filter_status)
    return {"outcomes": [_serialize(o) for o in outcomes], "count": len(outcomes)}


@router.get("/stats")
@limiter.limit("20/minute")
async def get_outcome_stats(
    request: Request,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_authed_db),
) -> dict:
    """Aggregate outcome stats: winrate, avg-R, grade_breakdown.

    Only includes closed and stopped outcomes. Open trades are excluded.
    Requires at least 1 closed trade to return meaningful data.
    """
    stats = await get_stats(db, tenant_id)
    return stats


@router.patch("/{outcome_id}/close")
@limiter.limit("20/minute")
async def close_outcome_endpoint(
    request: Request,
    outcome_id: str,
    body: OutcomeCloseRequest,
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_authed_db),
) -> dict:
    """Close an outcome: set exit_price/date and calculate R-multiple."""
    outcome = await close_outcome(
        db,
        outcome_id,
        exit_price=body.exit_price,
        exit_date=body.exit_date,
        status=body.status,
    )
    if outcome is None:
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Outcome not found")
    return _serialize(outcome)
