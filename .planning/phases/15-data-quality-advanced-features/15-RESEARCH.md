# Phase 15: Data Quality & Advanced Features — Research

**Researched:** 2026-04-03
**Domain:** Cache invalidation, data quality auditing, analysis history, performance load testing
**Confidence:** HIGH (codebase read directly; patterns verified from existing phases)

---

## Summary

Phase 15 operationalizes data robustness for the analysis engine built in Phases 12–14. The
foundation (`invalidation.py`, `models.py`, `data.py`) was partially scaffolded in Phase 12
with explicit notes that Beat integration was deferred here. This phase wires it all together:
a Celery Beat task polls for new earnings filings, invalidates stale Redis cache, marks
completed jobs as `stale`, adds analysis history retrieval and version diffing, and validates
performance under load.

**BRAPI has no earnings calendar endpoint** (confirmed from docs). The canonical approach is
a scheduled Celery Beat task that polls each recently-analyzed ticker's `incomeStatementHistoryQuarterly`
module, compares the most-recent filing date against the `data_timestamp` stored in the last
completed `AnalysisJob`, and calls `on_earnings_release()` when a newer filing is detected.
This matches the STATE.md guidance: "Pilot invalidation with 10 tickers; verify triggers."

The `AnalysisJob` table already stores `result_json`, `completed_at`, `data_timestamp`, and
`data_version_id`. Analysis history and version diffing are purely additive: a new
`GET /analysis/history/{ticker}` endpoint queries past completed jobs, and a diff function
compares `fair_value` (or relevant metric) between consecutive completed jobs to surface
"Fair value changed +15% due to EPS revision."

The Celery worker runs at `--concurrency=4` (docker-compose). For 500 concurrent analysis
requests, horizontal scaling means adding a second `celery-worker` container (or increasing
`--concurrency`). The load test uses Locust (`locustfile.py`) invoked headlessly — it does
NOT need to be inside pytest since the success criterion is a manual validation pass, not a
CI gate.

**Primary recommendation:** Wire the existing `on_earnings_release()` + `get_analyzed_tickers_recent_7d()`
into a Celery Beat task scheduled nightly. Add history endpoint + diff function. Scale worker
concurrency. Run Locust load test once to validate p95 < 30s.

---

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| Celery | 5.x (existing) | Beat scheduler + worker tasks | Already configured |
| Redis | 7-alpine (existing) | Cache + Celery broker/backend | Already running |
| SQLAlchemy (sync) | 2.x (existing) | DB writes in Celery tasks | `db_sync.py` pattern |
| FastAPI | 0.11x (existing) | New history endpoint | Already in use |
| pytest + pytest-asyncio | existing | Unit/integration tests | 257 tests passing |

### New for Phase 15
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| locust | ~2.x | Load testing (headless) | One-time performance validation |
| requests | existing | Already in project (BRAPI calls) | Earnings poll uses same HTTP client |

**Installation (only locust is new):**
```bash
pip install locust
```

Verify current version:
```bash
npm view locust version   # N/A — use pip
pip index versions locust
```

---

## Architecture Patterns

### Recommended Module Structure (additions to existing `analysis/`)
```
backend/app/modules/analysis/
├── invalidation.py          # EXISTS — on_earnings_release(), get_analyzed_tickers_recent_7d()
├── history.py               # NEW — get_analysis_history(), compute_analysis_diff()
├── tasks.py                 # EXTEND — add check_earnings_releases Celery task
├── router.py                # EXTEND — add GET /analysis/history/{ticker}
│
backend/tests/
├── test_phase15_cache.py    # NEW — invalidation Beat task, stale marking, Redis clear
├── test_phase15_history.py  # NEW — history endpoint, diff computation
├── test_phase15_perf.py     # NEW — smoke: job throughput, quota deduction on refresh
│
tests/locustfile.py          # NEW — 500-user load test script (separate from pytest)
```

