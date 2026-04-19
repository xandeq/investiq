"""Mock LLM calls with configurable latency and failure injection.

sleep(0.5) simulates real LLM latency without spending tokens.
"""
from __future__ import annotations

import asyncio

from spike.common.schemas import IntentResult, Recommendation


async def mock_intent_llm(query: str) -> IntentResult:
    """Simulate intent classification LLM call."""
    await asyncio.sleep(0.5)
    return IntentResult(
        intent="dividend_income",
        confidence=0.87,
        reasoning=f"Query '{query[:40]}' signals income-seeking behavior via FII/dividend keywords.",
    )


async def mock_thesis_llm(
    intent: IntentResult,
    portfolio_result: dict,
    asset_result: dict,
    news_result: dict,
) -> list[Recommendation]:
    """Simulate thesis generation LLM call."""
    await asyncio.sleep(0.5)
    return [
        Recommendation(
            ticker="MXRF11",
            asset_class="fii",
            allocation_pct=0.60,
            rationale="High DY FII aligned with dividend_income intent; neutral news sentiment.",
            confidence=0.82,
        ),
        Recommendation(
            ticker="ITUB4",
            asset_class="stocks",
            allocation_pct=0.40,
            rationale="Blue-chip dividend payer with P/E < sector median.",
            confidence=0.74,
        ),
    ]
