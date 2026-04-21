"""Signal Engine — Universe scanner for A+ swing trade setups.

Runs chart_analyzer on every ticker in UNIVERSE, applies gate evaluation,
filters to A+ signals only, and caches results in Redis (TTL 30min).
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from app.modules.chart_analyzer.analyzer import analyze
from app.modules.signal_engine.gates import evaluate_signal

logger = logging.getLogger(__name__)

_REDIS_KEY = "signal_engine:active_signals"
_REDIS_TTL = 30 * 60  # 30 minutes

UNIVERSE: list[str] = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3", "BBSE3", "BBAS3",
    "EGIE3", "TOTS3", "HAPV3", "BRFS3", "RDOR3", "SBSP3", "PRIO3", "RENT3",
    "EMBR3", "SUZB3", "LREN3", "B3SA3", "BOVA11",
]


async def _analyze_ticker(ticker: str, brapi_token: str, redis_client: Any) -> dict | None:
    """Analyze a single ticker and return a serializable signal dict if A+, else None."""
    try:
        analysis = await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
        evaluation = evaluate_signal(ticker, analysis)
        if not evaluation.is_a_plus:
            return None
        return {
            "ticker": ticker,
            "grade": evaluation.grade,
            "score": evaluation.score,
            "passed_gates": evaluation.passed_gates,
            "total_gates": evaluation.total_gates,
            "setup": evaluation.setup,
            "confluences": analysis.get("confluences", []),
            "indicators": analysis.get("indicators", {}),
        }
    except Exception as exc:
        logger.warning("scanner: failed to analyze %s: %s", ticker, exc)
        return None


async def scan_universe(
    brapi_token: str,
    redis_client: Any = None,
    max_signals: int = 4,
) -> list[dict]:
    """Scan all tickers in UNIVERSE concurrently.

    Returns up to max_signals A+ signals ordered by score (descending).
    Returns empty list if none qualify.
    """
    tasks = [_analyze_ticker(t, brapi_token, redis_client) for t in UNIVERSE]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    signals: list[dict] = []
    for r in results:
        if isinstance(r, dict):
            signals.append(r)

    signals.sort(key=lambda s: s["score"], reverse=True)
    return signals[:max_signals]


async def get_active_signals(redis_client: Any) -> list[dict]:
    """Fetch A+ signals cached in Redis. Returns empty list on miss or error."""
    if redis_client is None:
        return []
    try:
        raw = await redis_client.get(_REDIS_KEY)
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("scanner.get_active_signals: Redis read failed: %s", exc)
    return []


async def store_signals(redis_client: Any, signals: list[dict]) -> None:
    """Store A+ signals in Redis with TTL 30min."""
    if redis_client is None:
        return
    try:
        await redis_client.setex(_REDIS_KEY, _REDIS_TTL, json.dumps(signals))
    except Exception as exc:
        logger.warning("scanner.store_signals: Redis write failed: %s", exc)