### Pattern 1: Earnings Poll via Celery Beat (AI-13)

**What:** A `check_earnings_releases` Celery task runs nightly via Beat. It fetches the list
of recently-analyzed tickers, polls BRAPI for their most recent quarterly income statement
date, and calls `on_earnings_release()` if the filing is newer than the stored `data_timestamp`.

**When to use:** BRAPI has no push webhook for earnings — polling is the only option.
Nightly is sufficient because B3 filings (ITR/DFP) are not intraday events.

**Cache key pattern in data.py:**
```python
# Source: D:/claude-code/investiq/backend/app/modules/analysis/data.py line 88
cache_key = f"brapi:fundamentals:{ticker.upper()}"
```

**Cache key pattern in invalidation.py (current — incomplete):**
```python
# Source: D:/claude-code/investiq/backend/app/modules/analysis/invalidation.py line 68
cache_key = f"analysis:cache:{ticker}"  # BUG: wrong key prefix
```

**CRITICAL PITFALL — cache key mismatch:** `data.py` stores with key
`brapi:fundamentals:{TICKER}` but `invalidation.py` deletes `analysis:cache:{ticker}`. They do
not match. The fix in `on_earnings_release()` must delete the correct key:
```python
cache_key = f"brapi:fundamentals:{ticker.upper()}"
r.delete(cache_key)
```
This is a confirmed bug in the existing code (Phase 12 scaffolding).

**BRAPI earnings detection approach:**
```python
# Poll incomeStatementHistoryQuarterly for most recent end_date
params = {
    "modules": "incomeStatementHistoryQuarterly",
    "fundamental": "true",
}
url = f"{_BRAPI_BASE_URL}/quote/{ticker.upper()}"
# Compare result[0]["incomeStatementHistoryQuarterly"][0]["endDate"]
# against the analysis job's data_timestamp
```

**Beat schedule addition to celery_app.py:**
```python
"check-earnings-releases-nightly": {
    "task": "analysis.check_earnings_releases",
    "schedule": crontab(minute=0, hour=22, day_of_week="1-5"),  # 22h BRT Mon-Fri
    "args": [],
},
```

### Pattern 2: Analysis History + Version Diff (Success Criterion 4)

**What:** A new `history.py` module exposes two functions:
1. `get_analysis_history(ticker, tenant_id, analysis_type, limit=10)` — queries past
   completed `AnalysisJob` rows ordered by `completed_at desc`
2. `compute_analysis_diff(old_result: dict, new_result: dict, analysis_type: str)` — compares
   key metrics between two result dicts and returns a human-readable diff

**Version diff shape:**
```python
# Proposed return from compute_analysis_diff for DCF
{
    "changed_fields": [
        {
            "field": "fair_value",
            "old_value": 42.50,
            "new_value": 48.88,
            "pct_change": 15.0,
            "label": "Fair value changed +15.0%",
        }
    ],
    "summary": "Fair value changed +15% due to EPS revision",
}
```

**New endpoint:**
```
GET /analysis/history/{ticker}?analysis_type=dcf&limit=10
```
Returns list of `AnalysisJob` results (status=completed, for the authenticated tenant).

**Quota handling for Refresh:** A refresh is a new analysis submission — the existing
`POST /analysis/dcf` endpoint is called again. No special refresh endpoint needed. The
`_check_and_increment_quota()` in tasks.py already deducts 1 quota point per submission.
The old completed job remains in DB (archive via `status=stale` after re-run completes).

**Archiving pattern:** When a new analysis for the same (tenant, ticker, type) completes
successfully, mark all previous completed jobs for that (tenant, ticker, type) as `stale`.
This preserves history while clearly marking the current one.

### Pattern 3: Data Completeness Flags (AI-10)

**What:** `fetch_fundamentals()` already returns `data_completeness` with `available`,
`missing`, and `completeness` percentage. The sector comparison already returns
`peers_with_data / peers_attempted`. Phase 15 adds a green/yellow/red traffic-light flag
computed from these values.

