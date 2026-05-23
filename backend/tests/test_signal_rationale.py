"""Regression tests for GET /signals/{ticker}/rationale (Phase 67E).

Covers:
  - Unauthenticated access → 401
  - Authenticated + LLM success → returns rationale, confidence, cached=False
  - LLM failure falls back to template text (no 500 raised)
  - Cache hit returns cached=True
  - Invalid ticker rejected
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from tests.conftest import register_verify_and_login

pytestmark = pytest.mark.anyio

_ANALYSIS_APLUS = {
    "ticker": "PETR4",
    "has_setup": True,
    "setup": {
        "pattern": "Bullish Engulfing",
        "direction": "long",
        "entry": 38.00,
        "stop": 35.00,
        "target_1": 47.00,
        "rr": 3.0,
        "grade": "A+",
    },
    "indicators": {
        "volume_ratio": 2.0,
        "regime": "trending_up",
        "confluences": [
            "multi_tf_aligned",
            "RSI neutro (zona de valor)",
            "Acima da EMA200 (tendência de alta)",
            "EMA20 > EMA50 (momentum altista)",
            "MACD acima do sinal",
        ],
    },
}

_ANALYSIS_NO_SETUP = {
    "ticker": "MGLU3",
    "has_setup": False,
    "setup": None,
    "indicators": {
        "volume_ratio": 0.8,
        "regime": "sideways",
        "confluences": ["Acima da EMA200 (tendência de alta)"],
    },
}


async def test_rationale_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/signals/PETR4/rationale")
    assert resp.status_code == 401


async def test_rationale_invalid_ticker_rejected(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="rat0@example.com")
    resp = await client.get("/signals/TOOLONGTICKER123/rationale")
    assert resp.status_code == 400


async def test_rationale_llm_success_aplus(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="rat1@example.com")

    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.setex = AsyncMock()
    fake_redis.aclose = AsyncMock()

    with (
        patch("app.modules.signal_engine.router.analyze", return_value=_ANALYSIS_APLUS),
        patch("app.modules.signal_engine.router._get_async_redis", return_value=fake_redis),
        patch(
            "app.modules.briefing_engine.context_assembler.get_context_batch",
            AsyncMock(return_value={"PETR4": {"sentiment_score": 0.45, "reddit_mentions": 12}}),
        ),
        patch(
            "app.modules.ai.provider.call_llm",
            AsyncMock(return_value="PETR4 apresenta setup técnico A+ com candle de reversão bullish. "
                                   "O sentimento positivo nas redes sociais confirma o interesse dos investidores. "
                                   "Aguardar pullback para zona de entrada com stop definido."),
        ),
    ):
        resp = await client.get("/signals/PETR4/rationale")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "PETR4"
    assert isinstance(data["rationale"], str)
    assert len(data["rationale"]) > 20
    assert data["confidence"] in ("alta", "média", "baixa")
    assert data["cached"] is False


async def test_rationale_llm_failure_returns_template(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="rat2@example.com")

    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.setex = AsyncMock()
    fake_redis.aclose = AsyncMock()

    with (
        patch("app.modules.signal_engine.router.analyze", return_value=_ANALYSIS_APLUS),
        patch("app.modules.signal_engine.router._get_async_redis", return_value=fake_redis),
        patch(
            "app.modules.briefing_engine.context_assembler.get_context_batch",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.modules.ai.provider.call_llm",
            AsyncMock(side_effect=RuntimeError("LLM quota exceeded")),
        ),
    ):
        resp = await client.get("/signals/PETR4/rationale")

    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data["rationale"], str)
    assert len(data["rationale"]) > 10  # template text still present


async def test_rationale_no_setup_fallback(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="rat3@example.com")

    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=None)
    fake_redis.setex = AsyncMock()
    fake_redis.aclose = AsyncMock()

    with (
        patch("app.modules.signal_engine.router.analyze", return_value=_ANALYSIS_NO_SETUP),
        patch("app.modules.signal_engine.router._get_async_redis", return_value=fake_redis),
        patch(
            "app.modules.briefing_engine.context_assembler.get_context_batch",
            AsyncMock(return_value={}),
        ),
        patch(
            "app.modules.ai.provider.call_llm",
            AsyncMock(side_effect=RuntimeError("LLM unavailable")),
        ),
    ):
        resp = await client.get("/signals/MGLU3/rationale")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ticker"] == "MGLU3"
    assert isinstance(data["rationale"], str)


async def test_rationale_cache_hit_returns_cached_true(
    client: AsyncClient, email_stub
) -> None:
    await register_verify_and_login(client, email_stub, email="rat4@example.com")

    cached_payload = json.dumps({
        "ticker": "PETR4",
        "rationale": "Setup A+ confirmado com forte momentum. Sentimento positivo nas redes.",
        "confidence": "alta",
        "cached": False,
    })

    fake_redis = MagicMock()
    fake_redis.get = AsyncMock(return_value=cached_payload)
    fake_redis.aclose = AsyncMock()

    with patch("app.modules.signal_engine.router._get_async_redis", return_value=fake_redis):
        resp = await client.get("/signals/PETR4/rationale")

    assert resp.status_code == 200
    data = resp.json()
    assert data["cached"] is True
    assert "Setup A+" in data["rationale"]
