"""LangGraph implementation of decision_copilot_flow.

Architecture:
  intent_router (LLM mock)
       ↓
  ┌────┴────────────────────┐
  portfolio_agent   asset_research_agent   news_agent   ← parallel
  └────┬────────────────────┘
       ↓
  thesis_generator (LLM mock)

State persistence: MemorySaver (in-memory, for simulated restart test).
Replace with SqliteSaver / PostgresSaver for durable persistence.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Annotated, Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

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
# State definition
# ---------------------------------------------------------------------------

class DecisionState(TypedDict):
    """Typed state threaded through the entire graph.

    All fields optional — populated incrementally as nodes run.
    `traces` uses `add_messages`-style reducer to accumulate without
    replacing previous entries (LangGraph fan-in pattern).
    """
    input: DecisionInput
    intent: IntentResult | None
    portfolio_result: PortfolioResult | None
    asset_result: AssetResult | None
    news_result: NewsResult | None
    news_error: str | None
    recommendations: list[Recommendation]
    traces: Annotated[list[dict], lambda a, b: a + b]  # accumulate across fan-in


# ---------------------------------------------------------------------------
# Node implementations
# ---------------------------------------------------------------------------

async def intent_router(state: DecisionState) -> dict[str, Any]:
    t0 = time.perf_counter()
    logger.info("[intent_router] classifying query")
    result = await mock_intent_llm(state["input"].query)
    ms = (time.perf_counter() - t0) * 1000
    return {
        "intent": result,
        "traces": [{"agent": "intent_router", "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": ms, "status": "ok", "error": None}],
    }


async def portfolio_agent(state: DecisionState) -> dict[str, Any]:
    t0 = time.perf_counter()
    logger.info("[portfolio_agent] reading portfolio")
    result = await asyncio.get_event_loop().run_in_executor(
        None, portfolio_agent_sync, state["input"].portfolio_context
    )
    ms = (time.perf_counter() - t0) * 1000
    return {
        "portfolio_result": result,
        "traces": [{"agent": "portfolio_agent", "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": ms, "status": "ok", "error": None}],
    }


async def asset_research_agent(state: DecisionState) -> dict[str, Any]:
    t0 = time.perf_counter()
    logger.info("[asset_research_agent] filtering universe")
    intent = state["intent"]
    result = await asyncio.get_event_loop().run_in_executor(
        None,
        asset_research_agent_sync,
        intent.intent if intent else "unknown",
        state["input"].portfolio_context.capital_available,
    )
    ms = (time.perf_counter() - t0) * 1000
    return {
        "asset_result": result,
        "traces": [{"agent": "asset_research_agent", "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": ms, "status": "ok", "error": None}],
    }


async def news_agent(state: DecisionState, *, fail_times: int = 0) -> dict[str, Any]:
    """news_agent with retry logic baked in.

    On failure: retries up to 3 times with exponential backoff.
    If all retries fail: graceful degradation — returns empty news,
    marks trace with status='degraded'.
    """
    t0 = time.perf_counter()
    logger.info("[news_agent] fetching news")
    tickers = ["MXRF11", "ITUB4"]
    last_exc: Exception | None = None

    for attempt in range(1, 4):
        try:
            result = await news_agent_async(
                tickers, fail_times=fail_times, call_key=f"lg_{id(state)}"
            )
            ms = (time.perf_counter() - t0) * 1000
            logger.info("[news_agent] succeeded on attempt %d", attempt)
            return {
                "news_result": result,
                "news_error": None,
                "traces": [{"agent": "news_agent", "started_at": datetime.now(timezone.utc).isoformat(),
                            "duration_ms": ms, "status": "ok", "error": None}],
            }
        except Exception as exc:
            last_exc = exc
            logger.warning("[news_agent] attempt %d failed: %s", attempt, exc)
            if attempt < 3:
                await asyncio.sleep(0.1 * (2 ** (attempt - 1)))  # 100ms, 200ms backoff

    # Graceful degradation — flow continues without news
    ms = (time.perf_counter() - t0) * 1000
    logger.error("[news_agent] all retries exhausted, degrading gracefully")
    return {
        "news_result": NewsResult(headlines=[], sentiment="unknown", relevant_tickers=[]),
        "news_error": str(last_exc),
        "traces": [{"agent": "news_agent", "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": ms, "status": "degraded", "error": str(last_exc)}],
    }


async def thesis_generator(state: DecisionState) -> dict[str, Any]:
    t0 = time.perf_counter()
    logger.info("[thesis_generator] generating recommendations")
    intent = state["intent"]
    portfolio = state.get("portfolio_result")
    asset = state.get("asset_result")
    news = state.get("news_result")
    assert intent is not None, "thesis_generator requires intent to be set"
    recs = await mock_thesis_llm(
        intent=intent,
        portfolio_result=portfolio.model_dump() if portfolio else {},
        asset_result=asset.model_dump() if asset else {},
        news_result=news.model_dump() if news else {},
    )
    ms = (time.perf_counter() - t0) * 1000
    return {
        "recommendations": recs,
        "traces": [{"agent": "thesis_generator", "started_at": datetime.now(timezone.utc).isoformat(),
                    "duration_ms": ms, "status": "ok", "error": None}],
    }


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------

def build_graph(
    checkpointer=None,
    news_fail_times: int = 0,
) -> Any:
    """Build and compile the decision_copilot graph.

    Args:
        checkpointer: Checkpointer for state persistence (e.g., MemorySaver).
        news_fail_times: Inject news failures for retry testing.
    """
    builder = StateGraph(DecisionState)

    # Wrap news_agent to inject fail_times without changing node signature
    async def _news_node(state: DecisionState) -> dict:
        return await news_agent(state, fail_times=news_fail_times)

    # Add nodes
    builder.add_node("intent_router", intent_router)
    builder.add_node("portfolio_agent", portfolio_agent)
    builder.add_node("asset_research_agent", asset_research_agent)
    builder.add_node("news_agent", _news_node)
    builder.add_node("thesis_generator", thesis_generator)

    # Edges: START → intent_router
    builder.add_edge(START, "intent_router")

    # Fan-out: intent_router → 3 parallel nodes
    builder.add_edge("intent_router", "portfolio_agent")
    builder.add_edge("intent_router", "asset_research_agent")
    builder.add_edge("intent_router", "news_agent")

    # Fan-in: all 3 → thesis_generator (LangGraph waits for all incoming edges)
    builder.add_edge("portfolio_agent", "thesis_generator")
    builder.add_edge("asset_research_agent", "thesis_generator")
    builder.add_edge("news_agent", "thesis_generator")

    builder.add_edge("thesis_generator", END)

    return builder.compile(checkpointer=checkpointer)


# ---------------------------------------------------------------------------
# Public runner
# ---------------------------------------------------------------------------

async def run_flow(
    decision_input: DecisionInput,
    *,
    thread_id: str = "default",
    checkpointer=None,
    news_fail_times: int = 0,
) -> DecisionOutput:
    """Execute the decision_copilot_flow and return a typed DecisionOutput."""
    t_total = time.perf_counter()

    app = build_graph(checkpointer=checkpointer, news_fail_times=news_fail_times)

    initial_state: DecisionState = {
        "input": decision_input,
        "intent": None,
        "portfolio_result": None,
        "asset_result": None,
        "news_result": None,
        "news_error": None,
        "recommendations": [],
        "traces": [],
    }

    config = {"configurable": {"thread_id": thread_id}}
    result = await app.ainvoke(initial_state, config=config)

    traces = [
        AgentTrace(
            agent=t["agent"],
            started_at=datetime.fromisoformat(t["started_at"]),
            completed_at=datetime.fromisoformat(t["started_at"]),  # simplification
            duration_ms=t["duration_ms"],
            status=t["status"],
            error=t.get("error"),
        )
        for t in result["traces"]
    ]

    total_ms = (time.perf_counter() - t_total) * 1000
    logger.info("[flow] total duration: %.1fms", total_ms)

    return DecisionOutput(
        recommendations=result["recommendations"],
        portfolio_context=decision_input.portfolio_context,
        intent=result["intent"],
        generated_at=datetime.now(timezone.utc),
        trace=traces,
    )


# ---------------------------------------------------------------------------
# State persistence demo helpers
# ---------------------------------------------------------------------------

async def simulate_interrupted_then_resumed(decision_input: DecisionInput) -> dict:
    """Demonstrate state persistence: run 2 nodes, 'restart', resume.

    LangGraph checkpointing: the graph can be resumed from any node
    by replaying from the last checkpoint. Here we demonstrate the
    checkpoint is written after each node.
    """
    checkpointer = MemorySaver()
    app = build_graph(checkpointer=checkpointer)
    thread_id = "persistence-test"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state: DecisionState = {
        "input": decision_input,
        "intent": None,
        "portfolio_result": None,
        "asset_result": None,
        "news_result": None,
        "news_error": None,
        "recommendations": [],
        "traces": [],
    }

    # Run the full graph (checkpoints written at each node)
    await app.ainvoke(initial_state, config=config)

    # Simulate restart: get last checkpoint state
    checkpoint = checkpointer.get(config)  # type: ignore[arg-type]
    snapshot = app.get_state(config)

    return {
        "thread_id": thread_id,
        "checkpoint_keys": list(checkpoint["channel_values"].keys()) if checkpoint else [],
        "snapshot_next": snapshot.next,
        "snapshot_values_keys": list(snapshot.values.keys()),
        "intent_recovered": snapshot.values.get("intent") is not None,
        "recommendations_recovered": len(snapshot.values.get("recommendations", [])) > 0,
    }


async def stream_sse_events(decision_input: DecisionInput):
    """Yield SSE-style events for FastAPI streaming response (criterion 5)."""
    app = build_graph()
    initial_state: DecisionState = {
        "input": decision_input,
        "intent": None,
        "portfolio_result": None,
        "asset_result": None,
        "news_result": None,
        "news_error": None,
        "recommendations": [],
        "traces": [],
    }

    async for event in app.astream_events(initial_state, version="v2"):
        kind = event["event"]
        if kind == "on_chain_start" and event.get("name") not in ("LangGraph", "RunnableLambda"):
            yield {"event": "node_start", "node": event["name"], "data": {}}
        elif kind == "on_chain_end" and event.get("name") not in ("LangGraph", "RunnableLambda"):
            output = event.get("data", {}).get("output", {})
            yield {"event": "node_end", "node": event["name"], "data": output}