**Thresholds (proposed):**
| Color | Condition |
|-------|-----------|
| green | completeness >= 80% |
| yellow | 50% <= completeness < 80% |
| red | completeness < 50% |

These are returned as a new `completeness_flag` field in every analysis result. The planner
should add this as a computed field in the result builder (tasks.py) and/or in a new
`completeness.py` helper.

**Peer audit approach:** Manual verification of 50 sample tickers is accomplished by a
Python script (not a test) that: fetches fundamentals for 50 B3 large-caps, calls
`calculate_sector_comparison()`, and prints a completeness report. This is a one-time
operational task documented as a Wave 0 pre-work item.

### Pattern 4: Load Test (Success Criterion 3)

**Tool:** Locust (headless mode). NOT inside pytest — run as a separate CLI command.

**Locust file pattern:**
```python
# tests/locustfile.py
from locust import HttpUser, task, between

class AnalysisUser(HttpUser):
    wait_time = between(0.02, 0.1)  # ~10-50 requests/sec per user

    @task
    def request_dcf(self):
        self.client.post(
            "/analysis/dcf",
            json={"ticker": "PETR4"},
            headers={"Authorization": f"Bearer {JWT_TOKEN}"},
        )
```

**Run command:**
```bash
locust -f tests/locustfile.py \
  --host http://localhost:8000 \
  --users 500 \
  --spawn-rate 50 \
  --run-time 10s \
  --headless \
  --html tests/locust-report.html
```

**Celery concurrency for load:** Current `--concurrency=4` handles ~4 parallel jobs. For
500 concurrent *requests* (which queue immediately and return job IDs), the FastAPI layer
handles the queueing. The bottleneck is worker throughput. Scale workers via:
```yaml
# docker-compose.override.yml or prod override
celery-worker:
  command: celery -A app.celery_app worker --loglevel=info --concurrency=8
  deploy:
    replicas: 2  # horizontal scaling in production
```

**p95 < 30s interpretation:** The 500-request load test measures *API response latency* for
the initial POST (returns job_id in < 1s, not 30s). The 30s target is for *job completion*
latency measured separately by polling GET /analysis/{job_id} until status=completed.
The load test plan must distinguish between: (a) API submission latency (should be < 2s),
and (b) job completion latency (p95 < 30s).

### Anti-Patterns to Avoid

- **Wrong cache key in invalidation:** `on_earnings_release()` currently deletes
  `analysis:cache:{ticker}` but data is stored under `brapi:fundamentals:{TICKER}`. Fix
  the key before any invalidation logic is relied upon.
- **Polling BRAPI for all tickers:** `get_analyzed_tickers_recent_7d()` limits the set.
  Never poll all B3 stocks — that would exhaust the 15k/month BRAPI free tier immediately.
- **Running Locust inside pytest:** Locust is a separate process tool. Embedding it in pytest
  creates flaky async test failures. Keep it as a standalone script in `tests/`.
- **Using asyncio inside on_earnings_release:** The function uses `get_superuser_sync_db_session()`
  (sync). The Beat task runs in a Celery worker (sync context). Never add `asyncio.run()` here.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Earnings event detection | Custom B3/CVM scraper | BRAPI `incomeStatementHistoryQuarterly` polling | Already used; no new dependency |
| Load testing | Custom HTTP loop in pytest | Locust (headless) | Handles concurrency, timing, reporting |
| Cache key management | Custom cache abstraction | Direct Redis `setex`/`delete` (existing pattern) | Already established in data.py |
| History diff computation | Third-party diff library | Simple dict comparison (custom, ~30 lines) | Results are flat dicts, trivial to diff |
| Worker scaling | Custom queue manager | Docker Compose `replicas` + `--concurrency` | Already in docker-compose |

---

## What's Already Built (Critical for Planning)

