"""Cache invalidation for the AI Analysis module (Phase 12).

Marks analyses as 'stale' when earnings releases are detected,
and clears Redis cache for affected tickers.

The Celery beat task that calls on_earnings_release daily is deferred
to Phase 15 (AI-13) when BRAPI earnings feed integration happens.
Phase 12 only provides the invalidation function.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update

from app.core.db_sync import get_superuser_sync_db_session
from app.modules.analysis.models import AnalysisJob

logger = logging.getLogger(__name__)


def _get_sync_redis():
    """Get a synchronous Redis client for cache operations."""
    import redis as sync_redis

    return sync_redis.from_url(
        os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
    )


async def on_earnings_release(ticker: str, filing_date: datetime) -> int:
    """Invalidate cached analyses when new earnings are released.

    Marks all completed AnalysisJob rows for the given ticker that were
    completed before the filing_date as 'stale'. Also clears the Redis
    cache key for that ticker.

    Args:
        ticker: Stock ticker (e.g. "PETR4").
        filing_date: Date of the new earnings filing.

    Returns:
        Number of analyses marked as stale.
    """
    count = 0

    with get_superuser_sync_db_session() as session:
        stmt = (
            update(AnalysisJob)
            .where(
                AnalysisJob.ticker == ticker,
                AnalysisJob.status == "completed",
                AnalysisJob.completed_at < filing_date,
            )
            .values(
                status="stale",
                error_message="New earnings released; please refresh",
            )
        )
        result = session.execute(stmt)
        count = result.rowcount

    # Clear Redis cache for this ticker
    try:
        r = _get_sync_redis()
        cache_key = f"analysis:cache:{ticker}"
        r.delete(cache_key)
    except Exception as exc:
        logger.warning("Redis cache clear failed for %s: %s", ticker, exc)

    logger.info(
        "Invalidated %d analyses for %s due to earnings release", count, ticker
    )
    return count


def get_analyzed_tickers_recent_7d() -> list[str]:
    """Return distinct tickers with analyses in the last 7 days.

    Used to determine which tickers need earnings-release checking.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    with get_superuser_sync_db_session() as session:
        stmt = (
            select(AnalysisJob.ticker)
            .where(
                AnalysisJob.created_at > cutoff,
                AnalysisJob.status.in_(["completed", "stale"]),
            )
            .distinct()
        )
        result = session.execute(stmt).scalars().all()
        return list(result)
