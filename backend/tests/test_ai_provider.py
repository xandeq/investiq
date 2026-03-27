from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.modules.ai.provider import AIProviderError, _fetch_secret, call_llm


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
async def test_call_llm_admin_falls_back_to_paid_chain_when_free_pool_fails():
    """Integration: admin tier must try paid chain after free models fail."""
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
async def test_call_llm_paid_falls_back_to_free_pool_when_paid_chain_fails():
    """Regression: paid tier must still degrade gracefully if paid providers fail."""
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
