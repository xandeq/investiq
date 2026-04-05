---
phase: 19-opportunity-detector-page
plan: 01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, pydantic, celery, postgresql, sqlite, pytest]

# Dependency graph
requires:
  - phase: 16-frontend-integration-launch
    provides: "alert_engine.py dispatch_opportunity() pattern and sync DB session"
  - phase: 17-fii-screener-table
    provides: "get_global_db pattern for global tables, fii_screener router as reference"
provides:
  - "DetectedOpportunity SQLAlchemy model (detected_opportunities global table)"
  - "Migration 0022 creating detected_opportunities with 3 indexes"
  - "save_opportunity_to_db() persisting all dispatched opportunities via sync Celery session"
  - "GET /opportunity-detector/history API with asset_type and days filters"
  - "PATCH /opportunity-detector/{id}/follow toggle endpoint"
  - "12 passing tests covering all OPDET-01 sub-behaviors"
affects:
  - "19-opportunity-detector-page plan 02 (frontend page consumes this API)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "save_opportunity_to_db with get_superuser_sync_db_session for Celery persistence"
    - "Global table (no tenant_id) API endpoint using get_global_db"
    - "results[db] = save_opportunity_to_db(report) in dispatch_opportunity() for fire-and-forget DB persistence"

key-files:
  created:
    - backend/app/modules/opportunity_detector/models.py
    - backend/alembic/versions/0022_add_detected_opportunities.py
    - backend/app/modules/opportunity_detector/schemas.py
    - backend/app/modules/opportunity_detector/router.py
    - backend/tests/test_opportunity_detector_history.py
  modified:
    - backend/app/modules/opportunity_detector/alert_engine.py
    - backend/app/main.py
    - backend/tests/conftest.py

key-decisions:
  - "Used get_superuser_sync_db_session (sync) in save_opportunity_to_db — Celery workers are synchronous, async session would raise RuntimeError"
  - "save_opportunity_to_db called BEFORE Telegram/email dispatch so persistence is guaranteed even if channels fail"
  - "Exception in save_opportunity_to_db is caught and logged — never crashes the dispatch pipeline"
  - "GET /history uses get_global_db (not get_authed_db) — detected_opportunities has no RLS, global data"
  - "Patch mocks app.core.db_sync.get_superuser_sync_db_session (not alert_engine module attr) because function is imported locally inside save_opportunity_to_db"

patterns-established:
  - "Global table persistence from Celery: import get_superuser_sync_db_session locally inside function, wrap in try/except"
  - "Test isolation for anyio dual-backend (asyncio+trio): always use uuid prefix for inserted test data tickers"

requirements-completed: [OPDET-01]

# Metrics
duration: 27min
completed: 2026-04-05
---

# Phase 19 Plan 01: Opportunity Detector Backend Summary

**DetectedOpportunity model + migration 0022 + sync Celery persistence hook + GET /history (asset_type+days filters) + PATCH /{id}/follow + 12 passing tests**

## Performance

- **Duration:** 27 min
- **Started:** 2026-04-05T00:47:11Z
- **Completed:** 2026-04-05T01:13:53Z
- **Tasks:** 8 (Task 0 through Task 7)
- **Files modified:** 8

## Accomplishments

- DetectedOpportunity SQLAlchemy model with 17 fields covering all OpportunityReport data
- Migration 0022 creates `detected_opportunities` table with 3 indexes (ticker, asset_type, detected_at)
- Every opportunity dispatched by `dispatch_opportunity()` is now persisted to DB before Telegram/email delivery
- REST API: GET /opportunity-detector/history with filtering by asset_type and days window; PATCH /{id}/follow toggle
- 22 test runs (12 tests x asyncio+trio backends) all passing with zero regressions

## Task Commits

1. **Task 0: Test stubs** - `429528a` (test)
2. **Task 1: DetectedOpportunity model** - `da62f91` (feat)
3. **Task 2: Migration 0022** - `14d9c22` (feat)
4. **Task 3: Pydantic schemas** - `062d90b` (feat)
5. **Task 4: save_opportunity_to_db + dispatch hook** - `3b69454` (feat)
6. **Task 5: Router GET /history + PATCH /{id}/follow** - `7ed4417` (feat)
7. **Task 6: Register router in main.py** - `a3a5569` (feat)
8. **Task 7: Real test assertions** - `fffe6eb` (test)