| Component | File | Status | Notes |
|-----------|------|--------|-------|
| Cache write (24h TTL) | `data.py` L254-259 | Done | Key: `brapi:fundamentals:{TICKER}` |
| Cache read (hit check) | `data.py` L90-99 | Done | Returns cached JSON |
| `on_earnings_release()` | `invalidation.py` L34-77 | Done (broken) | Deletes wrong cache key; marks stale |
| `get_analyzed_tickers_recent_7d()` | `invalidation.py` L80-97 | Done | Returns tickers with recent analyses |
| `AnalysisJob.status` enum | `models.py` L52 | Done | includes `stale` status |
| Redis sync client helper | `data.py` L41-48, `invalidation.py` L24-31 | Done | Same pattern, two copies (de-dup opportunity) |
| Celery Beat scheduler | `celery_app.py` L60-108 | Done | No earnings check task yet — must add |
| Data completeness dict | `data.py` L196-218 | Done | Has `available`, `missing`, `completeness` pct |
| Peer data completeness | `sector.py` L146-153 | Done | `peers_with_data`, `peers_without_data`, `missing_tickers` |
| Analysis quota deduction | `tasks.py` L89-128 | Done | Deducts on every new job |
| `result_json` stored | `tasks.py` L312-313 | Done | All 4 analysis types |
| `completed_at` stored | `tasks.py` (via `_update_job`) L77 | Done | Set on status=completed |

**What is NOT built yet:**

| Component | Needed For |
|-----------|------------|
| Beat task: `check_earnings_releases` | AI-13 (cache invalidation trigger) |
| Fix: `on_earnings_release()` cache key bug | AI-13 |
| `completeness_flag` (green/yellow/red) | AI-10 |
| `history.py` module | Success criterion 4 |
| `GET /analysis/history/{ticker}` endpoint | Success criterion 4 |
| `compute_analysis_diff()` function | Success criterion 4 |
| Archive-old-jobs-on-refresh logic | Success criterion 5 |
| Locust `locustfile.py` | Success criterion 3 |
| `test_phase15_*.py` test files | All criteria |

---

## Common Pitfalls

### Pitfall 1: Cache Key Mismatch (Confirmed Bug)

**What goes wrong:** `on_earnings_release()` calls `r.delete(f"analysis:cache:{ticker}")`
but `fetch_fundamentals()` stores data under `r.setex(f"brapi:fundamentals:{ticker.upper()}", ...)`.
The Redis delete is a no-op — the stale fundamentals cache is never actually cleared.

**Why it happens:** Phase 12 scaffolded the function with a placeholder key; Phase 15 is
where this gets wired for real.

**How to avoid:** Fix the cache key in `on_earnings_release()` to match `data.py`.
Also add a test that: (1) calls `fetch_fundamentals()` to populate the cache, (2) calls
`on_earnings_release()`, (3) verifies the Redis key no longer exists.

### Pitfall 2: BRAPI Rate Exhaustion from Nightly Earnings Poll

**What goes wrong:** If the recent-tickers list grows unboundedly, the nightly Beat task
could exhaust the 15k/month BRAPI quota (currently ~480 req/day for quote refresh).

**Why it happens:** `get_analyzed_tickers_recent_7d()` returns ALL recently-analyzed tickers.
At scale, this could be hundreds.

**How to avoid:** Cap the poll list to top-N most recently analyzed (e.g., 50 tickers max).
Each poll call fetches only the `incomeStatementHistoryQuarterly` module (single field) — far
lighter than the full fundamentals fetch.

### Pitfall 3: asyncio in Celery Beat Task

**What goes wrong:** Beat tasks run in Celery's sync context. Using `asyncio.run()` inside
a Beat task can cause event loop conflicts if another coroutine is already running.

**Why it happens:** The `on_earnings_release()` function signature has `async def` (confirmed
in `invalidation.py` L34) but is called from a sync Celery task context.

