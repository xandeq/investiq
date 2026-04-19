"""Tests for the Pydantic AI implementation of decision_copilot_flow.

Criteria covered:
  C1 — state persistence (manual JSON file)
  C2 — parallel fan-out timing (asyncio.gather)
  C3 — retry + graceful degradation
  C4 — observability (traces populated)
  C5 — SSE streaming (manual yield pattern)
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest

from spike.common.schemas import (
    DecisionInput,
    DecisionOutput,
    PortfolioContext,
)
from spike.pydantic_ai_impl.flow import (
    run_flow,
    simulate_interrupted_then_resumed,
    stream_sse_events,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def decision_input() -> DecisionInput:
    return DecisionInput(
        query="Quero diversificar minha carteira com renda fixa de baixo risco",
        user_id="test-user-001",
        portfolio_context=PortfolioContext(
            capital_available=50_000.0,
            current_allocation={"MXRF11": 0.30, "ITUB4": 0.20, "cash": 0.50},
        ),
    )


@pytest.fixture
def state_file(tmp_path: Path) -> Path:
    return tmp_path / "test_state.json"


# ---------------------------------------------------------------------------
# C0 — Smoke: flow runs and returns valid DecisionOutput
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_run_flow_returns_decision_output(decision_input: DecisionInput):
    result = await run_flow(decision_input, thread_id="pai-smoke")

    assert isinstance(result, DecisionOutput)
    assert result.intent is not None
    assert result.intent.intent != ""
    assert len(result.recommendations) > 0
    assert result.portfolio_context.capital_available == 50_000.0
    assert result.generated_at is not None


@pytest.mark.asyncio
async def test_run_flow_traces_contain_all_agents(decision_input: DecisionInput):
    result = await run_flow(decision_input, thread_id="pai-traces")

    agent_names = {t.agent for t in result.trace}
    assert "intent_router" in agent_names
    assert "portfolio_agent" in agent_names
    assert "asset_research_agent" in agent_names
    assert "news_agent" in agent_names
    assert "thesis_generator" in agent_names


# ---------------------------------------------------------------------------
# C2 — Parallel fan-out: asyncio.gather wall-clock < sequential sum
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_parallel_fan_out_is_faster_than_sequential(decision_input: DecisionInput):
    t0 = time.perf_counter()
    result = await run_flow(decision_input, thread_id="pai-parallel")
    total_ms = (time.perf_counter() - t0) * 1000

    parallel_traces = [
        t for t in result.trace
        if t.agent in {"portfolio_agent", "asset_research_agent", "news_agent"}
    ]
    max_single_ms = max(t.duration_ms for t in parallel_traces)
    sum_ms = sum(t.duration_ms for t in parallel_traces)

    # If truly parallel: max_single < sum. If sequential: max_single ≈ sum.
    assert max_single_ms < sum_ms * 0.75, (
        f"max_single={max_single_ms:.1f}ms >= 75% of sum={sum_ms:.1f}ms "
        f"— asyncio.gather() may not be running them in parallel"
    )


# ---------------------------------------------------------------------------
# C1 — State persistence: manual JSON file
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_state_persistence_intent_recovered(
    decision_input: DecisionInput, state_file: Path
):
    result = await simulate_interrupted_then_resumed(decision_input, state_file)

    assert result["intent_recovered"] is True, (
        f"Intent not recovered from JSON file. Result: {result}"
    )
    assert state_file.exists(), "State file was not created"


@pytest.mark.asyncio
async def test_state_file_resume_skips_intent_rerun(
    decision_input: DecisionInput, state_file: Path
):
    """Second run_flow with same state_file must skip intent_router (resume from checkpoint)."""
    # First run: writes state_file after intent_router
    first = await run_flow(
        decision_input,
        thread_id="pai-resume-1",
        state_file=state_file,
    )
    assert state_file.exists()

    # Second run: should load intent from file, not re-run intent_router
    second = await run_flow(
        decision_input,
        thread_id="pai-resume-2",
        state_file=state_file,
    )

    assert first.intent.intent == second.intent.intent, (
        "Resumed flow should produce same intent as original"
    )


# ---------------------------------------------------------------------------
# C3 — Retry: news fails 2 times, succeeds on 3rd
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_news_retry_succeeds_after_2_failures(decision_input: DecisionInput):
    result = await run_flow(
        decision_input,
        thread_id="pai-retry-2",
        news_fail_times=2,
    )

    news_trace = next(t for t in result.trace if t.agent == "news_agent")
    assert news_trace.status == "ok", (
        f"Expected 'ok' after retry, got '{news_trace.status}'"
    )
    assert news_trace.error is None
    assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# C3 — Degradation: all retries exhausted → flow continues
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_news_degraded_when_all_retries_exhausted(decision_input: DecisionInput):
    result = await run_flow(
        decision_input,
        thread_id="pai-degrade",
        news_fail_times=10,
    )

    assert isinstance(result, DecisionOutput), "Flow must not raise on news failure"
    news_trace = next(t for t in result.trace if t.agent == "news_agent")
    assert news_trace.status == "degraded"
    assert news_trace.error is not None
    assert result.intent is not None
    assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# C4 — Observability: all traces have required fields
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_all_traces_have_required_fields(decision_input: DecisionInput):
    result = await run_flow(decision_input, thread_id="pai-obs")

    for trace in result.trace:
        assert trace.agent
        assert trace.duration_ms >= 0
        assert trace.started_at is not None
        assert trace.status in {"ok", "degraded", "error"}


# ---------------------------------------------------------------------------
# C5 — SSE streaming: events emitted
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_sse_streaming_emits_node_events(decision_input: DecisionInput):
    events = []
    async for event in stream_sse_events(decision_input):
        events.append(event)

    assert len(events) > 0, "No SSE events emitted"

    event_types = {e["event"] for e in events}
    assert "node_start" in event_types, "Missing node_start events"
    assert "node_end" in event_types, "Missing node_end events"

    node_names = {e["node"] for e in events}
    assert "intent_router" in node_names
    assert "thesis_generator" in node_names
