"""Outcome tracker service — records and analyzes signal outcomes (Sprint 3)."""
from __future__ import annotations

import logging
import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.outcome_tracker.models import SignalOutcome

logger = logging.getLogger(__name__)


def calculate_r_multiple(
    entry: Decimal,
    stop: Decimal,
    exit_price: Decimal,
    direction: str,
) -> Decimal:
    """R = (exit - entry) / (entry - stop) for long; reversed for short."""
    risk = abs(entry - stop)
    if risk == 0:
        return Decimal("0")
    if direction == "long":
        return (exit_price - entry) / risk
    return (entry - exit_price) / risk


async def create_outcome(db: AsyncSession, tenant_id: str, data: dict) -> SignalOutcome:
    """Create a new signal outcome record (registers an entry)."""
    outcome = SignalOutcome(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        ticker=data["ticker"],
        pattern=data.get("pattern"),
        direction=data["direction"],
        entry_price=Decimal(str(data["entry_price"])),
        stop_price=Decimal(str(data["stop_price"])),
        target_1=Decimal(str(data["target_1"])) if data.get("target_1") else None,
        target_2=Decimal(str(data["target_2"])) if data.get("target_2") else None,
        status="open",
        signal_grade=data.get("signal_grade"),
        signal_score=Decimal(str(data["signal_score"])) if data.get("signal_score") else None,
    )
    db.add(outcome)
    await db.flush()
    await db.refresh(outcome)
    return outcome


async def close_outcome(
    db: AsyncSession,
    outcome_id: str,
    exit_price: Decimal,
    exit_date: date | None = None,
    status: str = "closed",
) -> SignalOutcome | None:
    """Close an outcome: set exit_price, exit_date, compute R-multiple."""
    result = await db.execute(
        select(SignalOutcome).where(SignalOutcome.id == outcome_id)
    )
    outcome = result.scalar_one_or_none()
    if outcome is None:
        return None

    outcome.exit_price = exit_price
    outcome.exit_date = exit_date or date.today()
    outcome.status = status
    outcome.r_multiple = calculate_r_multiple(
        Decimal(str(outcome.entry_price)),
        Decimal(str(outcome.stop_price)),
        exit_price,
        outcome.direction,
    )
    await db.flush()
    await db.refresh(outcome)
    return outcome


async def list_outcomes(
    db: AsyncSession,
    tenant_id: str,
    status: str | None = None,
) -> list[SignalOutcome]:
    """List signal outcomes for a tenant, optionally filtered by status."""
    stmt = select(SignalOutcome).where(SignalOutcome.tenant_id == tenant_id)
    if status:
        stmt = stmt.where(SignalOutcome.status == status)
    stmt = stmt.order_by(SignalOutcome.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_stats(db: AsyncSession, tenant_id: str) -> dict[str, Any]:
    """Aggregate outcome stats: winrate, avg-R, grade_breakdown.

    Returns {} structure even with no data (zeros/null), so frontend always gets a valid response.
    """
    stmt = select(SignalOutcome).where(
        SignalOutcome.tenant_id == tenant_id,
        SignalOutcome.status.in_(["closed", "stopped"]),
        SignalOutcome.r_multiple.isnot(None),
    )
    result = await db.execute(stmt)
    outcomes = list(result.scalars().all())

    if not outcomes:
        return {
            "total_closed": 0,
            "winrate": None,
            "avg_r": None,
            "expectancy": None,
            "grade_breakdown": {},
        }

    r_multiples = [float(o.r_multiple) for o in outcomes]
    wins = [r for r in r_multiples if r > 0]
    winrate = round(len(wins) / len(r_multiples), 4)
    avg_r = round(sum(r_multiples) / len(r_multiples), 4)
    expectancy = round(sum(r_multiples) / len(r_multiples), 4)

    # Grade breakdown
    grade_map: dict[str, list[float]] = {}
    for o in outcomes:
        grade = o.signal_grade or "unknown"
        if grade not in grade_map:
            grade_map[grade] = []
        grade_map[grade].append(float(o.r_multiple))

    grade_breakdown = {
        grade: {
            "n": len(rs),
            "winrate": round(sum(1 for r in rs if r > 0) / len(rs), 4),
            "avg_r": round(sum(rs) / len(rs), 4),
        }
        for grade, rs in grade_map.items()
    }

    return {
        "total_closed": len(outcomes),
        "winrate": winrate,
        "avg_r": avg_r,
        "expectancy": expectancy,
        "grade_breakdown": grade_breakdown,
    }


async def get_expectancy_by_pattern(
    db: AsyncSession, tenant_id: str
) -> dict[str, Any]:
    """Calculate expectancy per pattern from closed outcomes (n >= 3).

    Expectancy = mean(r_multiples) for closed outcomes grouped by pattern.
    Only patterns with at least 3 closed trades are included.
    """
    stmt = (
        select(SignalOutcome)
        .where(
            SignalOutcome.tenant_id == tenant_id,
            SignalOutcome.status == "closed",
            SignalOutcome.r_multiple.isnot(None),
            SignalOutcome.pattern.isnot(None),
        )
    )
    result = await db.execute(stmt)
    outcomes = list(result.scalars().all())

    pattern_map: dict[str, list[float]] = {}
    for o in outcomes:
        p = o.pattern
        if p not in pattern_map:
            pattern_map[p] = []
        pattern_map[p].append(float(o.r_multiple))

    return {
        pattern: {
            "expectancy": round(sum(rs) / len(rs), 4),
            "n": len(rs),
            "win_rate": round(sum(1 for r in rs if r > 0) / len(rs), 4),
        }
        for pattern, rs in pattern_map.items()
        if len(rs) >= 3
    }
