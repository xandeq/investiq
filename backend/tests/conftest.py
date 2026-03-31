"""pytest configuration for InvestIQ backend tests.

Uses SQLite (aiosqlite) in-memory database so tests run without a running
PostgreSQL instance. JWT keys are generated fresh per test session.

Production uses PostgreSQL + asyncpg; the SQLAlchemy 2.x async abstraction is
identical so test fidelity is high for all ORM-level logic.

RLS enforcement tests (test_rls.py) use a separate PostgreSQL fixture — those
tests are skipped when PostgreSQL is not available.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from unittest.mock import patch, MagicMock

import fakeredis
import fakeredis.aioredis
import pytest
import pytest_asyncio
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# ---------------------------------------------------------------------------
# Generate test RSA key pair and inject into environment BEFORE importing app
# ---------------------------------------------------------------------------
def _generate_test_keys():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()
    return private_pem, public_pem


_TEST_PRIVATE_KEY, _TEST_PUBLIC_KEY = _generate_test_keys()

# Inject keys before settings are read
os.environ["JWT_PRIVATE_KEY"] = _TEST_PRIVATE_KEY
os.environ["JWT_PUBLIC_KEY"] = _TEST_PUBLIC_KEY
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["AUTH_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Test uses fakeredis below
os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"      # Prevents lazy StripeClient init failure in tests
os.environ["SLOWAPI_STORAGE_URI"] = "memory://"        # Use in-memory rate limiter — avoids Redis in tests

# Now import app (settings reads env vars)
from app.core.db import get_db
from app.main import app
from app.modules.auth.models import Base

# Import all models so Base.metadata.create_all() covers all tables.
# Each module's models must be imported before create_all is called —
# SQLAlchemy only includes tables it knows about at metadata build time.
import app.modules.portfolio.models as _pm  # noqa: F401 — registers Transaction, CorporateAction
import app.modules.ai.models as _aim  # noqa: F401 — registers AIAnalysisJob
import app.modules.imports.models as _im  # noqa: F401 — registers ImportFile, ImportJob, ImportStaging
import app.modules.billing.models as _bm  # noqa: F401 — registers Subscription
import app.modules.watchlist.models as _wm  # noqa: F401 — registers WatchlistItem
import app.modules.insights.models as _insm  # noqa: F401 — registers UserInsight
import app.modules.market_universe.models as _mum  # noqa: F401 — registers ScreenerSnapshot, FIIMetadata, FixedIncomeCatalog, TaxConfig
import app.modules.wizard.models as _wizm  # noqa: F401 — registers WizardJob
import app.modules.screener.models as _scrm  # noqa: F401 — registers ScreenerRun
import app.modules.analysis.models as _anm  # noqa: F401 — registers AnalysisJob, AnalysisQuotaLog, AnalysisCostLog


# ---------------------------------------------------------------------------
# In-memory SQLite engine for tests
# ---------------------------------------------------------------------------
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop_policy():
    """Use default asyncio event loop policy (required by anyio)."""
    import asyncio
    return asyncio.DefaultEventLoopPolicy()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        # SQLite-specific: enable foreign keys
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Fresh session for each test using implicit transactions.

    No outer session.begin() wrapper: routers that call await db.commit()
    commit their own implicit transaction without invalidating the session
    context. Tests are isolated by using unique email/ID values per test,
    not by rollback.
    """
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as session:
        yield session


# ---------------------------------------------------------------------------
# Fake Redis for rate-limiting tests (no real Redis needed)
# ---------------------------------------------------------------------------
class FakeRedis:
    """Minimal fake Redis for INCR/EXPIRE rate limiting in tests."""

    def __init__(self):
        self._store: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self._store[key] = self._store.get(key, 0) + 1
        return self._store[key]

    async def expire(self, key: str, seconds: int) -> None:
        pass  # Not needed for unit tests

    def reset(self):
        self._store.clear()


@pytest.fixture
def fake_redis():
    r = FakeRedis()
    yield r
    r.reset()


# ---------------------------------------------------------------------------
# Email stub (EXT-03: swappable adapter)
# ---------------------------------------------------------------------------
@pytest.fixture
def email_stub():
    """Captures all sent emails without making real HTTP requests."""
    sent: list[tuple[str, str, str]] = []

    async def stub(to_email: str, subject: str, html: str) -> None:
        sent.append((to_email, subject, html))

    stub.sent = sent
    return stub


