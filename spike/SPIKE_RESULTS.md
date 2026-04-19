# ADR-002 Spike: LangGraph vs Pydantic AI

**Spike branch**: `spike/adr-002`
**Conducted**: 2026-04-19
**Use case**: `decision_copilot_flow` — intent routing → parallel research fan-out → thesis generation
**Code**: `spike/langgraph_impl/flow.py`, `spike/pydantic_ai_impl/flow.py`
**Tests**: 8 LangGraph tests + 9 Pydantic AI tests → **17/17 green**

---

## 1. Executive Summary

| | LangGraph | Pydantic AI |
|---|---|---|
| **Fan-out/fan-in parallelism** | Idiomatic — `add_edge()` × 3 | Manual — `asyncio.gather()` |
| **State persistence** | Built-in `MemorySaver` / `SqliteSaver` (~5 lines) | Manual JSON serialize/deserialize (~15 lines, **intrusive**) |
| **Retry logic** | Manual (same as PAI) | Manual (same as LG) |
| **SSE streaming** | `astream_events(version="v2")` — natural | Manual `yield` pattern — **limitation**: `gather()` blocks until all parallel branches complete |
| **Type safety** | `TypedDict` state — partial (dict access) | `FlowDeps` dataclass + `Agent[D,O]` — strong |
| **Dependency footprint** | **9,089 KB** (LG + langchain-core + langsmith) | **4,487 KB** (PAI + pydantic + httpx) |
| **FastAPI integration** | Via `astream_events` → `StreamingResponse` | Via `async for` + manual yield → `StreamingResponse` |

**Recommendation: LangGraph** for `decision_copilot_flow` and production agentic workflows.

Rationale: the built-in checkpointer (MemorySaver → PostgresSaver) is the decisive differentiator for multi-step flows where users may resume sessions. Pydantic AI requires invasive custom persistence code at every checkpoint boundary — adding 15+ lines of boilerplate per resumable step. LangGraph's streaming via `astream_events` also emits per-node events naturally from parallel branches, whereas Pydantic AI's `asyncio.gather()` blocks until all parallel nodes finish before any event fires.

---

## 2. Criteria Scores (0–10, weight × score → weighted)

| # | Criterion | Weight | LangGraph | PAI | LG Weighted | PAI Weighted |
|---|-----------|--------|-----------|-----|-------------|--------------|
| C1 | State persistence / resumability | 15% | **9** | 4 | 1.35 | 0.60 |
| C2 | Parallel execution ergonomics | 15% | **9** | 7 | 1.35 | 1.05 |
| C3 | Retry + error handling | 10% | 7 | 7 | 0.70 | 0.70 |
| C4 | Observability / tracing | 10% | 7 | **8** | 0.70 | 0.80 |
| C5 | FastAPI SSE streaming | 10% | **9** | 6 | 0.90 | 0.60 |
| C6 | Type safety | 10% | 6 | **8** | 0.60 | 0.80 |
| C7 | Testability | 8% | **8** | 7 | 0.64 | 0.56 |
| C8 | Dependency footprint | 7% | 4 | **8** | 0.28 | 0.56 |
| C9 | Ecosystem maturity | 7% | **9** | 6 | 0.63 | 0.42 |
| C10 | Learning curve | 5% | 6 | **8** | 0.30 | 0.40 |
| C11 | Long-term maintenance | 3% | **8** | 6 | 0.24 | 0.18 |
| | **TOTAL** | 100% | | | **7.69** | **6.67** |

**Winner: LangGraph (7.69 vs 6.67)**

---

## 3. Evidence per Criterion

### C1 — State Persistence / Resumability (weight: 15%)

**LangGraph score: 9**

Built-in `MemorySaver` requires ~5 lines. Replace with `SqliteSaver` or `AsyncPostgresSaver` for production durable persistence — no application-level code changes needed.

```python
# LangGraph: 5 lines, zero intrusiveness
checkpointer = MemorySaver()
app = build_graph(checkpointer=checkpointer)
await app.ainvoke(state, config={"configurable": {"thread_id": "user-123"}})
# Resume: invoke again with same thread_id — LangGraph replays from last checkpoint
```

Test `test_state_persistence_checkpoint_written` verified `intent_recovered=True` and `recommendations_recovered=True` from checkpoint.

**Pydantic AI score: 4**

No built-in checkpointer. Every resumable boundary requires:
1. `state_file.write_text(json.dumps({...}))` — after each step
2. `if state_file and state_file.exists(): ... = Model(**saved["key"])` — at start of each step
3. Custom storage adapter (Redis, DB, file) — entirely user responsibility

`simulate_interrupted_then_resumed()` returned: `intrusiveness: "HIGH — must add save/load at every checkpoint boundary"`, `extra_code_lines: "~15 lines to serialize/deserialize"`.

