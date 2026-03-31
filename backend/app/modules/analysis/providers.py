"""LLM provider fallback chain for the AI Analysis module (Phase 12).

Implements a two-provider chain (OpenRouter -> Groq) with timeout-based
fallback. If all providers fail, raises AIProviderError.

Also provides a cached-analysis fallback for quota exhaustion scenarios.
"""
from __future__ import annotations

import asyncio
import logging
import os
from datetime import timezone

import httpx

logger = logging.getLogger(__name__)


class AIProviderError(Exception):
    """All analysis LLM providers exhausted."""

    pass


# Provider fallback chain configuration (from RESEARCH.md Section 5.2)
ANALYSIS_LLM_CHAIN = [
    {
        "provider": "openrouter",
        "model": "openai/gpt-4o-mini",
        "cost_per_1k_input": 0.15,
        "cost_per_1k_output": 0.60,
        "timeout_seconds": 30,
        "max_retries": 1,
    },
    {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "cost_per_1k_input": 0.0,
        "cost_per_1k_output": 0.0,
        "timeout_seconds": 20,
        "max_retries": 1,
    },
]

_SYSTEM_PROMPT = "You are a financial analyst. Be concise and factual."


async def call_analysis_llm(prompt: str, max_tokens: int = 300) -> tuple[str, dict]:
    """Call LLM with fallback chain for analysis tasks.

    Iterates through ANALYSIS_LLM_CHAIN. On timeout or failure, falls back
    to the next provider. Returns (response_text, metadata_dict).

    Raises:
        AIProviderError: If all providers in the chain fail.
    """
    errors: list[str] = []

    for config in ANALYSIS_LLM_CHAIN:
        provider = config["provider"]
        model = config["model"]
        timeout = config["timeout_seconds"]

        try:
            if provider == "openrouter":
                coro = _call_openrouter(prompt, model, max_tokens)
            elif provider == "groq":
                coro = _call_groq(prompt, model, max_tokens)
            else:
                logger.warning("Unknown provider %s — skipping", provider)
                errors.append(f"{provider}: unknown provider")
                continue

            response_text = await asyncio.wait_for(coro, timeout=timeout)
            return (
                response_text,
                {
                    "provider_used": provider,
                    "model": model,
                    "success": True,
                },
            )

        except asyncio.TimeoutError:
            msg = f"{provider}/{model}: timeout after {timeout}s"
            logger.warning("Analysis LLM %s", msg)
            errors.append(msg)
        except Exception as exc:
            msg = f"{provider}/{model}: {exc}"
            logger.warning("Analysis LLM %s", msg)
            errors.append(msg)

    raise AIProviderError(
        f"All analysis LLM providers exhausted. Errors: {'; '.join(errors[:5])}"
    )


async def _call_openrouter(prompt: str, model: str, max_tokens: int) -> str:
    """Call OpenRouter via the existing call_llm from ai.provider."""
    from app.modules.ai.provider import call_llm

    return await call_llm(
        prompt,
        system=_SYSTEM_PROMPT,
        tier="paid",
        max_tokens=max_tokens,
    )


async def _call_groq(prompt: str, model: str, max_tokens: int) -> str:
    """Call Groq API directly via httpx."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not set")

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.7,
            },
        )
        if resp.status_code == 200:
            return resp.json()["choices"][0]["message"]["content"]
        raise httpx.HTTPStatusError(
            f"HTTP {resp.status_code}: {resp.text[:200]}",
            request=resp.request,
            response=resp,
        )


def _get_cached_analysis_with_outdated_badge(
    ticker: str, analysis_type: str
) -> dict | None:
    """Return the most recent completed analysis with an outdated badge.

    Used as fallback when LLM quota is exhausted — shows stale data with
    a clear warning rather than failing completely.
    """
    import json

    from sqlalchemy import select

    from app.core.db_sync import get_superuser_sync_db_session
    from app.modules.analysis.models import AnalysisJob

    try:
        with get_superuser_sync_db_session() as session:
            stmt = (
                select(AnalysisJob)
                .where(
                    AnalysisJob.ticker == ticker,
                    AnalysisJob.analysis_type == analysis_type,
                    AnalysisJob.status == "completed",
                )
                .order_by(AnalysisJob.completed_at.desc())
                .limit(1)
            )
            job = session.execute(stmt).scalar_one_or_none()

            if job and job.result_json:
                result = json.loads(job.result_json)
                result["_outdated"] = True
                result["_outdated_reason"] = (
                    f"Analysis LLM quota exhausted. Results from "
                    f"{job.completed_at}. Contact support to refresh."
                )
                return result
    except Exception as exc:
        logger.warning("Failed to fetch cached analysis for %s: %s", ticker, exc)

    return None
