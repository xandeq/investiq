"""RLS tenant isolation tests.

AUTH-05: Tests that verify PostgreSQL Row Level Security prevents cross-tenant
data access. These tests MUST run as app_user (non-superuser) — superusers bypass
RLS policies, making isolation tests meaningless.

These tests require a real PostgreSQL instance with:
1. Migration 0002_add_rls_policies applied (RLS enabled on users table)
2. app_user role created with non-superuser privileges
3. rls.tenant_id GUC available for SET LOCAL calls

When PostgreSQL is not available (e.g., local dev with SQLite), these tests
are automatically skipped. They are designed to run inside the Docker backend
container where PostgreSQL is accessible.

Connection: postgresql+asyncpg://app_user:change_in_production@localhost:5432/investiq_test
"""
from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio

# ---------------------------------------------------------------------------
# PostgreSQL availability check — skip suite if PG is unreachable
# ---------------------------------------------------------------------------
POSTGRES_URL = os.getenv(
    "TEST_PG_URL",
    "postgresql+asyncpg://app_user:change_in_production@localhost:5432/investiq_test",
)
# We detect PG availability lazily in the fixture so we can provide a clear
# skip message rather than a confusing ImportError.

try:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
    from sqlalchemy import text
    _SQLALCHEMY_AVAILABLE = True
except ImportError:
    _SQLALCHEMY_AVAILABLE = False


def _pg_available() -> bool:
    """Return True if the PostgreSQL test server is reachable."""
    if not _SQLALCHEMY_AVAILABLE:
        return False
    try:
        import asyncpg  # type: ignore[import]
    except ImportError:
        return False
    import asyncio
    async def _check():
        try:
            conn = await asyncpg.connect(
                user="app_user",
                password="change_in_production",
                database="investiq_test",
                host="localhost",
                port=5432,
                timeout=2,
            )
            await conn.close()
            return True
        except Exception:
            return False
    try:
        loop = asyncio.new_event_loop()
        result = loop.run_until_complete(_check())
        loop.close()
        return result
    except Exception:
        return False


PG_AVAILABLE = _pg_available()
pytestmark = pytest.mark.skipif(
    not PG_AVAILABLE,
    reason="PostgreSQL not available — RLS tests require a real PG instance with app_user role and migration 0002 applied",
)


# ---------------------------------------------------------------------------
# Fixtures — app_user engine for RLS enforcement tests
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def app_user_engine():
    """Async engine connecting as app_user (non-superuser) — RLS applies to this role."""
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(POSTGRES_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="module")
async def superuser_engine():
    """Async engine connecting as postgres superuser — used only for INSERT setup."""
    pg_superuser_url = POSTGRES_URL.replace(
        "app_user:change_in_production",
        "postgres:postgres",
    )
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(pg_superuser_url, echo=False)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_test_data(superuser_engine):
    """Remove test data before each test to ensure isolation."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text
    factory = async_sessionmaker(superuser_engine, expire_on_commit=False)
    # Clean up before test
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE email LIKE 'rls-test-%@example.com'"))
        await session.commit()
    yield
    # Clean up after test
    async with factory() as session:
        await session.execute(text("DELETE FROM users WHERE email LIKE 'rls-test-%@example.com'"))
        await session.commit()


# ---------------------------------------------------------------------------
# Helper: insert user bypassing RLS (superuser) and query as app_user
# ---------------------------------------------------------------------------

async def _insert_user_as_superuser(superuser_engine, tenant_id: str, user_id: str, email: str) -> None:
    """Insert a user row as superuser (bypasses RLS — sets up test data)."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text
    factory = async_sessionmaker(superuser_engine, expire_on_commit=False)
    async with factory() as session:
        await session.execute(
            text("""
                INSERT INTO users (id, tenant_id, email, hashed_password, is_verified, plan, created_at, updated_at)
                VALUES (:id, :tenant_id, :email, '$2b$12$fakehash', false, 'free', now(), now())
            """),
            {"id": user_id, "tenant_id": tenant_id, "email": email},
        )
        await session.commit()


