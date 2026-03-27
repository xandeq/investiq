"""Rate limiter configuration using slowapi.

slowapi is a thin wrapper around limits that integrates with FastAPI/Starlette.
Uses Redis as the storage backend (same Redis instance as Celery/cache).

Usage in route handlers:
    from app.core.limiter import limiter
    from fastapi import Request

    @router.post("/endpoint")
    @limiter.limit("5/hour")
    async def my_endpoint(request: Request, ...):
        ...

Integration in main.py:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
"""
from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import settings

# Allow tests to override storage without affecting the app's Redis connections.
# Set SLOWAPI_STORAGE_URI=memory:// in test environments to avoid needing real Redis.
_storage_uri = os.environ.get("SLOWAPI_STORAGE_URI") or settings.REDIS_URL

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
)
