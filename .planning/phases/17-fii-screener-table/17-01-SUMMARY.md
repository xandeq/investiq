---
phase: 17-fii-screener-table
plan: "01"
subsystem: backend
tags: [fii, screener, celery, percentile-ranking, alembic, fastapi]
dependency_graph:
  requires:
    - "Phase 12: AnalysisJob pattern (async Celery + sync DB session)"
    - "Phase 8: get_global_db pattern + screener_snapshots table"
    - "market_universe: FIIMetadata + ScreenerSnapshot models"
  provides:
    - "GET /fii-screener/ranked endpoint"
    - "calculate_fii_scores Celery beat task (08:00 BRT daily)"
    - "FIIMetadata score columns (8 new columns)"
    - "FIIScoredRow, FIIScoredResponse Pydantic schemas"
  affects:
    - "Phase 17 Plan 02: frontend screener table page (consumes this API)"
    - "Phase 18: FII detail page (may reuse score data)"
tech_stack:
  added:
    - "app.modules.fii_screener (new module)"
    - "Alembic migration 0021 (8 new fii_metadata columns)"
  patterns:
    - "Percentile rank calculation: _percentile_ranks() helper with single/empty/None edge cases"
    - "Score formula: DY_rank*0.5 + PVP_rank_inverted*0.3 + liquidity_rank*0.2"
    - "Celery sync task with get_sync_db_session(tenant_id=None)"
    - "Read-only endpoint with get_global_db (no tenant scope)"
    - "NULLS LAST ordering via SQLAlchemy desc().nullslast()"
key_files:
  created:
    - "backend/alembic/versions/0021_add_fii_score_columns.py"
    - "backend/app/modules/fii_screener/__init__.py"
    - "backend/app/modules/fii_screener/schemas.py"
    - "backend/app/modules/fii_screener/router.py"
    - "backend/tests/test_phase17_fii_screener.py"
  modified:
    - "backend/app/modules/market_universe/models.py (8 new FIIMetadata columns)"
    - "backend/app/modules/market_universe/tasks.py (_percentile_ranks + calculate_fii_scores)"
    - "backend/app/celery_app.py (calculate-fii-scores-daily beat entry)"
    - "backend/app/main.py (fii_screener router registration)"
    - "backend/tests/conftest.py (get_global_db override for integration tests)"
decisions:
  - "Percentile rank single-element: returns [50] (median), not [0] — chosen to avoid unfair extreme ranking for FIIs in sparse data"
  - "Score is Decimal(str(computed_float)) to preserve precision without floating-point drift"
  - "short_name via LEFT JOIN with latest ScreenerSnapshot — no extra round-trip, reuses existing snapshot data"
  - "conftest client fixture now overrides get_global_db to route integration tests through test SQLite DB"
metrics:
  duration_seconds: 590
  completed_date: "2026-04-04"
  tasks_completed: 2
  tests_added: 18
  files_created: 5
  files_modified: 5
---

# Phase 17 Plan 01: FII Screener Backend Summary

## One-liner

Percentile-based FII composite scorer (DY 50% + P/VP 30% + liquidity 20%) with Celery beat task at 08:00 BRT and pre-scored ranked API endpoint GET /fii-screener/ranked.

## What Was Built

### Task 1: Schema, Migration, Model, Celery Task, and Unit Tests (TDD)

**Alembic Migration 0021** (`backend/alembic/versions/0021_add_fii_score_columns.py`):
- Adds 8 columns to `fii_metadata`: `dy_12m`, `pvp`, `daily_liquidity`, `score`, `dy_rank`, `pvp_rank`, `liquidity_rank`, `score_updated_at`
- Correct revision chain: down_revision = "0020_add_analysis_tables"
- Full downgrade removes all 8 columns

**FIIMetadata model** (`backend/app/modules/market_universe/models.py`):
- 8 new `Mapped[T | None]` columns added after `num_cotistas`

**`_percentile_ranks()` helper** (`backend/app/modules/market_universe/tasks.py`):
- Handles empty list, all-None, single element (returns [50]), and mixed None/value inputs correctly