**How to avoid:** The Beat task (`check_earnings_releases`) must be `@shared_task` (sync).
Inside it, call the sync DB operations directly. Remove the `async def` from
`on_earnings_release()` or add `asyncio.run()` only if no event loop is active. Simpler:
rewrite `on_earnings_release()` as a sync function — it only uses sync Redis and sync SQLAlchemy.

### Pitfall 4: Analysis History Leaks Across Tenants

**What goes wrong:** `GET /analysis/history/{ticker}` without tenant scoping would return
other tenants' analyses.

**Why it happens:** AnalysisJob is tenant-scoped but the query must explicitly filter
`AnalysisJob.tenant_id == tenant_id`.

**How to avoid:** Always add `.where(AnalysisJob.tenant_id == tenant_id)` to history queries,
same as the existing `get_analysis_result()` pattern in router.py L502-510.

### Pitfall 5: Locust JWT Token Hardcoded

**What goes wrong:** Locust load test requires a valid JWT to hit authenticated endpoints.
Hardcoding a token means it expires and the test silently fails.

**Why it happens:** Load tests are often set up once and forgotten.

**How to avoid:** Add a `on_start()` in the Locust user class that calls
`POST /auth/login` to obtain a fresh JWT before making analysis requests.

---

## Code Examples

### Fix on_earnings_release() cache key bug

```python
# Source: D:/claude-code/investiq/backend/app/modules/analysis/invalidation.py
# Current (wrong):
cache_key = f"analysis:cache:{ticker}"

# Correct (matches data.py line 88):
cache_key = f"brapi:fundamentals:{ticker.upper()}"
```

### New Celery Beat Task: check_earnings_releases

```python
# In app/modules/analysis/tasks.py
@shared_task(name="analysis.check_earnings_releases", bind=False)
def check_earnings_releases() -> dict:
    """Nightly task: detect new earnings filings and invalidate stale analyses.

    1. Get recently-analyzed tickers (last 7 days)
    2. For each ticker, fetch incomeStatementHistoryQuarterly from BRAPI
    3. If most-recent filing is newer than the analysis data_timestamp, invalidate
    """
    from app.modules.analysis.invalidation import (
        get_analyzed_tickers_recent_7d,
        on_earnings_release,
        get_last_analysis_data_timestamp,
    )

    tickers = get_analyzed_tickers_recent_7d()[:50]  # cap at 50
    invalidated = 0

    for ticker in tickers:
        brapi_date = _fetch_latest_quarterly_filing_date(ticker)
        if brapi_date is None:
            continue
        last_analysis_ts = get_last_analysis_data_timestamp(ticker)
        if last_analysis_ts and brapi_date > last_analysis_ts:
            count = on_earnings_release(ticker, brapi_date)
            invalidated += count

    logger.info("check_earnings_releases: %d analyses invalidated for %d tickers",
                invalidated, len(tickers))
    return {"tickers_checked": len(tickers), "analyses_invalidated": invalidated}
```

### Analysis Diff Computation

```python
# New: app/modules/analysis/history.py
def compute_analysis_diff(old_result: dict, new_result: dict, analysis_type: str) -> dict:
    """Compute human-readable diff between two analysis results."""
    METRIC_LABELS = {
        "dcf": {"fair_value": "Fair value"},
        "earnings": {"eps_cagr_5y": "EPS CAGR 5Y"},
        "dividend": {"current_yield": "Dividend yield", "payout_ratio": "Payout ratio"},
        "sector": {"peers_found": "Peers found"},
    }

    changed = []
    for field, label in METRIC_LABELS.get(analysis_type, {}).items():
        old_val = old_result.get(field)
        new_val = new_result.get(field)
        if old_val is not None and new_val is not None and old_val != 0:
            pct = round(((new_val - old_val) / abs(old_val)) * 100, 1)
            if abs(pct) >= 1.0:  # only surface changes >= 1%
                sign = "+" if pct > 0 else ""
                changed.append({
                    "field": field,
                    "old_value": old_val,
                    "new_value": new_val,
                    "pct_change": pct,
                    "label": f"{label} changed {sign}{pct}%",
                })

    summary = "; ".join(c["label"] for c in changed) if changed else "No significant changes"
    return {"changed_fields": changed, "summary": summary}
```