Test `test_state_file_resume_skips_intent_rerun` and `test_state_persistence_intent_recovered` both passed.

---

### C2 — Parallel Execution Ergonomics (weight: 15%)

**LangGraph score: 9**

Fan-out/fan-in is a first-class graph primitive. Adding a parallel branch = one `add_edge()` call. LangGraph auto-joins when all incoming edges to `thesis_generator` resolve — no `gather()`, no `Task`, no explicit barrier.

```python
# LangGraph fan-out: 3 lines
builder.add_edge("intent_router", "portfolio_agent")
builder.add_edge("intent_router", "asset_research_agent")
builder.add_edge("intent_router", "news_agent")
# Fan-in is implicit: all 3 → thesis_generator
```

**Measured parallelism (LangGraph)**:
- portfolio: 100ms, asset: 150ms, news: 307ms
- sum = 558ms, max = 307ms → ratio max/sum = 55% < 75% threshold ✓

**Pydantic AI score: 7**

`asyncio.gather()` works and is Pythonic. However it's manual — developer must explicitly choose what to gather, wrap sync functions in `run_in_executor`, and handle the result tuple unpacking.

```python
# Pydantic AI: explicit gather
(portfolio_result, p_ms), (asset_result, a_ms), (news_result, n_ms, news_err) = (
    await asyncio.gather(
        _run_portfolio(deps),
        _run_asset_research(deps, intent),
        _run_news_with_retry(deps),
    )
)
```

**Measured parallelism (Pydantic AI)**:
- portfolio: 100ms, asset: 150ms, news: 324ms
- sum = 575ms, max = 324ms → ratio 56% < 75% ✓

Both implementations achieve genuine parallelism. LangGraph wins on ergonomics for maintainability as flows grow.

---

### C3 — Retry + Error Handling (weight: 10%)

**Both score: 7** — identical implementation required in both.

Neither framework provides built-in retry. Both use the same manual pattern:
```python
for attempt in range(1, max_retries + 1):
    try:
        result = await call()
        return result, ..., None
    except Exception as exc:
        if attempt < max_retries:
            await asyncio.sleep(0.1 * (2 ** (attempt - 1)))
# Graceful degradation
return NewsResult(headlines=[], ...), ..., str(last_exc)
```

Tests verified:
- `fail_times=2` → status `ok` (succeeds on 3rd attempt) ✓
- `fail_times=10` → status `degraded`, flow completes without raising ✓

---

### C4 — Observability / Tracing (weight: 10%)

**LangGraph score: 7**

LangGraph has LangSmith integration (managed trace platform). For self-hosted tracing, `astream_events` provides node-level events. The `DecisionState["traces"]` accumulator pattern (Annotated list reducer) works but requires knowing LangGraph's fan-in reducer mechanism.

**Pydantic AI score: 8**

`FlowDeps` + explicit `_trace()` call after each step gives cleaner control. Traces are a first-class part of the `DecisionOutput` return type. No hidden framework magic — straightforward to audit.

Test `test_all_traces_have_required_fields` passed for both: all 5 agents present, durations ≥ 0, valid status values.

---

### C5 — FastAPI SSE Streaming (weight: 10%)

**LangGraph score: 9**

`app.astream_events(initial_state, version="v2")` emits `on_chain_start` / `on_chain_end` events per node as they complete — **including from parallel branches individually**. FastAPI integration:

```python
async def stream():
    async for event in app.astream_events(state, version="v2"):
        if event["event"] == "on_chain_end":
            yield f"data: {json.dumps(event['data'])}\n\n"

return StreamingResponse(stream(), media_type="text/event-stream")
```

**Pydantic AI score: 6**

Manual `async for event in stream_sse_events(...)` with `yield` works. Critical limitation: `asyncio.gather()` blocks until **all** parallel branches complete before any event fires. Users see nothing during the parallel phase, then get 3 events at once. Workaround requires replacing gather with `asyncio.create_task()` + per-task queue — significant complexity.

---

### C6 — Type Safety (weight: 10%)

**LangGraph score: 6**

`TypedDict` state provides IDE hints but `state["field"]` access is untyped at runtime. Mypy/Pyright catches missing keys in some cases but not all (especially with `state.get()`). Node return type is `dict[str, Any]` — no enforcement that returned keys match state fields.

**Pydantic AI score: 8**

`Agent[FlowDeps, OutputType]` is fully generic. `RunContext[FlowDeps]` gives typed access to deps. `FlowDeps` is a dataclass — all fields typed. Output types (`IntentResult`, `PortfolioResult`, etc.) are validated by Pydantic at run time. The tradeoff: Pydantic v2 models required (v1 compat layer breaks `Agent` schema generation — discovered and fixed during spike).

---

### C7 — Testability (weight: 8%)

**LangGraph score: 8**

