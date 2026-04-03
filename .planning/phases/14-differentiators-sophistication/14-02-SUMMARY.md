---
phase: 14-differentiators-sophistication
plan: 02
subsystem: testing, api
tags: [pytest, dcf, sensitivity, narrative, llm, cost-monitoring, fastapi]

requires:
  - phase: 13-core-analysis-engine
    provides: calculate_dcf_with_sensitivity, AnalysisCostLog model, call_analysis_llm, estimate_llm_cost, log_analysis_cost
  - phase: 14-01
    provides: LLM narrative generation, prompt construction, PT-BR directive

provides:
  - 30-test suite validating AI-05 (narrative quality), AI-06 (sensitivity), AI-07 (assumptions), cost tracking
  - GET /analysis/admin/costs endpoint (tenant-scoped, aggregated by type and day)

affects: [16-detail-page, 15-cache-invalidation]

tech-stack:
  added: []
  patterns:
    - "AsyncMock for testing async FastAPI endpoints with DB dependency overrides"
    - "patch('app.core.db_sync.get_superuser_sync_db_session') for cost logging tests (deferred import pattern)"
    - "FastAPI dependency_overrides with yield for async DB mocks in TestClient"

key-files:
  created:
    - backend/tests/test_phase14_quality.py
  modified:
    - backend/app/modules/analysis/router.py

key-decisions:
  - "Admin costs endpoint placed before /{job_id} catch-all route in router.py to avoid 404 routing conflict"
  - "days param validated with le=90 via FastAPI Query — days>90 returns 422 (not clamped)"
  - "Cost log test patches app.core.db_sync.get_superuser_sync_db_session (not app.modules.analysis.cost) because the import is deferred inside the function body"

requirements-completed: [AI-05, AI-06, AI-07]

duration: 15min
completed: 2026-04-03
---

# Phase 14 Plan 02: Narrative Quality + Sensitivity Tests + Admin Cost Endpoint Summary

**30 pytest tests validating bear<base<bull for 10 sensitivity inputs, PT-BR narrative quality, proportional DCF assumptions, and a tenant-scoped GET /analysis/admin/costs endpoint aggregating cost by type and day**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-03T10:10:00Z
- **Completed:** 2026-04-03T10:27:30Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments

- 30 tests across 5 categories: narrative quality (5), sensitivity (12), custom assumptions (5), cost tracking (4), admin endpoint (2) — all passing
- Proved bear < base < bull ordering holds for 10 parameterized DCF input combinations (high/low growth, high/low WACC, negative net_debt, various company sizes)
- GET /analysis/admin/costs endpoint with SQLAlchemy aggregation (func.count, func.sum, func.avg, func.date) grouped by analysis_type and by day
- No regressions: Phase 13 tests (49) all still pass

## Task Commits

1. **Task 1: Narrative quality + sensitivity + assumptions test suite** - `8ec4bb6` (test)
2. **Task 2: Admin cost monitoring endpoint** - `60b886b` (feat)

## Files Created/Modified

- `backend/tests/test_phase14_quality.py` - 502-line test file with 30 tests covering AI-05/AI-06/AI-07 and cost monitoring
- `backend/app/modules/analysis/router.py` - Added GET /analysis/admin/costs endpoint before /{job_id} catch-all; added AnalysisCostLog import, func, timedelta, Query imports

## Decisions Made

- Admin costs endpoint must be declared before `/{job_id}` wildcard route — path `/admin/costs` would otherwise match as a job_id and return 404
- days parameter uses `le=90` FastAPI Query constraint; values >90 return 422 (consistent behavior, no silent clamping)
- Cost log test patches the `get_superuser_sync_db_session` at `app.core.db_sync` (not `app.modules.analysis.cost`) because cost.py uses a deferred import inside the function body — the attribute doesn't exist on the module at patch time

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed patch path for cost log test**
- **Found during:** Task 1 (test_cost_log_created_on_analysis)
- **Issue:** Patch target `app.modules.analysis.cost.get_superuser_sync_db_session` raised AttributeError because the import is deferred inside the function body, not at module level
- **Fix:** Changed patch target to `app.core.db_sync.get_superuser_sync_db_session` (the actual module holding the symbol)
- **Files modified:** backend/tests/test_phase14_quality.py
- **Committed in:** 8ec4bb6 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed async DB mock in endpoint tests**
- **Found during:** Task 2 (test_admin_costs_endpoint_returns_200)
- **Issue:** Plain MagicMock for DB session returned 500 because `await db.execute()` requires an awaitable — `MagicMock()` is not awaitable
- **Fix:** Changed to `AsyncMock()` for the session so `await db.execute()` resolves correctly
- **Files modified:** backend/tests/test_phase14_quality.py
- **Committed in:** 60b886b (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - Bug)
**Impact on plan:** Both fixes were necessary for tests to pass. No scope creep.

## Issues Encountered

None beyond the two auto-fixed deviations above.

## Known Stubs

None — all test assertions validate real function outputs from dcf.py, cost.py, schemas.py, and the new admin endpoint.

## Self-Check

Files created:
- `D:/claude-code/investiq/backend/tests/test_phase14_quality.py` — FOUND
- `D:/claude-code/investiq/.planning/phases/14-differentiators-sophistication/14-02-SUMMARY.md` — this file

Commits:
- 8ec4bb6 (test(14-02)) — FOUND
- 60b886b (feat(14-02)) — FOUND

## Next Phase Readiness

- AI-05, AI-06, AI-07 requirements proven by test suite — ready for Phase 16 detail page
- Admin cost monitoring endpoint deployed and tested — ready for ops dashboard (Phase 16 plan 03)
- Phase 13 test suite (49 tests) still passing — no regressions

---
*Phase: 14-differentiators-sophistication*
*Completed: 2026-04-03*