### Completeness Flag Helper

```python
# New: app/modules/analysis/completeness.py (or inline in tasks.py)
def get_completeness_flag(completeness_dict: dict) -> str:
    """Return green/yellow/red flag based on data completeness percentage."""
    pct_str = completeness_dict.get("completeness", "0%")
    pct = int(pct_str.rstrip("%"))
    if pct >= 80:
        return "green"
    elif pct >= 50:
        return "yellow"
    return "red"
```

---

## Validation Architecture

**nyquist_validation: true** — Include test architecture.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `backend/pytest.ini` (exists) |
| Quick run command | `cd backend && python -m pytest tests/test_phase15_cache.py tests/test_phase15_history.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-13 | Earnings release detected, cache invalidated within check cycle | unit | `pytest tests/test_phase15_cache.py::TestEarningsPollTask -x` | Wave 0 |
| AI-13 | `on_earnings_release()` marks jobs stale + deletes correct Redis key | unit | `pytest tests/test_phase15_cache.py::TestOnEarningsRelease -x` | Wave 0 |
| AI-13 | Refresh button triggers new job + deducts 1 quota point | unit | `pytest tests/test_phase15_cache.py::TestRefreshQuota -x` | Wave 0 |
| AI-13 | Old analysis archived (stale) after refresh completes | unit | `pytest tests/test_phase15_cache.py::TestArchiveOnRefresh -x` | Wave 0 |
| AI-10 | Completeness flag green/yellow/red computed correctly | unit | `pytest tests/test_phase15_history.py::TestCompletenessFlag -x` | Wave 0 |
| AI-10 | History endpoint returns past analyses for tenant | unit | `pytest tests/test_phase15_history.py::TestHistoryEndpoint -x` | Wave 0 |
| AI-10 | History endpoint does NOT return other tenants' analyses | unit | `pytest tests/test_phase15_history.py::TestHistoryTenantIsolation -x` | Wave 0 |
| SC-4 | compute_analysis_diff returns correct pct_change for DCF fair_value | unit | `pytest tests/test_phase15_history.py::TestAnalysisDiff -x` | Wave 0 |
| SC-3 | Performance smoke: 10 concurrent DCF requests all return 202 (not timeout) | unit | `pytest tests/test_phase15_perf.py::TestConcurrentJobSubmission -x` | Wave 0 |

Note: Full 500-user Locust load test (Success Criterion 3) is a manual validation step,
not part of the automated pytest suite.

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_phase15_cache.py tests/test_phase15_history.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -q`
- **Phase gate:** Full suite green (257 existing + new Phase 15 tests) before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_phase15_cache.py` — covers AI-13 cache invalidation + stale marking + refresh quota
- [ ] `tests/test_phase15_history.py` — covers AI-10 completeness flags + history endpoint + tenant isolation + diff
- [ ] `tests/test_phase15_perf.py` — covers performance smoke test (10 concurrent submissions)
- [ ] `tests/locustfile.py` — 500-user load test script (manual validation, not in CI)

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Polling all tickers for earnings | Poll only recently-analyzed tickers | Phase 15 | Prevents BRAPI quota exhaustion |
| Overwrite analysis on refresh | Archive old + create new (status=stale) | Phase 15 | Enables history retrieval |
| No completeness flags | green/yellow/red based on field coverage | Phase 15 | Satisfies AI-10 |

**Deprecated/outdated:**

- The `async def on_earnings_release()` signature is a mismatch with its sync internals.
  Phase 15 should convert it to `def on_earnings_release()` (remove async) for clean
  Celery task invocation.

---

## Open Questions

1. **BRAPI earnings detection reliability**
   - What we know: `incomeStatementHistoryQuarterly` returns the most recent quarterly
     filing date. B3 companies file ITR (quarterly) and DFP (annual).
   - What's unclear: Does BRAPI update `incomeStatementHistoryQuarterly` the same day
     as the CVM filing, or with 1-2 day lag?
   - Recommendation: STATE.md explicitly flags this as "pilot with 10 tickers; verify
     triggers." Phase 15 should include a piloting step as part of Wave 1 before
     wiring the Beat schedule in production.

2. **Analysis history scope — per tenant vs cross-tenant**
   - What we know: All AnalysisJob rows are tenant-scoped.
   - What's unclear: Should the history endpoint show all analyses by this tenant for
     this ticker (including analyses by other users of the same tenant), or only the
     authenticated user's own analyses?
   - Recommendation: Show all analyses for the tenant+ticker combination (tenant-scoped,
     not user-scoped) — consistent with the rest of the system's multi-tenancy model.

3. **Locust JWT strategy**
   - What we know: All analysis endpoints require authentication.
   - What's unclear: How to provision a stable test JWT for load testing without
     hardcoding.
   - Recommendation: Locust `on_start()` method calls `POST /auth/login` with a
     dedicated test account credentials from environment variables.

---

## Recommended Plan Structure

Phase 15 maps cleanly to 3 plans aligned with the STATE.md outline:

| Plan | Name | Scope | Req IDs |
|------|------|-------|---------|
| 15-01 | cache-invalidation | Fix `on_earnings_release()` cache key bug, add `check_earnings_releases` Beat task, add `get_last_analysis_data_timestamp()` helper, add Beat schedule entry in `celery_app.py`, add refresh archiving logic, write `test_phase15_cache.py` | AI-13 |
| 15-02 | data-quality | Add `completeness_flag` to all 4 analysis result builders (tasks.py), add `history.py` with `get_analysis_history()` + `compute_analysis_diff()`, add `GET /analysis/history/{ticker}` endpoint, write `test_phase15_history.py` | AI-10, SC-4, SC-5 |
| 15-03 | performance | Add Celery concurrency tuning doc/config, write `tests/locustfile.py`, write `test_phase15_perf.py` (smoke only in pytest), run Locust headless and record results, add worker scale guidance to `docker-compose.override.yml` | SC-3 |

Each plan is independent and can be executed sequentially without blocking. Plan 15-01
is the critical path (fixes the existing bug and wires the Beat task). Plans 15-02 and
15-03 can run in parallel once 15-01 is complete.

---

## Sources

### Primary (HIGH confidence)
- Direct source file reads: `invalidation.py`, `data.py`, `tasks.py`, `models.py`,
  `router.py`, `sector.py`, `providers.py`, `schemas.py`, `celery_app.py`,
  `docker-compose.yml` — all read directly from `D:/claude-code/investiq/`
- `pytest.ini` — confirmed test framework configuration
- STATE.md + ROADMAP.md — confirmed architecture decisions and research flags

### Secondary (MEDIUM confidence)
- BRAPI docs (`brapi.dev/docs/acoes.mdx` fetched) — confirmed no earnings calendar
  endpoint exists; `incomeStatementHistoryQuarterly` is the available module
- Locust official docs / search results — confirmed headless CLI pattern and Celery
  integration approach

### Tertiary (LOW confidence)
- CVM/B3 ENET filing timing (same-day vs +1 day lag) — not directly verifiable without
  running a pilot. Flagged as Open Question.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in project, no new choices needed
- Architecture patterns: HIGH — derived directly from existing source code
- Cache key bug: HIGH — confirmed by reading both `data.py` and `invalidation.py`
- BRAPI earnings detection: MEDIUM — module name confirmed, lag timing LOW
- Load test approach: HIGH — Locust is the documented pattern for FastAPI+Celery
- Pitfalls: HIGH — derived from actual code reading

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (30 days — stable stack, no fast-moving dependencies)
