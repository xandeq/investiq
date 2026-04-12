"""Tests for GET /renda-fixa/macro-rates endpoint."""
import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login


# ---------------------------------------------------------------------------
# Auth test (no login needed)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_macro_rates_requires_auth(client: AsyncClient):
    """Unauthenticated request returns 401."""
    resp = await client.get("/renda-fixa/macro-rates")
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Authenticated tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_macro_rates_endpoint(client: AsyncClient, db_session, email_stub):
    """Authenticated request returns 200 with cdi and ipca keys."""
    await register_verify_and_login(
        client, email_stub, email="macro_rates@example.com"
    )

    resp = await client.get("/renda-fixa/macro-rates")
    assert resp.status_code == 200
    data = resp.json()
    assert "cdi" in data
    assert "ipca" in data


@pytest.mark.asyncio
async def test_macro_rates_redis_fallback(client: AsyncClient, db_session, email_stub):
    """When Redis is unavailable (default in tests), returns 200 with null cdi and ipca."""
    await register_verify_and_login(
        client, email_stub, email="macro_rates_fallback@example.com"
    )

    resp = await client.get("/renda-fixa/macro-rates")
    assert resp.status_code == 200
    data = resp.json()
    # Redis is not running in test env — both values should be null (graceful fallback)
    assert data["cdi"] is None
    assert data["ipca"] is None
