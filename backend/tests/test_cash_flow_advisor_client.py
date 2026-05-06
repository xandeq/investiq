"""Tests for DIAX cash-flow projection client."""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal

import httpx
import pytest

from app.modules.cash_flow_advisor.client import DiaxClient, DiaxNotConfigured


class AsyncRedisStub:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.setex_calls = 0

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.setex_calls += 1
        self.store[key] = value


@pytest.mark.asyncio
async def test_diax_client_raises_when_unconfigured(monkeypatch) -> None:
    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_BASE_URL", "")
    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_INTEGRATION_KEY", "")

    with pytest.raises(DiaxNotConfigured):
        await DiaxClient(redis_client=AsyncRedisStub()).get_cash_flow_projection()


@pytest.mark.asyncio
async def test_diax_client_fetches_projection_with_integration_key(monkeypatch) -> None:
    captured_headers: dict[str, str] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_headers.update(request.headers)
        return httpx.Response(
            200,
            json={
                "currentBalance": "25000.00",
                "availableToInvest": "17000.00",
                "nextBigOutflow": {
                    "date": "2026-05-15",
                    "amount": "8000.00",
                    "description": "Cartao",
                },
                "dailyProjection": [],
            },
        )

    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_BASE_URL", "https://diax.test")
    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_INTEGRATION_KEY", "secret-key")
    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        projection = await DiaxClient(
            redis_client=AsyncRedisStub(),
            http_client=http_client,
        ).get_cash_flow_projection()

    assert captured_headers["x-integration-key"] == "secret-key"
    assert projection.current_balance == Decimal("25000.00")
    assert projection.available_to_invest == Decimal("17000.00")
    assert projection.next_big_outflow is not None
    assert projection.next_big_outflow.date == date(2026, 5, 15)


@pytest.mark.asyncio
async def test_diax_client_reuses_cached_projection(monkeypatch) -> None:
    calls = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            200,
            json={
                "currentBalance": "1.00",
                "availableToInvest": "2.00",
                "nextBigOutflow": None,
                "dailyProjection": [],
            },
        )

    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_BASE_URL", "https://diax.test")
    monkeypatch.setattr("app.modules.cash_flow_advisor.client.settings.DIAX_INTEGRATION_KEY", "secret-key")
    redis = AsyncRedisStub()
    transport = httpx.MockTransport(handler)

    async with httpx.AsyncClient(transport=transport) as http_client:
        client = DiaxClient(redis_client=redis, http_client=http_client)
        first = await client.get_cash_flow_projection()
        second = await client.get_cash_flow_projection()

    assert first.available_to_invest == Decimal("2.00")
    assert second.available_to_invest == Decimal("2.00")
    assert calls == 1
    assert redis.setex_calls == 1
    cached = json.loads(redis.store["cash_flow_advisor:diax_projection"])
    assert cached["availableToInvest"] == "2.00"
