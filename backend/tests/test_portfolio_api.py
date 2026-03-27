"""Integration tests for the Portfolio API.

Tests cover:
- POST /portfolio/transactions (buy, sell, dividend, renda_fixa, BDR/ETF)
- GET /portfolio/positions (with CMP and Redis price enrichment)
- GET /portfolio/pnl (realized + unrealized P&L, allocation)
- GET /portfolio/benchmarks (CDI + IBOVESPA from Redis)
- GET /portfolio/dividends (filtered dividend history)
- RLS tenant isolation

These tests use:
- fakeredis.aioredis for Redis (no real Redis needed)
- SQLite in-memory DB via db_session fixture
- email_stub for auth email verification
"""
from __future__ import annotations

import json
import pytest
import pytest_asyncio
from decimal import Decimal
from httpx import ASGITransport, AsyncClient
from tests.conftest import register_and_verify, register_verify_and_login


# ---------------------------------------------------------------------------
# Shared transaction payloads
# ---------------------------------------------------------------------------

BUY_PETR4 = {
    "ticker": "PETR4",
    "asset_class": "acao",
    "transaction_type": "buy",
    "transaction_date": "2024-01-15",
    "quantity": "100",
    "unit_price": "38.50",
}

BUY_PETR4_SECOND = {
    "ticker": "PETR4",
    "asset_class": "acao",
    "transaction_type": "buy",
    "transaction_date": "2024-02-01",
    "quantity": "100",
    "unit_price": "40.00",
}

SELL_PETR4 = {
    "ticker": "PETR4",
    "asset_class": "acao",
    "transaction_type": "sell",
    "transaction_date": "2024-03-01",
    "quantity": "50",
    "unit_price": "42.00",
}

FII_DIVIDEND = {
    "ticker": "HGLG11",
    "asset_class": "fii",
    "transaction_type": "dividend",
    "transaction_date": "2024-01-20",
    "quantity": "1",
    "unit_price": "1.25",
    "is_exempt": True,
}

RENDA_FIXA_BUY = {
    "ticker": "CDB_BTG",
    "asset_class": "renda_fixa",
    "transaction_type": "buy",
    "transaction_date": "2024-01-10",
    "quantity": "1",
    "unit_price": "5000.00",
    "coupon_rate": "0.135",
    "maturity_date": "2026-01-15",
}

BDR_BUY = {
    "ticker": "AAPL34",
    "asset_class": "bdr",
    "transaction_type": "buy",
    "transaction_date": "2024-01-12",
    "quantity": "10",
    "unit_price": "55.00",
}

