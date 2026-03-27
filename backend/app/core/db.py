from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from typing import AsyncGenerator
from uuid import UUID
from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_pre_ping=True,
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

# Auth engine: uses a superuser connection that bypasses RLS.
# Auth endpoints (login, register, verify-email) look up users by email without
# a tenant context — RLS would block these queries if using app_user.
_auth_engine = create_async_engine(
    settings.AUTH_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)
_auth_session_factory = async_sessionmaker(_auth_engine, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Auth DB session — uses superuser to bypass RLS. For auth endpoints before tenant is known."""
    async with _auth_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_tenant_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    """DB session with RLS tenant context injected. Use for ALL tenant-scoped queries.

    SET LOCAL is transaction-scoped — safe with connection pools.
    Never use SET (connection-scoped) — leaks across pool reuse.
    """
    async with async_session_factory() as session:
        UUID(tenant_id)  # validate UUID format before embedding
        await session.execute(text(f"SET LOCAL rls.tenant_id = '{tenant_id}'"))
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_global_db() -> AsyncGenerator[AsyncSession, None]:
    """DB session without tenant injection — for global tables (screener, catalog, tax).

    Uses the same async_session_factory (app_user connection) as get_tenant_db,
    but does NOT call SET LOCAL rls.tenant_id. Safe because global tables
    (screener_snapshots, fii_metadata, fixed_income_catalog, tax_config) have
    no RLS policy — app_user access is controlled via GRANT statements in migration 0015.

    Use for:
        - Reading screener_snapshots in Phase 8 screener endpoints
        - Reading fixed_income_catalog in Phase 9 renda fixa endpoints
        - Instantiating TaxEngine (reads tax_config) in Phase 9/10
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
