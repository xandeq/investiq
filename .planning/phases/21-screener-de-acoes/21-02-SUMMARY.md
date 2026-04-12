---
phase: 21-screener-de-acoes
plan: 02
subsystem: api
tags: [fastapi, pydantic, sqlalchemy, screener, pytest]

# Dependency graph
requires:
  - phase: 21-01
    provides: variacao_12m_pct column added to ScreenerSnapshot model and DB migration
provides:
  - GET /screener/universe endpoint returning all ~900 tickers from latest snapshot
  - ScreenerUniverseRow and ScreenerUniverseResponse Pydantic schemas
  - query_screener_universe() service function with latest-date logic and market_cap ordering
  - 4 unit tests covering auth, empty, latest-snapshot, and schema validation
affects: [21-03-frontend-screener-page]

# Tech tracking
tech-stack:
  added: []
  patterns: [client-side-filtering-data-source, global-db-for-snapshot-tables]

key-files:
  created:
    - backend/tests/test_screener_universe.py
  modified:
    - backend/app/modules/screener_v2/schemas.py
    - backend/app/modules/screener_v2/service.py
    - backend/app/modules/screener_v2/router.py

key-decisions:
  - "No server-side filtering on /universe -- frontend does all filtering with useMemo (per D-09)"
  - "Orders by market_cap desc nullslast -- most liquid tickers first for UX"
  - "Reuses existing get_global_db and screener_v2 router -- no new router needed"

patterns-established:
  - "Universe endpoint pattern: fetch latest snapshot_date first, then query all rows for that date"
  - "Test pattern for screener endpoints: register_verify_and_login + db_session.add for seeding"

requirements-completed: [SCRA-01, SCRA-04]

# Metrics
duration: 8min
completed: 2026-04-12
---

# Phase 21 Plan 02: Screener Universe Endpoint Summary

**GET /screener/universe endpoint returning all ~900 B3 tickers from latest screener snapshot with 8 fields for client-side filtering**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-12T14:25:00Z
- **Completed:** 2026-04-12T14:33:07Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Added ScreenerUniverseRow (8 fields: ticker, short_name, sector, regular_market_price, variacao_12m_pct, dy, pl, market_cap) and ScreenerUniverseResponse Pydantic schemas
- Added query_screener_universe() service function that finds latest snapshot_date and returns all tickers ordered by market_cap desc nullslast
- Added GET /screener/universe endpoint on existing screener_v2 router with auth required and 30/minute rate limit
- Created 4 unit tests: unauthenticated 401, empty dataset returns [], latest-snapshot-only logic, exact 8-field schema validation

## Task Commits

Each task was committed atomically:

1. **Task 1: Pydantic schemas + service function** - `0bcd7a1` (feat)
2. **Task 2: Router endpoint + unit tests** - `859cb8b` (feat)

**Plan metadata:** (docs commit — see below)

## Files Created/Modified
- `backend/app/modules/screener_v2/schemas.py` - Added ScreenerUniverseRow and ScreenerUniverseResponse classes
- `backend/app/modules/screener_v2/service.py` - Added ScreenerUniverseRow import and query_screener_universe() function
- `backend/app/modules/screener_v2/router.py` - Added ScreenerUniverseResponse/query_screener_universe imports and /universe endpoint
- `backend/tests/test_screener_universe.py` - 4 unit tests for the universe endpoint

## Decisions Made
- No server-side filtering on /universe: all ~900 tickers returned raw, frontend filters with useMemo (per D-09 decision, matching Phase 17 FII Screener pattern)
- Reused existing screener_v2 router (already mounted at /screener in main.py) -- no changes to main.py needed
- Adapted test pattern to use register_verify_and_login + db_session (no auth_headers fixture exists)

## Deviations from Plan

None - plan executed exactly as written. The only adaptation was test fixture names (plan mentioned `auth_headers` and `async_session` which don't exist -- used `register_verify_and_login` helper and `db_session` instead, which is the established project pattern).

## Issues Encountered
- Pre-existing test failure in test_market_data_adapters.py (unrelated to this plan) -- confirmed pre-existing by checking on clean branch before my changes

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- GET /screener/universe is live and returns all tickers with 8 fields needed for the frontend screener page
- Endpoint requires auth and is rate-limited at 30/minute
- 4 tests pass, full test suite passes (pre-existing failure in test_market_data_adapters.py is unrelated)
- Ready for Plan 03: Frontend /acoes/screener page with useMemo client-side filtering

---
*Phase: 21-screener-de-acoes*
*Completed: 2026-04-12*