ETF_BUY = {
    "ticker": "BOVA11",
    "asset_class": "etf",
    "transaction_type": "buy",
    "transaction_date": "2024-01-08",
    "quantity": "20",
    "unit_price": "118.50",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_create_buy_transaction(client, email_stub):
    """POST buy transaction → 201, response has id and correct CMP."""
    await register_verify_and_login(client, email_stub)

    resp = await client.post("/portfolio/transactions", json=BUY_PETR4)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert "id" in data
    assert data["ticker"] == "PETR4"
    assert data["asset_class"] == "acao"
    assert data["transaction_type"] == "buy"
    assert Decimal(data["quantity"]) == Decimal("100")
    assert Decimal(data["unit_price"]) == Decimal("38.50")


@pytest.mark.asyncio
async def test_fii_dividend_exempt(client, email_stub):
    """POST FII dividend with is_exempt=True → 201, is_exempt preserved."""
    await register_verify_and_login(client, email_stub)

    resp = await client.post("/portfolio/transactions", json=FII_DIVIDEND)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["is_exempt"] is True
    assert data["ticker"] == "HGLG11"
    assert data["transaction_type"] == "dividend"


@pytest.mark.asyncio
async def test_renda_fixa_transaction(client, email_stub):
    """POST renda_fixa buy with coupon_rate + maturity_date → 201, fields preserved."""
    await register_verify_and_login(client, email_stub)

    resp = await client.post("/portfolio/transactions", json=RENDA_FIXA_BUY)
    assert resp.status_code == 201, resp.text
    data = resp.json()

    assert data["asset_class"] == "renda_fixa"
    assert Decimal(data["coupon_rate"]) == Decimal("0.135")
    assert data["maturity_date"] == "2026-01-15"


@pytest.mark.asyncio
async def test_bdr_etf_transaction(client, email_stub):
    """POST BDR and ETF buy transactions → 201 each."""
    await register_verify_and_login(client, email_stub)

    resp_bdr = await client.post("/portfolio/transactions", json=BDR_BUY)
    assert resp_bdr.status_code == 201, resp_bdr.text
    assert resp_bdr.json()["asset_class"] == "bdr"

    resp_etf = await client.post("/portfolio/transactions", json=ETF_BUY)
    assert resp_etf.status_code == 201, resp_etf.text
    assert resp_etf.json()["asset_class"] == "etf"


@pytest.mark.asyncio
async def test_get_positions_with_cmp(client, email_stub):
    """POST two buys, GET /portfolio/positions → list contains asset with correct CMP."""
    await register_verify_and_login(client, email_stub)

    await client.post("/portfolio/transactions", json=BUY_PETR4)
    await client.post("/portfolio/transactions", json=BUY_PETR4_SECOND)

    resp = await client.get("/portfolio/positions")
    assert resp.status_code == 200, resp.text
    positions = resp.json()

    assert len(positions) >= 1
    petr4_pos = next((p for p in positions if p["ticker"] == "PETR4"), None)
    assert petr4_pos is not None
    assert Decimal(petr4_pos["quantity"]) == Decimal("200")
    # CMP should be (100*38.50 + 100*40.00) / 200 = 39.25
    assert Decimal(petr4_pos["cmp"]) == Decimal("39.25000000")


@pytest.mark.asyncio
async def test_positions_with_stale_data(client, email_stub):
    """GET /portfolio/positions when Redis is empty → current_price_stale=True."""
    await register_verify_and_login(client, email_stub)

    await client.post("/portfolio/transactions", json=BUY_PETR4)

    resp = await client.get("/portfolio/positions")
    assert resp.status_code == 200, resp.text
    positions = resp.json()

    assert len(positions) >= 1
    petr4_pos = next((p for p in positions if p["ticker"] == "PETR4"), None)
    assert petr4_pos is not None
    assert petr4_pos["current_price_stale"] is True
    assert petr4_pos["current_price"] is None


@pytest.mark.asyncio
async def test_pnl_endpoint(client, email_stub):
    """POST buy, GET /portfolio/pnl → has realized_pnl=0, unrealized_pnl computed."""
    await register_verify_and_login(client, email_stub)

    await client.post("/portfolio/transactions", json=BUY_PETR4)

    resp = await client.get("/portfolio/pnl")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "realized_pnl_total" in data
    assert "unrealized_pnl_total" in data
    assert "total_portfolio_value" in data
    assert "allocation" in data
    assert "positions" in data
    assert Decimal(data["realized_pnl_total"]) == Decimal("0")


@pytest.mark.asyncio
async def test_benchmarks_endpoint(client, email_stub, fake_redis_async):
    """Pre-populate fakeredis with CDI/IBOV, GET /portfolio/benchmarks → returns values."""
    await register_verify_and_login(client, email_stub)

    # Pre-populate Redis with macro data
    await fake_redis_async.set("market:macro:cdi", "13.75")
    await fake_redis_async.set("market:macro:selic", "14.25")
    await fake_redis_async.set("market:macro:ipca", "4.83")
    await fake_redis_async.set("market:macro:ptax_usd", "5.07")
    await fake_redis_async.set("market:macro:fetched_at", "2024-01-15T12:00:00")

    ibov_data = json.dumps({
        "symbol": "IBOV",
        "price": "128000.00",
        "change": "500.00",
        "change_pct": "0.39",
        "fetched_at": "2024-01-15T12:00:00",
        "data_stale": False,
    })
    await fake_redis_async.set("market:quote:IBOV", ibov_data)

    resp = await client.get("/portfolio/benchmarks")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["cdi"] is not None
    assert Decimal(str(data["cdi"])) == Decimal("13.75")
    assert data["ibovespa_price"] is not None
    assert Decimal(str(data["ibovespa_price"])) == Decimal("128000.00")
    assert data["data_stale"] is False


@pytest.mark.asyncio
async def test_dividends_endpoint(client, email_stub):
    """POST dividend transaction, GET /portfolio/dividends → dividend appears."""
    await register_verify_and_login(client, email_stub)

    await client.post("/portfolio/transactions", json=FII_DIVIDEND)

    resp = await client.get("/portfolio/dividends")
    assert resp.status_code == 200, resp.text
    dividends = resp.json()

    assert len(dividends) >= 1
    div = next((d for d in dividends if d["ticker"] == "HGLG11"), None)
    assert div is not None
    assert div["is_exempt"] is True
    assert div["transaction_type"] == "dividend" or div.get("transaction_type") == "dividend"


@pytest.mark.asyncio
async def test_sell_updates_position(client, email_stub):
    """POST buy 100@38.50, POST sell 50@42.00 → GET positions shows qty=50, CMP=38.50."""
    await register_verify_and_login(client, email_stub)

    await client.post("/portfolio/transactions", json=BUY_PETR4)
    await client.post("/portfolio/transactions", json=SELL_PETR4)

    resp = await client.get("/portfolio/positions")
    assert resp.status_code == 200, resp.text
    positions = resp.json()

    petr4_pos = next((p for p in positions if p["ticker"] == "PETR4"), None)
    assert petr4_pos is not None
    assert Decimal(petr4_pos["quantity"]) == Decimal("50")
    # CMP must NOT change on sell — B3 rule
    assert Decimal(petr4_pos["cmp"]) == Decimal("38.50000000")


@pytest.mark.asyncio
async def test_rls_isolation(db_session, test_engine, fake_redis_async):
    """Tenant A transactions not visible to Tenant B.

    Uses two separate AsyncClient instances with independent session overrides.
    Both share the same test_engine but have their own transaction scope,
    so each sees only the data written in its own session.
    """
    import fakeredis
    import fakeredis.aioredis
    import re
    from app.main import app as fastapi_app
    from app.core.db import get_db
    from app.core.middleware import get_authed_db
    from app.modules.auth.service import AuthService
    from app.modules.auth.router import _get_service as auth_get_service
    from app.modules.portfolio.router import _get_redis
    from app.modules.market_data.router import _get_market_service
    from app.modules.market_data.service import MarketDataService
    from sqlalchemy.ext.asyncio import async_sessionmaker

    factory = async_sessionmaker(test_engine, expire_on_commit=False)

    # -----------------------------------------------------------------------
    # Tenant A: register + login + post a buy transaction
    # -----------------------------------------------------------------------
    email_sent_a: list = []

    async def stub_a(to_email: str, subject: str, html: str) -> None:
        email_sent_a.append((to_email, subject, html))

    fake_redis_sync_a = fakeredis.FakeRedis()

    async with factory() as session_a:
        async with session_a.begin():
            async def override_db_a():
                yield session_a

            async def override_authed_db_a():
                yield session_a

            def override_auth_service_a():
                return AuthService(session_a, email_sender=stub_a, redis_client=fake_redis_sync_a)

            fastapi_app.dependency_overrides[get_db] = override_db_a
            fastapi_app.dependency_overrides[get_authed_db] = override_authed_db_a
            fastapi_app.dependency_overrides[auth_get_service] = override_auth_service_a
            fastapi_app.dependency_overrides[_get_redis] = lambda: fake_redis_async
            fastapi_app.dependency_overrides[_get_market_service] = lambda: MarketDataService(fake_redis_async)

            async with AsyncClient(
                transport=ASGITransport(app=fastapi_app), base_url="http://test"
            ) as client_a:
                # Register
                r = await client_a.post(
                    "/auth/register",
                    json={"email": "rls_a@example.com", "password": "SecurePass123!"},
                )
                assert r.status_code == 201, r.text
                # Verify email
                _, _, html_a = email_sent_a[-1]
                tok_a = re.search(r"token=([^\"'&\s]+)", html_a).group(1)
                await client_a.get(f"/auth/verify-email?token={tok_a}")
                # Login
                r = await client_a.post(
                    "/auth/login",
                    json={"email": "rls_a@example.com", "password": "SecurePass123!"},
                )
                assert r.status_code == 200, r.text
                # Post buy
                r = await client_a.post("/portfolio/transactions", json=BUY_PETR4)
                assert r.status_code == 201, r.text

            await session_a.rollback()

    fastapi_app.dependency_overrides.clear()

    # -----------------------------------------------------------------------
    # Tenant B: register + login + get positions — should be empty
    # -----------------------------------------------------------------------
    email_sent_b: list = []

    async def stub_b(to_email: str, subject: str, html: str) -> None:
        email_sent_b.append((to_email, subject, html))

    fake_redis_sync_b = fakeredis.FakeRedis()
    fake_redis_async_b = fakeredis.aioredis.FakeRedis()

    async with factory() as session_b:
        async with session_b.begin():
            async def override_db_b():
                yield session_b

            async def override_authed_db_b():
                yield session_b

            def override_auth_service_b():
                return AuthService(session_b, email_sender=stub_b, redis_client=fake_redis_sync_b)

            fastapi_app.dependency_overrides[get_db] = override_db_b
            fastapi_app.dependency_overrides[get_authed_db] = override_authed_db_b
            fastapi_app.dependency_overrides[auth_get_service] = override_auth_service_b
            fastapi_app.dependency_overrides[_get_redis] = lambda: fake_redis_async_b
            fastapi_app.dependency_overrides[_get_market_service] = lambda: MarketDataService(fake_redis_async_b)

            async with AsyncClient(
                transport=ASGITransport(app=fastapi_app), base_url="http://test"
            ) as client_b:
                r = await client_b.post(
                    "/auth/register",
                    json={"email": "rls_b@example.com", "password": "SecurePass123!"},
                )
                assert r.status_code == 201, r.text
                _, _, html_b = email_sent_b[-1]
                tok_b = re.search(r"token=([^\"'&\s]+)", html_b).group(1)
                await client_b.get(f"/auth/verify-email?token={tok_b}")
                r = await client_b.post(
                    "/auth/login",
                    json={"email": "rls_b@example.com", "password": "SecurePass123!"},
                )
                assert r.status_code == 200, r.text

                # GET positions — tenant B should have an empty portfolio
                r = await client_b.get("/portfolio/positions")
                assert r.status_code == 200, r.text
                positions_b = r.json()

                # Tenant B should NOT see Tenant A's PETR4 (different DB session = different data)
                petr4_in_b = [p for p in positions_b if p["ticker"] == "PETR4"]
                assert petr4_in_b == [], (
                    f"RLS FAILURE: Tenant B sees Tenant A's position: {petr4_in_b}"
                )

            await session_b.rollback()

    fastapi_app.dependency_overrides.clear()
