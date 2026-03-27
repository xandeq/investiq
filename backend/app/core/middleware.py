"""FastAPI dependency chain for RLS tenant injection.

This module provides the `get_authed_db` dependency that:
1. Reads and validates the JWT access token from the httpOnly cookie.
2. Extracts the tenant_id from the decoded token payload.
3. Opens a database session and executes SET LOCAL rls.tenant_id = :tid
   before yielding the session to the route handler.

Usage in route handlers:
    from app.core.middleware import get_authed_db
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi import Depends

    @router.get("/my-data")
    async def get_my_data(db: AsyncSession = Depends(get_authed_db)):
        # All queries on `db` are automatically scoped to the authenticated
        # tenant via PostgreSQL Row Level Security.
        result = await db.execute(select(MyModel))
        ...

Design notes:
- SET LOCAL is transaction-scoped — safe with connection pools (PgBouncer, asyncpg).
  Never use plain SET (connection-scoped) — it leaks across pool reuse.
- The tenant context is injected at the DB level, not the application level.
  Even if application code accidentally queries a different tenant's data,
  PostgreSQL RLS will silently return 0 rows.
- get_authed_db depends on get_current_user (401 if not authenticated) and
  get_tenant_db (from db.py, which executes SET LOCAL).
"""
from __future__ import annotations

from typing import AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_tenant_db
from app.core.security import get_current_user


async def get_current_tenant_id(
    current_user: dict = Depends(get_current_user),
) -> str:
    """FastAPI dependency: extract tenant_id from the authenticated JWT.

    Raises 401 if the JWT is missing, expired, or invalid (handled by
    get_current_user upstream).

    Returns:
        str: The tenant_id UUID string from the JWT payload.
    """
    return current_user["tenant_id"]


async def get_authed_db(
    tenant_id: str = Depends(get_current_tenant_id),
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: DB session with RLS tenant context.

    Opens a PostgreSQL session, executes:
        SET LOCAL rls.tenant_id = '<tenant_id>'

    before the route handler runs. All queries in this session are
    automatically filtered by PostgreSQL Row Level Security to the
    authenticated tenant's data.

    This is the standard dependency for ALL tenant-scoped routes in
    subsequent plans. Auth-only routes (login, register, verify-email)
    use get_db() instead (no tenant context needed for unauthenticated paths).

    Raises:
        401: If the request has no valid JWT cookie (via get_current_user).
    """
    async for session in get_tenant_db(tenant_id):
        yield session
