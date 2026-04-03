---
phase: 13-core-analysis-engine
plan: 02
subsystem: api
tags: [celery, fastapi, earnings, dividend, analysis, brapi]

# Dependency graph
requires:
  - phase: 13-01
    provides: "fetch_fundamentals(), data.py, dcf.py, run_dcf pattern"
provides:
  - "calculate_earnings_analysis() with EPS history, CAGR, accrual ratio, FCF conversion, quality flag"
  - "calculate_dividend_analysis() with yield, payout, coverage, consistency, sustainability"
  - "run_earnings and run_dividend Celery tasks (async job pattern)"
  - "POST /analysis/earnings and POST /analysis/dividend endpoints (202)"
affects: [13-03-sector, 14-llm-narrative, 16-frontend]

# Tech tracking
tech-stack:
  added: []
  patterns: ["earnings quality flag (high/medium/low) from accrual ratio + FCF conversion", "dividend sustainability flag (safe/warning/risk) from payout, coverage, dividend cuts"]

key-files:
  created:
    - backend/app/modules/analysis/earnings.py
    - backend/app/modules/analysis/dividend.py
    - backend/tests/test_phase13_earnings_dividend.py
  modified:
    - backend/app/modules/analysis/tasks.py
    - backend/app/modules/analysis/router.py

key-decisions:
  - "Accrual ratio uses (total_debt + total_cash) as proxy for total assets since BRAPI does not expose total assets directly"
  - "Dividend cut detection checks last 3 year-over-year changes for >20% decline"
  - "Sustainability assessment is strictly ordered: risk checks first, then warning, then safe"

patterns-established:
  - "Analysis task pattern: quota check, running, fetch, calculate, LLM narrative, versioning, complete, cost log"
  - "Router endpoint pattern: rate limit, quota, create job, dispatch delay, return 202"

requirements-completed: [AI-02, AI-03]

# Metrics
duration: 6min
completed: 2026-04-03
---

# Phase 13 Plan 02: Earnings + Dividend Analysis Summary

**Earnings quality analysis (accrual ratio, FCF conversion, EPS CAGR) and dividend sustainability analysis (payout, coverage, consistency, safe/warning/risk flags) as Celery tasks with 202 async endpoints**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-03T00:41:38Z
- **Completed:** 2026-04-03T00:47:17Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Earnings module computes 5-year EPS history with YoY growth, CAGR, accrual ratio, FCF conversion, and earnings quality flag (high/medium/low)
- Dividend module computes yield, payout ratio, coverage ratio, 5-year consistency score, sustainability flag (safe/warning/risk), and dividend history
- Both analysis types follow exact run_dcf Celery pattern: quota check, LLM narrative in PT-BR with static fallback, data versioning, cost logging
- Two new POST endpoints (/analysis/earnings, /analysis/dividend) return 202 with job_id for async polling
- 29 tests cover all calculations, edge cases, quality flags, sustainability assessment, and endpoint integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Earnings and dividend calculation modules** - `2a8af0f` (feat)
2. **Task 2: Celery tasks + router endpoints + tests** - `a17bdc2` (feat)

## Files Created/Modified
- `backend/app/modules/analysis/earnings.py` - EPS history, CAGR, accrual ratio, FCF conversion, quality flag
- `backend/app/modules/analysis/dividend.py` - Yield, payout, coverage, consistency, sustainability assessment
- `backend/app/modules/analysis/tasks.py` - Added run_earnings and run_dividend Celery tasks
- `backend/app/modules/analysis/router.py` - Added POST /earnings and POST /dividend endpoints
- `backend/tests/test_phase13_earnings_dividend.py` - 29 tests for all calculations and endpoints

## Decisions Made
- Used (total_debt + total_cash) as proxy for total assets in accrual ratio since BRAPI does not expose total assets directly; documented in data_completeness note
- Dividend sustainability uses strict priority: risk triggers checked first (payout>0.80, coverage<1.2, 20%+ cut), then warning (payout>0.60, coverage<1.5), then safe
- EPS CAGR returns None when oldest EPS is negative (no meaningful growth calculation possible)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed accrual ratio threshold boundary**
- **Found during:** Task 2 (test writing)
- **Issue:** Accrual ratio of exactly 0.40 rated as "moderate" not "poor" (threshold is >0.40 for poor)
- **Fix:** Adjusted test to use 0.45 accrual ratio for the "poor" test case
- **Files modified:** backend/tests/test_phase13_earnings_dividend.py
- **Committed in:** a17bdc2

---

**Total deviations:** 1 auto-fixed (1 bug in test)
**Impact on plan:** Minor test adjustment. No scope creep.

## Known Stubs

None - all data flows are wired to real fundamentals data from BRAPI via fetch_fundamentals().

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Earnings and dividend analysis modules complete, ready for Phase 13 Plan 03 (sector peer comparison)
- All three analysis types (DCF, earnings, dividend) share the same async job pattern and can be consumed by the frontend
- LLM narrative generation is wired with static fallback for when providers are unavailable

---
*Phase: 13-core-analysis-engine*
*Completed: 2026-04-03*