## Files Created/Modified

- `backend/app/modules/opportunity_detector/models.py` - DetectedOpportunity model (17 fields, global table)
- `backend/alembic/versions/0022_add_detected_opportunities.py` - Migration creating table + 3 indexes
- `backend/app/modules/opportunity_detector/schemas.py` - OpportunityRowSchema + OpportunityHistoryResponse (Pydantic v2)
- `backend/app/modules/opportunity_detector/alert_engine.py` - Added save_opportunity_to_db() + hooked into dispatch_opportunity()
- `backend/app/modules/opportunity_detector/router.py` - GET /history and PATCH /{id}/follow endpoints
- `backend/app/main.py` - Registered opportunity_detector_router at /opportunity-detector
- `backend/tests/test_opportunity_detector_history.py` - 12 tests covering all OPDET-01 sub-behaviors
- `backend/tests/conftest.py` - Added DetectedOpportunity model import for test DB table creation

## Decisions Made

- Sync session (not async) in save_opportunity_to_db: Celery workers are synchronous by default — using async session in a sync Celery task raises RuntimeError
- DB persistence fires BEFORE Telegram/email so data is saved even if all notification channels fail
- Mock path `app.core.db_sync.get_superuser_sync_db_session` not `alert_engine.get_superuser_sync_db_session` — the function is imported locally inside the method body
- Test tickers use uuid prefix to prevent cross-run contamination in anyio dual-backend mode

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Registered DetectedOpportunity model in conftest.py**
- **Found during:** Task 7 (Implement real test assertions)
- **Issue:** DetectedOpportunity was not imported in conftest.py, so its table was never created by Base.metadata.create_all() in the test DB. Integration tests would fail with "no such table" at runtime.
- **Fix:** Added `import app.modules.opportunity_detector.models as _odm` to conftest.py following the established pattern for all other module models
- **Files modified:** backend/tests/conftest.py
- **Verification:** Integration tests pass with 22/22 passing
- **Committed in:** fffe6eb (Task 7 commit)

**2. [Rule 1 - Bug] Fixed test data isolation for anyio dual-backend runs**
- **Found during:** Task 7 (test_returns_sorted_by_detected_at_desc trio run failing)
- **Issue:** Using hardcoded tickers "AA11", "BB22", "CC33" caused collision when asyncio and trio backends both inserted rows; second run found 6 rows but expected 3, then sort assertion failed
- **Fix:** Switched to uuid-prefixed tickers following the phase17 pattern used throughout the test suite
- **Files modified:** backend/tests/test_opportunity_detector_history.py
- **Verification:** Both asyncio and trio runs pass
- **Committed in:** fffe6eb (Task 7 commit)

---

**Total deviations:** 2 auto-fixed (1 missing critical, 1 bug)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered

- Two pre-existing test failures exist in the baseline suite (test_celery_task_unhandled_exception and test_rls_on_transactions). Confirmed pre-existing by stash-verification. Not caused by this plan.

## Known Stubs

None - all API data is wired through real DB queries. No placeholder values.

## User Setup Required

None — no new external services or environment variables required.

## Next Phase Readiness

- Backend API ready for plan 19-02 frontend integration
- Endpoint: GET /opportunity-detector/history?asset_type=acao&days=30
- Endpoint: PATCH /opportunity-detector/{id}/follow
- Migration 0022 must be applied to production DB before deploy: `alembic upgrade head`
- No blockers for frontend page implementation

---
*Phase: 19-opportunity-detector-page*
*Completed: 2026-04-05*

## Self-Check: PASSED

- All 5 created files exist on disk
- All 8 task commits found in git log
- 22/22 tests passing (test_opportunity_detector_history.py)
- Full suite: 537+ passed, 2 pre-existing failures (not caused by this plan)
