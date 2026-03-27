"""Tests for Watchlist API endpoints (CRUD + price alert target).

Coverage:
  WATCH-01: Add ticker to watchlist (POST /watchlist)
  WATCH-02: Add duplicate ticker returns 409
  WATCH-03: List watchlist items (GET /watchlist)
  WATCH-04: Delete ticker from watchlist (DELETE /watchlist/{ticker})
  WATCH-05: Delete non-existent ticker returns 404
  WATCH-06: Update notes (PATCH /watchlist/{ticker})
  WATCH-07: Update price_alert_target (PATCH /watchlist/{ticker})
  WATCH-08: Clear price_alert_target by setting to null (PATCH)
  WATCH-09: Get quotes returns price_alert_target in response
  WATCH-10: Ticker is uppercased on add
  WATCH-11: Unauthenticated requests return 401
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def authed_client(client: AsyncClient, email_stub) -> AsyncClient:
    """Client with a logged-in session."""
    await register_verify_and_login(client, email_stub, email="watch@example.com")
    return client


# ---------------------------------------------------------------------------
# WATCH-01: Add ticker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_ticker_to_watchlist(authed_client: AsyncClient):
    resp = await authed_client.post("/watchlist", json={"ticker": "PETR4"})
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["ticker"] == "PETR4"
    assert data["price_alert_target"] is None
    assert data["notes"] is None
    assert "id" in data


# ---------------------------------------------------------------------------
# WATCH-02: Duplicate ticker → 409
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_add_duplicate_ticker_returns_409(authed_client: AsyncClient):
    await authed_client.post("/watchlist", json={"ticker": "VALE3"})
    resp = await authed_client.post("/watchlist", json={"ticker": "VALE3"})
    assert resp.status_code == 409, resp.text


# ---------------------------------------------------------------------------
# WATCH-03: List watchlist
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_watchlist_returns_added_items(authed_client: AsyncClient):
    await authed_client.post("/watchlist", json={"ticker": "WEGE3"})
    await authed_client.post("/watchlist", json={"ticker": "ABEV3"})

    resp = await authed_client.get("/watchlist")
    assert resp.status_code == 200, resp.text
    tickers = [i["ticker"] for i in resp.json()]
    assert "WEGE3" in tickers
    assert "ABEV3" in tickers


# ---------------------------------------------------------------------------
# WATCH-04: Delete ticker
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_ticker_removes_from_watchlist(authed_client: AsyncClient):
    await authed_client.post("/watchlist", json={"ticker": "MGLU3"})
    resp = await authed_client.delete("/watchlist/MGLU3")
    assert resp.status_code == 204, resp.text

    # Confirm it's gone
    list_resp = await authed_client.get("/watchlist")
    tickers = [i["ticker"] for i in list_resp.json()]
    assert "MGLU3" not in tickers


# ---------------------------------------------------------------------------
# WATCH-05: Delete non-existent → 404
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_delete_nonexistent_ticker_returns_404(authed_client: AsyncClient):
    resp = await authed_client.delete("/watchlist/XXXX99")
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# WATCH-06: Update notes
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_notes(authed_client: AsyncClient):
    await authed_client.post("/watchlist", json={"ticker": "ITUB4"})
    resp = await authed_client.patch("/watchlist/ITUB4", json={"notes": "Strong dividend yield"})
    assert resp.status_code == 200, resp.text
    assert resp.json()["notes"] == "Strong dividend yield"


# ---------------------------------------------------------------------------
# WATCH-07: Update price_alert_target
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_update_price_alert_target(authed_client: AsyncClient):
    await authed_client.post("/watchlist", json={"ticker": "BBDC4"})
    resp = await authed_client.patch("/watchlist/BBDC4", json={"price_alert_target": "28.50"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    # price_alert_target can come back as string or number depending on serializer
    assert float(data["price_alert_target"]) == pytest.approx(28.50)


# ---------------------------------------------------------------------------
# WATCH-08: Clear price_alert_target by setting null
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_clear_price_alert_target(authed_client: AsyncClient):
    await authed_client.post("/watchlist", json={"ticker": "BOVA11", "price_alert_target": "115.00"})
    resp = await authed_client.patch("/watchlist/BOVA11", json={"price_alert_target": None})
    assert resp.status_code == 200, resp.text
    assert resp.json()["price_alert_target"] is None


# ---------------------------------------------------------------------------
# WATCH-09: Quotes endpoint includes price_alert_target
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quotes_includes_price_alert_target(authed_client: AsyncClient, fake_redis_async):
    import json
    # Seed Redis with a quote
    await fake_redis_async.set(
        "market:quote:PETR4",
        json.dumps({"symbol": "PETR4", "regularMarketPrice": 38.50}),
        ex=1200,
    )

    await authed_client.post(
        "/watchlist",
        json={"ticker": "PETR4", "price_alert_target": "40.00"},
    )
    resp = await authed_client.get("/watchlist/quotes")
    assert resp.status_code == 200, resp.text
    quotes = resp.json()
    petr4 = next((q for q in quotes if q["ticker"] == "PETR4"), None)
    assert petr4 is not None
    assert float(petr4["price_alert_target"]) == pytest.approx(40.00)


# ---------------------------------------------------------------------------
# WATCH-10: Ticker uppercased
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ticker_is_uppercased(authed_client: AsyncClient):
    resp = await authed_client.post("/watchlist", json={"ticker": "petr4"})
    assert resp.status_code == 201, resp.text
    assert resp.json()["ticker"] == "PETR4"


# ---------------------------------------------------------------------------
# WATCH-11: Unauthenticated → 401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unauthenticated_watchlist_returns_401(client: AsyncClient):
    resp = await client.get("/watchlist")
    assert resp.status_code == 401, resp.text
