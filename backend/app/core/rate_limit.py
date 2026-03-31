"""Per-request rate limiting for analysis endpoints (Phase 12).

Uses Redis to enforce cooldown periods between analysis requests.
Separate from slowapi (which handles general API rate limiting) —
this is analysis-specific with plan-tier-aware windows.

Rate limits:
  - Free: 1 request per 300s (5 min) — blocked by quota anyway, but defense-in-depth
  - Pro: 1 request per 60s (1 min)
  - Enterprise: 100 requests per 60s (effectively no per-request limit)
"""
from __future__ import annotations

import logging
import os

import redis as sync_redis

logger = logging.getLogger(__name__)

# Rate limit configuration per plan tier
# (max_requests, window_seconds)
_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "free": (1, 300),
    "pro": (1, 60),
    "enterprise": (100, 60),
}

# Lazy Redis singleton
_redis_client: sync_redis.Redis | None = None


def _get_redis() -> sync_redis.Redis:
    """Get or create Redis client (lazy singleton)."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        _redis_client = sync_redis.from_url(redis_url, decode_responses=True)
    return _redis_client


def set_redis_client(client: sync_redis.Redis | None) -> None:
    """Override Redis client for testing."""
    global _redis_client
    _redis_client = client


async def check_analysis_rate_limit(
    tenant_id: str, plan_tier: str
) -> tuple[bool, int]:
    """Check per-request rate limit for analysis.

    Returns:
        (allowed, retry_after_seconds)
        allowed=True means the request can proceed.
        retry_after_seconds is the TTL remaining when blocked (0 if allowed).
    """
    max_requests, window = _RATE_LIMITS.get(plan_tier, (1, 300))
    key = f"analysis:rate_limit:{tenant_id}"

    try:
        r = _get_redis()
        current = r.get(key)

        if current is not None and int(current) >= max_requests:
            ttl = r.ttl(key)
            retry_after = max(ttl, 1)  # At least 1 second
            logger.info(
                "analysis.rate_limited tenant_id=%s tier=%s retry_after=%d",
                tenant_id, plan_tier, retry_after,
            )
            return (False, retry_after)

        # Increment and set expiry atomically
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window)
        pipe.execute()

        return (True, 0)

    except Exception as exc:
        # If Redis is down, allow the request (fail open for rate limiting)
        logger.warning("analysis.rate_limit_redis_error: %s — allowing request", exc)
        return (True, 0)
