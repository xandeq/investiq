---
phase: 12-foundation-legal-cost-control-async-architecture
plan: 03
status: complete
started: "2026-03-31"
completed: "2026-03-31"
commits:
  - hash: 9e07722
    message: "feat(analysis): implement LLM provider fallback chain and DCF Celery task (12-03 Task 1)"
  - hash: 113f9d3
    message: "feat(analysis): add cache invalidation and wire Celery dispatch in router (12-03 Task 2)"
---

# Plan 12-03 Summary: Async Tasks, LLM Fallback, and Cache Invalidation

## What was done

### Task 1: LLM provider fallback chain and DCF Celery task

- **`backend/app/modules/analysis/providers.py`** — LLM fallback chain:
  - `ANALYSIS_LLM_CHAIN`: 2-provider chain (OpenRouter gpt-4o-mini -> Groq llama-3.3-70b-versatile)
  - `call_analysis_llm()`: async function with `asyncio.wait_for()` timeout per provider
  - `AIProviderError`: custom exception when all providers exhausted
  - `_get_cached_analysis_with_outdated_badge()`: fallback to stale cached analysis with warning badge
  - OpenRouter uses existing `call_llm` from `ai.provider`; Groq uses direct httpx POST

- **`backend/app/modules/analysis/tasks.py`** — Celery task (follows wizard pattern):
  - `@shared_task(name="analysis.run_dcf", bind=True, max_retries=0)`
  - `_update_job()`: superuser session DB update (same pattern as wizard/tasks.py)
  - `_check_and_increment_quota()`: monthly quota enforcement
  - `_fetch_fundamentals_stub()`: hardcoded sample data (real BRAPI in Phase 13)
  - `_calculate_dcf_stub()`: hardcoded DCF result (real calculation in Phase 13)
  - Full pipeline: quota check -> running -> LLM narrative -> build result with data versioning -> completed
  - Error handling: try/except wraps steps 3-8, sets status="failed" with error_message
  - Cost logging via `log_analysis_cost` on both success and failure paths

- **`backend/app/modules/analysis/cost.py`** — Created minimal stub (Plan 02 agent later replaced with full implementation including `estimate_llm_cost()` with pricing table)

### Task 2: Cache invalidation and router wiring

- **`backend/app/modules/analysis/invalidation.py`**:
  - `on_earnings_release(ticker, filing_date)`: marks completed analyses as "stale", clears Redis cache key `analysis:cache:{ticker}`, returns count of invalidated rows
  - `get_analyzed_tickers_recent_7d()`: returns distinct tickers with recent analyses (for Celery beat scheduling in Phase 15)

- **`backend/app/modules/analysis/router.py`** — Wired Celery dispatch:
  - Added `run_dcf.delay(job_id=..., tenant_id=..., ticker=..., assumptions=...)` after job creation in POST /analysis/dcf endpoint
  - Replaced Plan 02's placeholder comment with actual dispatch

### Tests (16 Plan 03 tests)

| Test | Status |
|------|--------|
| test_llm_fallback_fires_on_primary_failure | PASS |
| test_llm_all_providers_fail_raises_error | PASS |
| test_llm_openrouter_success_returns_immediately | PASS |
| test_chain_has_two_entries | PASS |
| test_chain_providers_are_openrouter_and_groq | PASS |
| test_async_job_lifecycle_complete | PASS |
| test_celery_task_error_handling | PASS |
| test_celery_task_unhandled_exception | PASS |
| test_run_dcf_calls_log_analysis_cost_on_success | PASS |
| test_analysis_includes_data_version_id | PASS |
| test_data_timestamp_visible_in_api | PASS |
| test_data_sources_in_result | PASS |
| test_invalidation_marks_analyses_stale | PASS |
| test_invalidation_returns_count | PASS |
| test_api_response_includes_disclaimer | PASS |
| test_disclaimer_component_renders | SKIP (frontend) |

## Test results

```
26 passed, 5 skipped (Plan 02 stubs + frontend deferred)
```

## Acceptance criteria met

- `providers.py` contains `ANALYSIS_LLM_CHAIN` with 2 entries (openrouter, groq)
- `providers.py` contains `async def call_analysis_llm(` and `class AIProviderError`
- `tasks.py` contains `@shared_task(name="analysis.run_dcf"` with bind=True, max_retries=0
- `tasks.py` contains `_update_job` and `_check_and_increment_quota` functions
- `tasks.py` contains `log_analysis_cost` calls in both success and failure paths
- `tasks.py` contains `build_data_version_id()` and `get_data_sources()` calls
- `tasks.py` imports and uses `call_analysis_llm`
- `invalidation.py` contains `async def on_earnings_release(ticker` and `def get_analyzed_tickers_recent_7d`
- `invalidation.py` updates status to "stale" and deletes Redis cache `analysis:cache:{ticker}`
- `router.py` contains `run_dcf.delay(` call after job creation
- All async/task/fallback/invalidation tests pass
