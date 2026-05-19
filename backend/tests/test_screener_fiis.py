"""Tests for GET /screener/fiis and GET /screener/fiis/export endpoints.

Coverage:
- Auth required on both endpoints
- /screener/fiis returns paginated JSON with disclaimer
- /screener/fiis/export returns CSV with correct headers and CVM disclaimer row
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login

pytestmark = pytest.mark.asyncio


async def test_screener_fiis_requires_auth(client: AsyncClient) -> None:
    """GET /screener/fiis returns 401 when not authenticated."""
    resp = await client.get("/screener/fiis")
    assert resp.status_code == 401


async def test_screener_fiis_export_requires_auth(client: AsyncClient) -> None:
    """GET /screener/fiis/export returns 401 when not authenticated."""
    resp = await client.get("/screener/fiis/export")
    assert resp.status_code == 401


async def test_screener_fiis_authenticated_empty(
    client: AsyncClient, email_stub
) -> None:
    """GET /screener/fiis returns 200 with empty results when no snapshot data exists."""
    await register_verify_and_login(client, email_stub)
    resp = await client.get("/screener/fiis")
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "total" in data
    assert "disclaimer" in data
    assert isinstance(data["results"], list)


async def test_screener_fiis_export_returns_csv(
    client: AsyncClient, email_stub
) -> None:
    """GET /screener/fiis/export returns CSV with correct content-type and header row."""
    await register_verify_and_login(client, email_stub)
    resp = await client.get("/screener/fiis/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    text = resp.text
    lines = [l for l in text.splitlines() if l.strip()]
    # First line must be the CSV header
    assert lines[0].startswith("Ticker")
    assert "DY" in lines[0]
    assert "P/VP" in lines[0]
    # Last non-empty line is the CVM disclaimer
    assert "CVM" in lines[-1]


async def test_screener_fiis_export_respects_filters(
    client: AsyncClient, email_stub
) -> None:
    """GET /screener/fiis/export accepts filter params without error (no snapshot data → header only)."""
    await register_verify_and_login(client, email_stub)
    resp = await client.get("/screener/fiis/export?min_dy=7&max_pvp=1.1&segmento=Tijolo")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# Ações screener export tests
# ---------------------------------------------------------------------------


async def test_screener_acoes_requires_auth(client: AsyncClient) -> None:
    """GET /screener/acoes returns 401 when not authenticated."""
    resp = await client.get("/screener/acoes")
    assert resp.status_code == 401


async def test_screener_acoes_export_requires_auth(client: AsyncClient) -> None:
    """GET /screener/acoes/export returns 401 when not authenticated."""
    resp = await client.get("/screener/acoes/export")
    assert resp.status_code == 401


async def test_screener_acoes_export_returns_csv(
    client: AsyncClient, email_stub
) -> None:
    """GET /screener/acoes/export returns CSV with correct content-type and header row."""
    await register_verify_and_login(client, email_stub)
    resp = await client.get("/screener/acoes/export")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
    assert "attachment" in resp.headers.get("content-disposition", "")

    text = resp.text
    lines = [line for line in text.splitlines() if line.strip()]
    assert lines[0].startswith("Ticker")
    assert "P/L" in lines[0]
    assert "P/VP" in lines[0]
    assert "CVM" in lines[-1]


async def test_screener_acoes_export_respects_filters(
    client: AsyncClient, email_stub
) -> None:
    """GET /screener/acoes/export accepts filter params without error."""
    await register_verify_and_login(client, email_stub)
    resp = await client.get("/screener/acoes/export?min_dy=5&max_pl=20&sector=Financeiro")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers.get("content-type", "")
