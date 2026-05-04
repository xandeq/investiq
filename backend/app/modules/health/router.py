"""System health endpoints — no auth required (public, read-only).

GET /health/freshness — data freshness status for external monitors.

Returns last-run timestamps and staleness flags for the 3 main data domains:
  screener   — daily refresh (Mon-Fri 07:00 BRT), stale if > 48h
  macro      — every 6h, stale if > 12h (SELIC/CDI/IPCA)
  tesouro    — every 6h, stale if > 12h (ANBIMA treasury rates)

Consumed by: UptimeRobot/Better Stack monitors, frontend staleness banner,
admin dashboard. Returns 200 always — staleness is informational, not a 5xx.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

_SCREENER_STALE_HOURS = 48
_MACRO_STALE_HOURS = 12


class DataFreshnessResponse(BaseModel):
    checked_at: datetime
    screener_last_run: datetime | None       # MAX(snapshot_date) from screener_snapshots
    screener_stale: bool                     # > 48h or never run
    macro_last_fetched: datetime | None      # market:macro:fetched_at from Redis
    macro_stale: bool                        # > 12h or never fetched


@router.get("/freshness", response_model=DataFreshnessResponse, include_in_schema=True)
async def data_freshness() -> DataFreshnessResponse:
    """Return data freshness status for all major data domains.

    No authentication required — intended for external health monitors
    (UptimeRobot, Better Stack) and the frontend staleness banner.
    """
    now = datetime.now(tz=timezone.utc)

    # ── Screener: read MAX(snapshot_date) from PostgreSQL ─────────────────
    screener_last_run: datetime | None = None
    try:
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy import select, func as sqlfunc
        from app.modules.market_universe.models import ScreenerSnapshot

        engine = create_async_engine(
            os.environ.get(
                "DATABASE_URL",
                "postgresql+asyncpg://app_user:change_in_production@postgres:5432/investiq",
            ),
            pool_pre_ping=True,
            pool_size=1,
        )
        async with AsyncSession(engine) as session:
            result = await session.execute(
                select(sqlfunc.max(ScreenerSnapshot.snapshot_date))
            )
            max_date = result.scalar()
            if max_date:
                screener_last_run = datetime.combine(
                    max_date, datetime.min.time()
                ).replace(tzinfo=timezone.utc)
        await engine.dispose()
    except Exception as exc:
        logger.warning("health/freshness: screener query failed: %s", exc)

    # ── Macro: read market:macro:fetched_at from Redis ────────────────────
    macro_last_fetched: datetime | None = None
    try:
        import redis as redis_lib
        r = redis_lib.Redis.from_url(
            os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True,
            socket_connect_timeout=2,
        )
        fetched_raw = r.get("market:macro:fetched_at")
        if fetched_raw:
            macro_last_fetched = datetime.fromisoformat(fetched_raw)
            if macro_last_fetched.tzinfo is None:
                macro_last_fetched = macro_last_fetched.replace(tzinfo=timezone.utc)
    except Exception as exc:
        logger.warning("health/freshness: Redis query failed: %s", exc)

    # ── Staleness flags ────────────────────────────────────────────────────
    screener_stale = (
        screener_last_run is None
        or (now - screener_last_run) > timedelta(hours=_SCREENER_STALE_HOURS)
    )
    macro_stale = (
        macro_last_fetched is None
        or (now - macro_last_fetched) > timedelta(hours=_MACRO_STALE_HOURS)
    )

    return DataFreshnessResponse(
        checked_at=now,
        screener_last_run=screener_last_run,
        screener_stale=screener_stale,
        macro_last_fetched=macro_last_fetched,
        macro_stale=macro_stale,
    )
