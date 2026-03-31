"""LLM cost tracking for the AI Analysis module (Phase 12).

Estimates and logs per-analysis LLM costs based on provider pricing.
Free-tier providers (Groq) return cost=0.0.

Pricing data from RESEARCH.md Section 2.3 (as of March 2026).
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal

logger = logging.getLogger(__name__)

# Pricing per token (USD) — keyed as "provider/model"
# Source: RESEARCH.md Section 2.3, verified March 2026
_PRICING: dict[str, dict[str, float]] = {
    "openrouter/openai/gpt-4o-mini": {
        "input": 0.000150,
        "output": 0.000600,
    },
    "openrouter/deepseek/deepseek-chat": {
        "input": 0.000014,
        "output": 0.000056,
    },
    "groq/llama-3.3-70b-versatile": {
        "input": 0.0,
        "output": 0.0,
    },
    "groq/llama-3.1-8b-instant": {
        "input": 0.0,
        "output": 0.0,
    },
}


def estimate_llm_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> float:
    """Estimate LLM cost in USD. Returns 0.0 for free-tier providers.

    Looks up pricing by "provider/model" key. If not found, returns 0.0
    with a warning log (unknown provider should be investigated).
    """
    key = f"{provider}/{model}"
    pricing = _PRICING.get(key)

    if pricing is None:
        logger.warning("analysis.cost_unknown_model key=%s", key)
        return 0.0

    cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])
    return round(cost, 6)


def log_analysis_cost(
    tenant_id: str,
    job_id: str,
    analysis_type: str,
    ticker: str,
    duration_ms: int,
    status: str,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> None:
    """Log analysis cost to database.

    Creates an AnalysisCostLog row with estimated_cost_usd calculated
    from provider pricing if provider/model/tokens are provided.

    Uses superuser session to bypass RLS (cost logging is system-level).
    Never raises — cost logging must not break the main task flow.
    """
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.analysis.models import AnalysisCostLog

        estimated_cost: Decimal | None = None
        if llm_provider and llm_model and input_tokens is not None and output_tokens is not None:
            cost_float = estimate_llm_cost(llm_provider, llm_model, input_tokens, output_tokens)
            estimated_cost = Decimal(str(cost_float))

        cost_log = AnalysisCostLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            job_id=job_id,
            analysis_type=analysis_type,
            ticker=ticker,
            llm_provider=llm_provider,
            llm_model=llm_model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=estimated_cost,
            duration_ms=duration_ms,
            status=status,
            created_at=datetime.now(tz=timezone.utc),
        )

        with get_superuser_sync_db_session() as session:
            session.add(cost_log)

        logger.info(
            "analysis.cost_logged job_id=%s type=%s ticker=%s cost_usd=%s",
            job_id, analysis_type, ticker, estimated_cost,
        )
    except Exception as exc:
        logger.warning("Failed to log analysis cost (non-fatal): %s", exc)