Graph is easy to test:
- `build_graph(checkpointer=None)` factory makes it easy to inject checkpointers
- `news_fail_times` parameter enables fault injection at graph level
- `MemorySaver` in tests — no external deps

`asyncio.get_event_loop()` deprecation warning may appear in test runs (Python 3.12 prefers `asyncio.to_thread()`).

**Pydantic AI score: 7**

`FlowDeps` is a plain dataclass — trivially mockable. However, `Agent` instances with `TestModel()` are module-level globals, which can cause state leakage between tests if `_news_fail_count` dict isn't reset. `call_key` parameter was added to isolate counters per test run.

---

### C8 — Dependency Footprint (weight: 7%)

**LangGraph**: 9,089 KB total (LangGraph 1,444 KB + langchain-core 4,439 KB + langsmith 3,206 KB)
**Pydantic AI**: 4,487 KB total (pydantic-ai 123 KB + pydantic 3,637 KB + httpx 726 KB)

Pydantic AI is ~50% smaller. However, if the project already uses LangChain ecosystem (e.g., vector stores, loaders), langchain-core is already a transitive dep — cost drops to ~1,444 KB marginal.

---

### C9 — Ecosystem Maturity (weight: 7%)

**LangGraph (v1.1.2)**: Backed by LangChain Inc. Strong enterprise adoption. LangSmith observability platform. PostgresSaver available for durable production persistence. Active changelog, issues tracked openly.

**Pydantic AI (v1.84.1)**: Created by Samuel Colvin (pydantic author). Growing but younger ecosystem. No built-in cloud observability. No built-in durable persistence. Logfire integration available for tracing.

---

### C10 — Learning Curve (weight: 5%)

**LangGraph**: Concepts to learn — `StateGraph`, `TypedDict` state, edge types, fan-in reducers (`Annotated` list), checkpointer API. Roughly 2–4h to be productive.

**Pydantic AI**: Concepts are plain Python + `Agent[D,O]` + `RunContext`. Roughly 1–2h to be productive. The `TestModel()` pattern is idiomatic for testing without LLM calls.

---

### C11 — Long-term Maintenance (weight: 3%)

**LangGraph**: Explicit graph topology makes the flow's shape self-documenting. Adding a new parallel branch = 3 lines (`add_node` + 2 `add_edge`). Breaking changes in LangGraph tend to be scoped to the graph API, not LLM interaction.

**Pydantic AI**: Adding a new parallel branch requires editing `asyncio.gather()` call + result tuple + `_trace()` call — ~6 lines scattered through `run_flow()`. Persistence boundaries must be audited manually when flow topology changes.

---

## 4. Wall-Clock Benchmarks

Measured on the spike use case (all mocks, no real LLM):

| Phase | LangGraph | Pydantic AI |
|-------|-----------|-------------|
| intent_router | 508ms | 510ms |
| portfolio_agent (parallel) | 101ms | 101ms |
| asset_research_agent (parallel) | 151ms | 151ms |
| news_agent (parallel) | 307ms | 324ms |
| thesis_generator | 510ms | 508ms |
| **Total flow** | **1,338ms** | **1,342ms** |

Both implementations are within measurement noise of each other. Framework overhead is negligible (~4ms difference).

---

## 5. Decision

**Use LangGraph** for `decision_copilot_flow` in production.

Primary driver: **C1 (state persistence)**. The advisor flow will need session resumability — users submit a query, get disconnected, and expect results to be available on reconnect. LangGraph's `AsyncPostgresSaver` provides this with zero application-layer code change, while Pydantic AI would require persistent custom serialization code at every step boundary.

Secondary driver: **C5 (SSE streaming)**. LangGraph's `astream_events` fires events as individual parallel nodes complete, giving users real-time feedback during the research phase. Pydantic AI's `asyncio.gather()` pattern blocks until all parallel branches complete before emitting.

Pydantic AI is the better choice if: (a) the flow is simple enough that state persistence is not needed, (b) strong type safety is the primary concern, (c) dependency footprint is constrained, or (d) the team is more familiar with plain async Python than graph APIs.

---

## 6. Files

```
spike/
  common/
    schemas.py          # Shared Pydantic v2 models
    llm_mock.py         # mock_intent_llm, mock_thesis_llm
    mocks.py            # portfolio_agent_sync, asset_research_agent_sync, news_agent_async
  langgraph_impl/
    flow.py             # 340 lines — DecisionState, build_graph, run_flow, stream_sse_events
    test_flow.py        # 8 tests — C0–C5 coverage
  pydantic_ai_impl/
    flow.py             # 361 lines — FlowDeps, 5 Agents, run_flow, stream_sse_events
    test_flow.py        # 9 tests — C0–C5 coverage
  SPIKE_RESULTS.md      # This file
```

**Test results**: `pytest spike/ -v` → **17 passed** in ~25s
