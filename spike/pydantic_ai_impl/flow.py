"""Pydantic AI implementation of decision_copilot_flow.

Architecture:
  Pydantic AI has no built-in graph concept — each agent is an `Agent`.
  Orchestration is plain Python: asyncio.gather() for parallelism,
  try/except + asyncio.sleep() for retry, json.dumps() for "persistence".

  intent_router (Agent, mock model)
       ↓
  asyncio.gather(                ← parallel
    portfolio_agent.run(),
    asset_research_agent.run(),
    news_agent.run(),            ← with retry wrapper
  )
       ↓
  thesis_generator (Agent, mock model)

State persistence: manual — serialize DecisionState to JSON, reload from JSON.
No built-in checkpointer. Requires custom storage (Redis, DB, file).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.test import TestModel

from spike.common.llm_mock import mock_intent_llm, mock_thesis_llm
from spike.common.mocks import (
    asset_research_agent_sync,
    news_agent_async,
    portfolio_agent_sync,
)
from spike.common.schemas import (
    AgentTrace,
    AssetResult,
    DecisionInput,
    DecisionOutput,
    IntentResult,
    NewsResult,
    PortfolioResult,
    Recommendation,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Dependencies (Pydantic AI's DI mechanism)
# ---------------------------------------------------------------------------

@dataclass
class FlowDeps:
    """Injected into every agent run via RunContext[FlowDeps]."""
    decision_input: DecisionInput
    news_fail_times: int = 0
    news_call_key: str = "pai_default"


# ---------------------------------------------------------------------------
# Agent definitions
# ---------------------------------------------------------------------------
# Using TestModel (no LLM calls) — output comes from our mock functions, not
# from LLM text completion. This is the right pattern when you own the logic.
# In production, replace TestModel with "claude-3-5-sonnet-latest" etc.

intent_agent: Agent[FlowDeps, IntentResult] = Agent(
    TestModel(),
    output_type=IntentResult,
    deps_type=FlowDeps,
    name="intent_router",
    system_prompt="Classify investment intent from user query.",
)

portfolio_agent_obj: Agent[FlowDeps, PortfolioResult] = Agent(
    TestModel(),
    output_type=PortfolioResult,
    deps_type=FlowDeps,
    name="portfolio_agent",
    system_prompt="Read and summarize portfolio state.",
)

asset_agent_obj: Agent[FlowDeps, AssetResult] = Agent(
    TestModel(),
    output_type=AssetResult,
    deps_type=FlowDeps,
    name="asset_research_agent",
    system_prompt="Filter asset universe for investment candidates.",
)

news_agent_obj: Agent[FlowDeps, NewsResult] = Agent(
    TestModel(),
    output_type=NewsResult,
    deps_type=FlowDeps,
    name="news_agent",
    system_prompt="Fetch and summarize news for tickers.",
)

thesis_agent_obj: Agent[FlowDeps, list[Recommendation]] = Agent(
    TestModel(),
    output_type=list[Recommendation],
    deps_type=FlowDeps,
    name="thesis_generator",
    system_prompt="Generate investment thesis from research.",
)


# ---------------------------------------------------------------------------
# Override agent outputs with mock functions
# Pydantic AI TestModel ignores system_prompt and calls the first tool/output
# validator. We use `override` context or just call our mocks directly and
# wrap in Agent.run() for tracing. Since TestModel doesn't call real LLM,
# we bypass the model and call our mocks for the actual logic.
# ---------------------------------------------------------------------------

async def _run_intent(deps: FlowDeps) -> tuple[IntentResult, float]:
    t0 = time.perf_counter()
    result = await mock_intent_llm(deps.decision_input.query)
    return result, (time.perf_counter() - t0) * 1000


async def _run_portfolio(deps: FlowDeps) -> tuple[PortfolioResult, float]:
    t0 = time.perf_counter()
    result = await asyncio.get_event_loop().run_in_executor(
        None, portfolio_agent_sync, deps.decision_input.portfolio_context
    )
    return result, (time.perf_counter() - t0) * 1000


async def _run_asset_research(
    deps: FlowDeps, intent: IntentResult
) -> tuple[AssetResult, float]:
    t0 = time.perf_counter()
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        asset_research_agent_sync,
        intent.intent,
        deps.decision_input.portfolio_context.capital_available,
    )
    return result, (time.perf_counter() - t0) * 1000


async def _run_news_with_retry(
    deps: FlowDeps, *, max_retries: int = 3
) -> tuple[NewsResult, float, str | None]:
    """Retry wrapper — 3 attempts with exponential backoff.

    Returns (result, duration_ms, error_or_None).
    On exhaustion: returns degraded NewsResult, not raises.
    """
    t0 = time.perf_counter()
    tickers = ["MXRF11", "ITUB4"]
    last_exc: Exception | None = None

    for attempt in range(1, max_retries + 1):
        try:
            result = await news_agent_async(
                tickers,
                fail_times=deps.news_fail_times,
                call_key=deps.news_call_key,
            )
            logger.info("[news_agent] succeeded on attempt %d", attempt)
            return result, (time.perf_counter() - t0) * 1000, None
        except Exception as exc:
            last_exc = exc
            logger.warning("[news_agent] attempt %d failed: %s", attempt, exc)
            if attempt < max_retries:
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))

    logger.error("[news_agent] all retries exhausted, degrading gracefully")
    return (
        NewsResult(headlines=[], sentiment="unknown", relevant_tickers=[]),
        (time.perf_counter() - t0) * 1000,
        str(last_exc),
    )


async def _run_thesis(
    deps: FlowDeps,
    intent: IntentResult,
    portfolio_result: PortfolioResult,
    asset_result: AssetResult,
    news_result: NewsResult,
) -> tuple[list[Recommendation], float]:
    t0 = time.perf_counter()
    result = await mock_thesis_llm(
        intent=intent,
        portfolio_result=portfolio_result.model_dump(),
        asset_result=asset_result.model_dump(),
        news_result=news_result.model_dump(),
    )
    return result, (time.perf_counter() - t0) * 1000


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

async def run_flow(
    decision_input: DecisionInput,
    *,
    thread_id: str = "default",
    news_fail_times: int = 0,
    state_file: Path | None = None,
) -> DecisionOutput:
    """Execute decision_copilot_flow with Pydantic AI agents.

    Args:
        state_file: If provided, load partial state from JSON (simulates
                    persistence / restart recovery).
    """
    t_total = time.perf_counter()
    traces: list[AgentTrace] = []
    deps = FlowDeps(
        decision_input=decision_input,
        news_fail_times=news_fail_times,
        news_call_key=f"pai_{thread_id}",
    )

    def _trace(agent: str, started: datetime, ms: float, status: str, error: str | None = None) -> None:
        traces.append(AgentTrace(
            agent=agent,
            started_at=started,
            completed_at=started,
            duration_ms=ms,
            status=status,
            error=error,
        ))

    # --- Step 1: intent_router ---
    intent: IntentResult | None = None
    if state_file and state_file.exists():
        saved = json.loads(state_file.read_text())
        if saved.get("intent"):
            intent = IntentResult(**saved["intent"])
            logger.info("[flow] RESUMED — loaded intent from state file")

    if intent is None:
        started = datetime.now(timezone.utc)
        intent, ms = await _run_intent(deps)
        _trace("intent_router", started, ms, "ok")
        logger.info("[intent_router] classified as: %s", intent.intent)

        # Persist partial state after step 1
        if state_file:
            state_file.write_text(json.dumps({"intent": intent.model_dump()}))
            logger.info("[flow] partial state saved after intent_router")

    # --- Step 2: Parallel fan-out ---
    started_parallel = datetime.now(timezone.utc)

    (portfolio_result, p_ms), (asset_result, a_ms), (news_result, n_ms, news_err) = (
        await asyncio.gather(
            _run_portfolio(deps),
            _run_asset_research(deps, intent),
            _run_news_with_retry(deps),
        )
    )

    _trace("portfolio_agent",       started_parallel, p_ms, "ok")
    _trace("asset_research_agent",  started_parallel, a_ms, "ok")
    _trace("news_agent",            started_parallel, n_ms,
           "degraded" if news_err else "ok", news_err)

    logger.info(
        "[parallel] portfolio=%.1fms asset=%.1fms news=%.1fms",
        p_ms, a_ms, n_ms,
    )

    # --- Step 3: thesis_generator (fan-in) ---
    started_thesis = datetime.now(timezone.utc)
    recommendations, t_ms = await _run_thesis(
        deps, intent, portfolio_result, asset_result, news_result
    )
    _trace("thesis_generator", started_thesis, t_ms, "ok")

    total_ms = (time.perf_counter() - t_total) * 1000
    logger.info("[flow] total duration: %.1fms", total_ms)

    return DecisionOutput(
        recommendations=recommendations,
        portfolio_context=decision_input.portfolio_context,
        intent=intent,
        generated_at=datetime.now(timezone.utc),
        trace=traces,
    )


# ---------------------------------------------------------------------------
# State persistence demo
# ---------------------------------------------------------------------------

async def simulate_interrupted_then_resumed(
    decision_input: DecisionInput, state_file: Path
) -> dict:
    """Demonstrate manual state persistence via JSON file.

    Step 1: Run only the intent_router node, save state to file, 'crash'.
    Step 2: Reload from file, resume from portfolio/asset/news onwards.
    """
    deps = FlowDeps(decision_input=decision_input)

    # "First run" — runs intent_router and saves
    started = datetime.now(timezone.utc)
    intent, ms = await _run_intent(deps)
    state_file.write_text(json.dumps({"intent": intent.model_dump()}))
    logger.info("[persistence] intent saved, simulating crash...")

    # "After restart" — load from file
    saved = json.loads(state_file.read_text())
    intent_recovered = IntentResult(**saved["intent"])

    return {
        "thread_id": "persistence-test",
        "state_file": str(state_file),
        "intent_recovered": intent_recovered.intent == intent.intent,
        "intent_value": intent_recovered.intent,
        "loc": "JSON file (manual — no built-in checkpointer)",
        "extra_code_lines": "~15 lines to serialize/deserialize",
        "intrusiveness": "HIGH — must add save/load at every checkpoint boundary",
    }


# ---------------------------------------------------------------------------
# SSE streaming — manual event emitter
# ---------------------------------------------------------------------------

async def stream_sse_events(decision_input: DecisionInput):
    """Yield SSE-style events. No built-in streaming — manual yield pattern."""
    deps = FlowDeps(decision_input=decision_input)

    # intent_router
    yield {"event": "node_start", "node": "intent_router", "data": {}}
    intent, _ = await _run_intent(deps)
    yield {"event": "node_end", "node": "intent_router", "data": intent.model_dump()}

    # Parallel nodes — can't easily stream individual completions from gather()
    # Must fire and yield after all complete, OR use separate Tasks + queues
    yield {"event": "node_start", "node": "parallel_fan_out", "data": {}}
    (portfolio_result, _), (asset_result, _), (news_result, _, _) = await asyncio.gather(
        _run_portfolio(deps),
        _run_asset_research(deps, intent),
        _run_news_with_retry(deps),
    )
    yield {"event": "node_end", "node": "portfolio_agent", "data": portfolio_result.model_dump()}
    yield {"event": "node_end", "node": "asset_research_agent", "data": asset_result.model_dump()}
    yield {"event": "node_end", "node": "news_agent", "data": news_result.model_dump()}

    # thesis_generator
    yield {"event": "node_start", "node": "thesis_generator", "data": {}}
    recommendations, _ = await _run_thesis(deps, intent, portfolio_result, asset_result, news_result)
    yield {"event": "node_end", "node": "thesis_generator",
           "data": [r.model_dump() for r in recommendations]}
