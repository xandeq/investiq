"""HTTP endpoint tests for GET /market-data/* router.

Coverage:
  MD-02: GET /market-data/macro  — returns stale when Redis empty
  MD-03: GET /market-data/macro  — returns real data when Redis seeded

  MD-05: GET /market-data/fundamentals/{ticker}  — stale when cache miss
  MD-06: GET /market-data/fundamentals/{ticker}  — correct shape when seeded

  MD-08: GET /market-data/quote/{ticker}  — stale when cache miss
  MD-09: GET /market-data/quote/{ticker}  — correct shape + values when seeded

  MD-11: GET /market-data/historical/{ticker}  — stale when cache miss

Note: Auth (401) tests are omitted for market-data endpoints. These endpoints use only
`get_authed_db` (which conftest overrides to bypass JWT in tests), not `get_current_tenant_id`.
Auth IS enforced in production — it just cannot be exercised at the HTTP level in the SQLite
test environment.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EPOCH_STR = "2000-01-01T00:00:00"


# ---------------------------------------------------------------------------
# Macro
# ---------------------------------------------------------------------------


async def test_macro_stale_when_empty(
    client: AsyncClient, email_stub
) -> None:
    """MD-02: GET /market-data/macro returns data_stale=True when Redis has no macro keys."""
    await register_verify_and_login(client, email_stub, email="macro_stale@test.com")
    resp = await client.get("/market-data/macro")
    assert resp.status_code == 200
    data = resp.json()
    assert "data_stale" in data
    assert data["data_stale"] is True
    assert "selic" in data
    assert "cdi" in data


async def test_macro_returns_seeded_data(
    client: AsyncClient, email_stub, fake_redis_async
) -> None:
    """MD-03: GET /market-data/macro returns correct values when Redis is seeded."""
    await fake_redis_async.set("market:macro:selic", "14.75")
    await fake_redis_async.set("market:macro:cdi", "14.65")
    await fake_redis_async.set("market:macro:ipca", "4.83")
    await fake_redis_async.set("market:macro:ptax_usd", "5.10")
    await fake_redis_async.set("market:macro:fetched_at", datetime.now(timezone.utc).isoformat())

    await register_verify_and_login(client, email_stub, email="macro_seeded@test.com")
    resp = await client.get("/market-data/macro")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_stale"] is False
    assert float(data["selic"]) == pytest.approx(14.75)
    assert float(data["cdi"]) == pytest.approx(14.65)


# ---------------------------------------------------------------------------
# Fundamentals
# ---------------------------------------------------------------------------


async def test_fundamentals_stale_on_cache_miss(
    client: AsyncClient, email_stub
) -> None:
    """MD-05: GET /market-data/fundamentals/{ticker} returns data_stale=True for unknown ticker."""
    await register_verify_and_login(client, email_stub, email="fund_stale@test.com")
    resp = await client.get("/market-data/fundamentals/UNKNOWN99")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_stale"] is True
    assert "ticker" in data


async def test_fundamentals_seeded_data(
    client: AsyncClient, email_stub, fake_redis_async
) -> None:
    """MD-06: GET /market-data/fundamentals/{ticker} returns correct shape when Redis seeded."""
    payload = json.dumps({
        "ticker": "VALE3",
        "pl": 8.5,
        "pvp": 1.2,
        "dy": 9.3,
        "ev_ebitda": 4.1,
        "fetched_at": _EPOCH_STR,
        "data_stale": False,
    })
    await fake_redis_async.set("market:fundamentals:VALE3", payload.encode())

    await register_verify_and_login(client, email_stub, email="fund_seeded@test.com")
    resp = await client.get("/market-data/fundamentals/VALE3")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_stale"] is False
    assert data["ticker"] == "VALE3"
    assert float(data["pl"]) == pytest.approx(8.5)
    assert float(data["dy"]) == pytest.approx(9.3)


# ---------------------------------------------------------------------------
# Quote
# ---------------------------------------------------------------------------


async def test_quote_stale_on_cache_miss(
    client: AsyncClient, email_stub
) -> None:
    """MD-08: GET /market-data/quote/{ticker} returns data_stale=True for unknown ticker."""
    await register_verify_and_login(client, email_stub, email="quote_stale@test.com")
    resp = await client.get("/market-data/quote/NOTICKER99")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_stale"] is True
    assert "price" in data
    assert "change_pct" in data


async def test_quote_seeded_data(
    client: AsyncClient, email_stub, fake_redis_async
) -> None:
    """MD-09: GET /market-data/quote/{ticker} returns correct price data when Redis seeded."""
    payload = json.dumps({
        "symbol": "ITUB4",
        "regularMarketPrice": 32.50,
        "regularMarketChange": 0.75,
        "regularMarketChangePercent": 2.36,
        "fetched_at": _EPOCH_STR,
    })
    await fake_redis_async.set("market:quote:ITUB4", payload.encode(), ex=1200)

    await register_verify_and_login(client, email_stub, email="quote_seeded@test.com")
    resp = await client.get("/market-data/quote/ITUB4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_stale"] is False
    assert data["symbol"] == "ITUB4"
    assert float(data["price"]) == pytest.approx(32.50)
    assert float(data["change_pct"]) == pytest.approx(2.36)


# ---------------------------------------------------------------------------
# Historical
# ---------------------------------------------------------------------------


async def test_historical_stale_on_cache_miss(
    client: AsyncClient, email_stub
) -> None:
    """MD-11: GET /market-data/historical/{ticker} returns data_stale=True for unknown ticker."""
    await register_verify_and_login(client, email_stub, email="hist_stale@test.com")
    resp = await client.get("/market-data/historical/NOSTOCKHERE")
    assert resp.status_code == 200
    data = resp.json()
    assert data["data_stale"] is True
    assert "ticker" in data
    assert "points" in data
    assert isinstance(data["points"], list)