# ---------------------------------------------------------------------------
# AsyncClient fixture using test DB and stub email
# ---------------------------------------------------------------------------
@pytest_asyncio.fixture
async def client(db_session, email_stub, fake_redis, fake_redis_async) -> AsyncGenerator[AsyncClient, None]:
    """HTTP client wired to the test DB, stub email, and fake Redis.

    Overrides:
    - get_db: uses in-memory SQLite session
    - get_authed_db: uses in-memory SQLite session (bypasses SET LOCAL — SQLite incompatible)
    - auth _get_service: uses stub email + fake_redis for rate limiting
    - portfolio _get_redis: uses fake_redis_async (fakeredis.aioredis)
    - market_data _get_market_service: wraps fake_redis_async in MarketDataService
    """
    from app.modules.auth.service import AuthService
    from app.modules.market_data.service import MarketDataService
    from app.core.middleware import get_authed_db

    async def override_get_db():
        yield db_session

    async def override_get_authed_db():
        """Bypass SET LOCAL for SQLite test DB — RLS isolation tested via test_rls.py."""
        yield db_session

    def override_get_auth_service():
        return AuthService(db_session, email_sender=email_stub, redis_client=fake_redis)

    def override_get_redis():
        return fake_redis_async

    def override_get_market_service():
        return MarketDataService(fake_redis_async)

    from app.modules.auth.router import _get_service as auth_get_service
    from app.modules.portfolio.router import _get_redis
    from app.modules.market_data.router import _get_market_service
    from app.modules.dashboard.router import _get_redis as dashboard_get_redis
    from app.modules.ai.router import _get_redis as ai_get_redis

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_authed_db] = override_get_authed_db
    app.dependency_overrides[auth_get_service] = override_get_auth_service
    app.dependency_overrides[_get_redis] = override_get_redis
    app.dependency_overrides[_get_market_service] = override_get_market_service
    app.dependency_overrides[dashboard_get_redis] = override_get_redis
    app.dependency_overrides[ai_get_redis] = override_get_redis

    # Mock wizard Celery dispatch -- tests don't need real Celery
    with patch("app.modules.wizard.router._dispatch") as mock_dispatch:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            c._mock_wizard_dispatch = mock_dispatch  # expose for test assertions
            yield c

    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Helper: register + verify a user (shared across tests)
# ---------------------------------------------------------------------------
async def register_and_verify(
    client: AsyncClient,
    email_stub,
    email: str = "test@example.com",
    password: str = "SecurePass123!",
) -> str:
    """Register a user and simulate email verification. Returns user_id."""
    resp = await client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text

    # Extract token from verification email link
    assert email_stub.sent, "Verification email was not sent"
    _, _, html = email_stub.sent[-1]
    token = _extract_token_from_html(html)

    # Verify email
    resp2 = await client.get(f"/auth/verify-email?token={token}")
    assert resp2.status_code == 200, resp2.text

    return resp.json()["user_id"]


async def register_verify_and_login(
    client: AsyncClient,
    email_stub,
    email: str = "test@example.com",
    password: str = "SecurePass123!",
) -> str:
    """Register, verify email, and login. Returns user_id.

    Use this helper for tests that need an authenticated session cookie
    (i.e., tests that call protected endpoints like /portfolio/*).
    """
    user_id = await register_and_verify(client, email_stub, email=email, password=password)

    # Login to get httpOnly session cookies
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text

    return user_id


def _extract_token_from_html(html: str) -> str:
    """Extract token from verification/reset email HTML."""
    import re
    match = re.search(r"token=([^\"'&\s]+)", html)
    assert match, f"No token found in HTML: {html[:200]}"
    return match.group(1)


# ---------------------------------------------------------------------------
# Celery / Redis fixtures for market data task tests
# ---------------------------------------------------------------------------
@pytest.fixture
def fake_redis_sync():
    """Synchronous fakeredis instance for Celery task tests."""
    r = fakeredis.FakeRedis()
    yield r
    r.flushall()


@pytest.fixture
def fake_redis_async():
    """Asynchronous fakeredis instance for async service tests."""
    r = fakeredis.aioredis.FakeRedis()
    yield r


@pytest.fixture
def mock_stripe_client():
    """Mocks stripe StripeClient so no real Stripe API calls are made in tests.

    Patches the module-level _stripe variable in billing.service so all
    BillingService methods use the mock instead of a real StripeClient instance.
    """
    from unittest.mock import AsyncMock, MagicMock, patch

    mock = MagicMock()
    mock.checkout.sessions.create_async = AsyncMock(
        return_value=MagicMock(url="https://checkout.stripe.com/test_session")
    )
    mock.billing_portal.sessions.create_async = AsyncMock(
        return_value=MagicMock(url="https://billing.stripe.com/test_portal")
    )
    mock.customers.create_async = AsyncMock(
        return_value=MagicMock(id="cus_test123")
    )
    mock.subscriptions.retrieve_async = AsyncMock(
        return_value=MagicMock(
            id="sub_test123",
            status="active",
            current_period_end=9999999999,
        )
    )
    # construct_event is sync
    mock.construct_event = MagicMock(return_value={
        "type": "checkout.session.completed",
        "data": {"object": {
            "customer": "cus_test123",
            "subscription": "sub_test123",
        }}
    })
    with patch("app.modules.billing.service._stripe", mock):
        yield mock


@pytest.fixture
def mock_brapi_client():
    """Mocks httpx.get to return a brapi.dev-style quote response for PETR4."""
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "results": [
            {"symbol": "PETR4", "regularMarketPrice": 38.50}
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_response) as mock_get:
        yield mock_get
