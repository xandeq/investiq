from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.ai.provider import (
    _FREE_MODEL_POOL,
    AIProviderError,
    _fetch_secret,
    call_llm,
)


def test_fetch_secret_prefers_environment_variable(monkeypatch):
    """Regression: runtime env must override stale AWS secrets."""
    monkeypatch.setenv("OPENAI_API_KEY", "env-openai-key")

    with patch("app.modules.ai.provider.subprocess.run") as mock_run:
        value = _fetch_secret("tools/openai", "OPENAI_API_KEY")

    assert value == "env-openai-key"
    mock_run.assert_not_called()


def test_fetch_secret_uses_aws_when_env_missing(monkeypatch):
    """Smoke: AWS SM is used when no runtime override exists."""
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

    with patch("app.modules.ai.provider.subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = '{"OPENROUTER_API_KEY":"aws-openrouter-key"}'
        value = _fetch_secret("tools/openrouter", "OPENROUTER_API_KEY")

    assert value == "aws-openrouter-key"
    mock_run.assert_called_once()


@pytest.mark.asyncio
async def test_call_llm_admin_falls_back_to_paid_chain_when_free_pool_fails(monkeypatch):
    """Integration: admin tier must try paid chain after free models fail."""
    monkeypatch.setenv("AI_FORCE_FREE", "false")  # tier-routing test — bypass kill-switch
    with patch(
        "app.modules.ai.provider._call_free_pool",
        new=AsyncMock(side_effect=AIProviderError("free path failed")),
    ), patch(
        "app.modules.ai.provider._call_paid_chain",
        new=AsyncMock(return_value="paid-fallback-ok"),
    ) as mock_paid:
        result = await call_llm("prompt", system="system", tier="admin")

    assert result == "paid-fallback-ok"
    mock_paid.assert_awaited_once()


@pytest.mark.asyncio
async def test_call_llm_paid_falls_back_to_free_pool_when_paid_chain_fails(monkeypatch):
    """Regression: paid tier must still degrade gracefully if paid providers fail."""
    monkeypatch.setenv("AI_FORCE_FREE", "false")  # tier-routing test — bypass kill-switch
    with patch(
        "app.modules.ai.provider._call_paid_chain",
        new=AsyncMock(side_effect=AIProviderError("paid path failed")),
    ), patch(
        "app.modules.ai.provider._call_free_pool",
        new=AsyncMock(return_value="free-fallback-ok"),
    ) as mock_free:
        result = await call_llm("prompt", system="system", tier="paid")

    assert result == "free-fallback-ok"
    mock_free.assert_awaited_once()


# ---------------------------------------------------------------------------
# AI_FORCE_FREE kill-switch (2026-06-07) — force every tier to the free pool
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
@pytest.mark.parametrize("tier", ["paid", "ultra", "admin", "free"])
async def test_force_free_routes_every_tier_to_free_pool(monkeypatch, tier):
    """Cost kill-switch: when AI_FORCE_FREE=true, no paid/ultra chain may run."""
    monkeypatch.setenv("AI_FORCE_FREE", "true")
    with patch(
        "app.modules.ai.provider._call_free_pool",
        new=AsyncMock(return_value="free-ok"),
    ) as mock_free, patch(
        "app.modules.ai.provider._call_paid_chain",
        new=AsyncMock(return_value="paid-NOT-allowed"),
    ) as mock_paid, patch(
        "app.modules.ai.provider._call_ultra_chain",
        new=AsyncMock(return_value="ultra-NOT-allowed"),
    ) as mock_ultra:
        result = await call_llm("prompt", system="system", tier=tier)

    assert result == "free-ok"
    mock_free.assert_awaited_once()
    mock_paid.assert_not_awaited()
    mock_ultra.assert_not_awaited()


@pytest.mark.asyncio
async def test_force_free_off_allows_paid_chain(monkeypatch):
    """Switch off: paid tier reaches the paid chain again (regression guard)."""
    monkeypatch.setenv("AI_FORCE_FREE", "false")
    with patch(
        "app.modules.ai.provider._call_paid_chain",
        new=AsyncMock(return_value="paid-ok"),
    ) as mock_paid:
        result = await call_llm("prompt", system="system", tier="paid")

    assert result == "paid-ok"
    mock_paid.assert_awaited_once()


def test_free_pool_includes_openrouter_free_models():
    """Regression: free pool must contain OpenRouter :free models with openrouter style."""
    openrouter_entries = [e for e in _FREE_MODEL_POOL if e[0] == "openrouter"]
    assert openrouter_entries, "no openrouter models in free pool"
    for provider, model, style in openrouter_entries:
        assert model.endswith(":free"), f"{model} is not a free model"
        assert style == "openrouter"


def test_free_pool_has_multiple_providers_for_failover():
    """Free models must span >=3 providers so one slow/down provider fails over."""
    providers = {e[0] for e in _FREE_MODEL_POOL}
    assert len(providers) >= 3, f"only {providers} — not enough for robust failover"


# ---------------------------------------------------------------------------
# Cheap tier (2026-06-07) — DeepSeek → Grok-3-mini → gpt-4o-mini → free
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_cheap_tier_uses_cheap_chain(monkeypatch):
    """Cheap tier must route to the cheap chain when kill-switch is off."""
    monkeypatch.setenv("AI_FORCE_FREE", "false")
    with patch(
        "app.modules.ai.provider._call_cheap_chain",
        new=AsyncMock(return_value="cheap-ok"),
    ) as mock_cheap:
        result = await call_llm("prompt", system="system", tier="cheap")

    assert result == "cheap-ok"
    mock_cheap.assert_awaited_once()


@pytest.mark.asyncio
async def test_cheap_tier_falls_back_to_free_pool(monkeypatch):
    """Cheap tier must degrade to the free pool if all cheap providers fail."""
    monkeypatch.setenv("AI_FORCE_FREE", "false")
    with patch(
        "app.modules.ai.provider._call_cheap_chain",
        new=AsyncMock(side_effect=AIProviderError("cheap failed")),
    ), patch(
        "app.modules.ai.provider._call_free_pool",
        new=AsyncMock(return_value="free-fallback-ok"),
    ) as mock_free:
        result = await call_llm("prompt", system="system", tier="cheap")

    assert result == "free-fallback-ok"
    mock_free.assert_awaited_once()


@pytest.mark.asyncio
async def test_force_free_overrides_cheap_tier(monkeypatch):
    """Kill-switch must intercept the cheap tier too (no paid spend)."""
    monkeypatch.setenv("AI_FORCE_FREE", "true")
    with patch(
        "app.modules.ai.provider._call_free_pool",
        new=AsyncMock(return_value="free-ok"),
    ) as mock_free, patch(
        "app.modules.ai.provider._call_cheap_chain",
        new=AsyncMock(return_value="cheap-NOT-allowed"),
    ) as mock_cheap:
        result = await call_llm("prompt", system="system", tier="cheap")

    assert result == "free-ok"
    mock_free.assert_awaited_once()
    mock_cheap.assert_not_awaited()