**`calculate_fii_scores` Celery task** (`backend/app/modules/market_universe/tasks.py`):
- Uses `get_sync_db_session(tenant_id=None)` (sync psycopg2, not asyncpg)
- Queries latest snapshot date from ScreenerSnapshot
- Joins FIIMetadata with ScreenerSnapshot filtered to FII tickers (ending in "11")
- Computes DY, P/VP (inverted: `100 - pvp_rank_raw`), and liquidity percentile ranks
- Score = `DY_rank * 0.5 + PVP_rank_inverted * 0.3 + liquidity_rank * 0.2`
- Any NULL metric → score = None
- Batch-updates fii_metadata rows with score_updated_at timestamp

**Beat schedule** (`backend/app/celery_app.py`):
- Key: `"calculate-fii-scores-daily"` → `crontab(minute=0, hour=8)` daily

**FII Screener schemas** (`backend/app/modules/fii_screener/schemas.py`):
- `FIIScoredRow`: ticker, short_name, segmento, dy_12m, pvp, daily_liquidity, score, dy_rank, pvp_rank, liquidity_rank, score_updated_at (all as strings for JSON precision)
- `FIIScoredResponse`: disclaimer, score_available, total, results

### Task 2: API Endpoint and Router Registration

**`GET /fii-screener/ranked`** (`backend/app/modules/fii_screener/router.py`):
- Requires `get_current_user` (auth gate → 401 without token)
- Uses `get_global_db` (no tenant scope — FII data is global)
- Rate-limited: `@limiter.limit("30/minute")`
- Queries FIIMetadata + LEFT JOIN latest ScreenerSnapshot for `short_name`
- Orders by: `FIIMetadata.score.desc().nullslast()`, then `ticker.asc()`
- Sets `score_available=True` only if at least one row has score != None
- Converts Decimal to string for JSON precision

**main.py**: router registered as `include_router(fii_screener_router, prefix="/fii-screener")`

**conftest.py**: added `get_global_db` override pointing to test SQLite session (Rule 2: missing critical test infrastructure)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Infrastructure] Added get_global_db override to conftest**
- **Found during:** Task 2 integration test execution
- **Issue:** The `client` fixture in conftest.py did not override `get_global_db`, so endpoints using this dependency would fail in tests (attempting to connect to real PostgreSQL)
- **Fix:** Added `override_get_global_db()` that yields `db_session`, registered in `app.dependency_overrides`
- **Files modified:** `backend/tests/conftest.py`
- **Commit:** 50b862e

**2. [Rule 1 - Bug] Single-element percentile rank returns 50, not 0**
- **Found during:** Task 1 TDD RED→GREEN transition
- **Issue:** Plan specifies `_percentile_ranks([42]) == [50]`, but formula `round(0 / max(1-1, 1) * 100) = 0`. Added special case for n==1
- **Fix:** Added `if n == 1: ranks[orig_i] = 50` branch before the general loop
- **Files modified:** `backend/app/modules/market_universe/tasks.py`
- **Commit:** 4c48633

**3. [Rule 3 - Ticker uniqueness] Test tickers use UUID prefix to avoid UNIQUE constraint**
- **Found during:** Task 2 integration test execution (trio/asyncio both run tests)
- **Issue:** Tests running on multiple backends (asyncio + trio) would insert duplicate tickers
- **Fix:** Used `uuid4().hex[:4].upper()` as prefix for test FII tickers in integration tests
- **Files modified:** `backend/tests/test_phase17_fii_screener.py`
- **Commit:** 50b862e

## Pre-existing Issues (Out of Scope)

- `test_phase12_foundation.py::TestAsyncJobs::test_celery_task_unhandled_exception`: Fails due to `_fetch_fundamentals_stub` not existing in analysis.tasks. Pre-existing before Phase 17 — confirmed via git stash test.

## Test Results

- Phase 17 tests: **18/18 passing**
- Full suite (excluding known pre-existing failure): **260 passing**
- No new failures introduced

## Known Stubs

None — all data is properly wired. The `score_available` flag correctly returns `False` when no scores have been computed yet (first run before Celery task executes), which is a legitimate runtime state, not a stub.

## Self-Check: PASSED

- backend/alembic/versions/0021_add_fii_score_columns.py: FOUND
- backend/app/modules/fii_screener/__init__.py: FOUND
- backend/app/modules/fii_screener/schemas.py: FOUND
- backend/app/modules/fii_screener/router.py: FOUND
- backend/tests/test_phase17_fii_screener.py: FOUND
- .planning/phases/17-fii-screener-table/17-01-SUMMARY.md: FOUND
- Task 1 commit 4c48633: FOUND
- Task 2 commit 50b862e: FOUND
