"""Mock agent functions — pure Python, no framework dependencies.

Each function simulates what a real agent would do.
news_agent has a configurable failure mode for retry testing (criterion 3).
"""
from __future__ import annotations

import asyncio
import time

from spike.common.schemas import AssetResult, NewsResult, PortfolioContext, PortfolioResult


def portfolio_agent_sync(portfolio_ctx: PortfolioContext) -> PortfolioResult:
    """Sync function — simulates DB read of portfolio positions (~100ms)."""
    time.sleep(0.10)
    return PortfolioResult(
        available_capital=portfolio_ctx.capital_available,
        current_stocks_pct=portfolio_ctx.current_allocation.get("stocks", 0.0),
        current_fii_pct=portfolio_ctx.current_allocation.get("fii", 0.0),
        current_rf_pct=portfolio_ctx.current_allocation.get("rf", 0.0),
        rebalancing_needed=portfolio_ctx.current_allocation.get("stocks", 0.0) > 0.5,
    )


def asset_research_agent_sync(intent: str, capital: float) -> AssetResult:
    """Sync function — filters asset universe by intent and capital (~150ms)."""
    time.sleep(0.15)
    candidates = [
        {"ticker": "MXRF11", "dy": 0.12, "class": "fii"},
        {"ticker": "HGLG11", "dy": 0.09, "class": "fii"},
        {"ticker": "ITUB4",  "dy": 0.06, "class": "stocks"},
    ] if "dividend" in intent else [
        {"ticker": "WEGE3",  "dy": 0.02, "class": "stocks"},
        {"ticker": "BOVA11", "dy": 0.04, "class": "etf"},
    ]
    return AssetResult(
        candidates=[c for c in candidates if capital >= 100],
        filter_applied=f"intent={intent}, capital={capital}",
        universe_size=len(candidates),
    )


_news_fail_count: dict[str, int] = {}


async def news_agent_async(
    tickers: list[str],
    *,
    fail_times: int = 0,
    call_key: str = "default",
) -> NewsResult:
    """Async function — simulates news API call with injected failure.

    Args:
        tickers: Tickers to fetch news for.
        fail_times: How many times to fail before succeeding (for retry testing).
        call_key: Unique key per test to isolate failure counters.
    """
    _news_fail_count.setdefault(call_key, 0)
    if _news_fail_count[call_key] < fail_times:
        _news_fail_count[call_key] += 1
        raise RuntimeError(
            f"[news_agent] Simulated failure {_news_fail_count[call_key]}/{fail_times} "
            f"for tickers={tickers}"
        )
    await asyncio.sleep(0.3)
    return NewsResult(
        headlines=[
            "FII market resilient amid rate concerns",
            "ITUB4 dividend yield hits 5-year high",
        ],
        sentiment="neutral",
        relevant_tickers=tickers[:2],
    )