async def _count_users_as_app_user(app_user_engine, tenant_id: str) -> int:
    """Count users as app_user with given tenant_id context."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text
    factory = async_sessionmaker(app_user_engine, expire_on_commit=False)
    async with factory() as session:
        # SET LOCAL only works inside an explicit transaction
        async with session.begin():
            await session.execute(
                text("SET LOCAL rls.tenant_id = :tid"),
                {"tid": tenant_id},
            )
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            return result.scalar_one()


# ---------------------------------------------------------------------------
# Test: AUTH-05 — Tenant isolation (SELECT)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation(app_user_engine, superuser_engine):
    """AUTH-05: Tenant A inserts a user row. Querying as Tenant B returns 0 rows.

    Tenant isolation is enforced at the PostgreSQL RLS level (not application code).
    The SET LOCAL rls.tenant_id GUC is the ONLY mechanism — if it leaks, isolation fails.
    """
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Insert a user belonging to Tenant A (as superuser — bypasses RLS to set up test data)
    await _insert_user_as_superuser(
        superuser_engine,
        tenant_id=tenant_a,
        user_id=user_id,
        email=f"rls-test-{user_id}@example.com",
    )

    # Query as Tenant B — should see 0 rows (RLS blocks cross-tenant access)
    count_as_b = await _count_users_as_app_user(app_user_engine, tenant_b)
    assert count_as_b == 0, f"Tenant B saw {count_as_b} rows from Tenant A — RLS FAILED"

    # Query as Tenant A — should see the 1 row that belongs to it
    count_as_a = await _count_users_as_app_user(app_user_engine, tenant_a)
    assert count_as_a == 1, f"Tenant A should see its own row but got {count_as_a}"


# ---------------------------------------------------------------------------
# Test: AUTH-05 — Tenant isolation (UPDATE)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tenant_isolation_update(app_user_engine, superuser_engine):
    """AUTH-05: Tenant B UPDATE on Tenant A rows affects 0 rows (silent isolation).

    PostgreSQL FORCE ROW LEVEL SECURITY makes UPDATE silently skip rows that
    don't match the RLS policy — no error is raised, 0 rows updated.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text

    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Insert user belonging to Tenant A
    await _insert_user_as_superuser(
        superuser_engine,
        tenant_id=tenant_a,
        user_id=user_id,
        email=f"rls-test-{user_id}@example.com",
    )

    # Attempt UPDATE as Tenant B — should affect 0 rows
    factory = async_sessionmaker(app_user_engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            await session.execute(
                text("SET LOCAL rls.tenant_id = :tid"),
                {"tid": str(tenant_b)},
            )
            result = await session.execute(
                text("UPDATE users SET plan = 'hijacked' WHERE id = :id"),
                {"id": user_id},
            )
            rows_affected = result.rowcount

    assert rows_affected == 0, (
        f"Tenant B UPDATE affected {rows_affected} rows from Tenant A — RLS FAILED"
    )

    # Verify the row was NOT modified
    from sqlalchemy.ext.asyncio import async_sessionmaker as asm2
    factory2 = asm2(superuser_engine, expire_on_commit=False)
    async with factory2() as session:
        result = await session.execute(
            text("SELECT plan FROM users WHERE id = :id"),
            {"id": user_id},
        )
        plan = result.scalar_one_or_none()
    assert plan == "free", f"Row was modified by cross-tenant UPDATE — plan is now '{plan}'"


# ---------------------------------------------------------------------------
# Test: AUTH-05 — No context returns 0 rows (safe default)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rls_with_no_context(app_user_engine, superuser_engine):
    """When rls.tenant_id is not set, SELECT returns 0 rows (safe default).

    NULLIF(current_setting('rls.tenant_id', TRUE), '') returns NULL when the
    GUC is not set. NULL != any tenant_id UUID, so no rows match.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text

    tenant_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())

    # Insert a user
    await _insert_user_as_superuser(
        superuser_engine,
        tenant_id=tenant_id,
        user_id=user_id,
        email=f"rls-test-{user_id}@example.com",
    )

    # Query WITHOUT setting rls.tenant_id — should return 0 rows
    factory = async_sessionmaker(app_user_engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            # Do NOT set rls.tenant_id — test the "no context" default
            result = await session.execute(text("SELECT COUNT(*) FROM users"))
            count = result.scalar_one()

    assert count == 0, (
        f"Query without rls.tenant_id context returned {count} rows — should be 0 (safe default)"
    )


# ---------------------------------------------------------------------------
# Test: app_user role exists and is NOT a superuser
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_app_user_role_exists(superuser_engine):
    """app_user role must exist and must NOT be a superuser.

    Superusers bypass RLS — if app_user were a superuser, all isolation tests
    would pass vacuously (RLS never applied) while providing no real guarantee.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text

    factory = async_sessionmaker(superuser_engine, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT rolname, rolsuper, rolcanlogin
                FROM pg_catalog.pg_roles
                WHERE rolname = 'app_user'
            """)
        )
        row = result.fetchone()

    assert row is not None, "app_user role does not exist — run migration 0002_add_rls_policies"
    role_name, is_superuser, can_login = row
    assert not is_superuser, "app_user must NOT be a superuser — superusers bypass RLS"
    assert can_login, "app_user must be able to login (LOGIN privilege required)"


# ---------------------------------------------------------------------------
# Test: RLS policies exist on users and refresh_tokens tables
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rls_policies_exist(superuser_engine):
    """Migration 0002 must have created tenant_isolation policy on users and refresh_tokens."""
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text

    factory = async_sessionmaker(superuser_engine, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT tablename, policyname
                FROM pg_policies
                WHERE policyname = 'tenant_isolation'
                  AND tablename IN ('users', 'refresh_tokens')
                ORDER BY tablename
            """)
        )
        rows = result.fetchall()

    table_names = {row[0] for row in rows}
    assert "users" in table_names, "tenant_isolation policy missing on users table"
    assert "refresh_tokens" in table_names, "tenant_isolation policy missing on refresh_tokens table"


# ---------------------------------------------------------------------------
# Test: FORCE ROW LEVEL SECURITY is enabled (prevents table owner bypass)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_rls_enabled(superuser_engine):
    """FORCE ROW LEVEL SECURITY must be set on users — prevents table owner bypass.

    Without FORCE RLS, the table owner (postgres) bypasses RLS even when logged
    in normally. With FORCE RLS, even the owner must pass the policy.
    """
    from sqlalchemy.ext.asyncio import async_sessionmaker
    from sqlalchemy import text

    factory = async_sessionmaker(superuser_engine, expire_on_commit=False)
    async with factory() as session:
        result = await session.execute(
            text("""
                SELECT relrowsecurity, relforcerowsecurity
                FROM pg_class
                WHERE relname = 'users'
            """)
        )
        row = result.fetchone()

    assert row is not None, "users table not found in pg_class"
    rls_enabled, force_rls = row
    assert rls_enabled, "Row Level Security must be ENABLED on users table"
    assert force_rls, "FORCE ROW LEVEL SECURITY must be set on users table (prevents table owner bypass)"
