---
phase: 13-core-analysis-engine
plan: 01
subsystem: analysis
tags: [dcf, brapi, bcb, selic, wacc, sensitivity, real-data]
dependency_graph:
  requires: [12-03]
  provides: [data.py, dcf.py, real-dcf-task]
  affects: [tasks.py, schemas.py]
tech_stack:
  added: [bcb-api]
  patterns: [redis-cache-24h, capm-wacc, 2-stage-fcff, sensitivity-3scenario]
key_files:
  created:
    - backend/app/modules/analysis/data.py
    - backend/app/modules/analysis/dcf.py
    - backend/tests/test_phase13_dcf.py
  modified:
    - backend/app/modules/analysis/tasks.py
    - backend/app/modules/analysis/schemas.py
decisions:
  - Used _resolve_brapi_token() with same priority as BrapiClient (env > AWS SM) rather than importing BrapiClient directly, to keep sync HTTP calls simple
  - Debt cost simplified as SELIC + 2pp spread (not ticker-specific)
  - Net debt subtracted from EV in sensitivity (equity value per share)
  - Growth rate CAGR uses reversed cashflow_history (BRAPI returns newest first)
metrics:
  duration: 344s
  completed: "2026-04-03T00:38:08Z"
  tasks_completed: 2
  tasks_total: 2
  tests_added: 20
  files_created: 3
  files_modified: 2
requirements: [AI-01]
---

# Phase 13 Plan 01: DCF Real Data Layer Summary

Real BRAPI fundamentals fetching + BCB SELIC integration + 2-Stage FCFF DCF with CAPM WACC and 3-scenario sensitivity analysis, replacing all Phase 12 stubs.

## What Was Built

### data.py - BRAPI Data Layer + BCB SELIC
- `fetch_fundamentals(ticker)`: Calls BRAPI with 5 modules (summaryProfile, defaultKeyStatistics, financialData, incomeStatementHistory, cashflowHistory), parses 20+ fields including income/cashflow history and dividend data. Redis cache with 24h TTL. Builds data_completeness metadata.
- `get_selic_rate()`: Calls BCB API serie 432, returns (rate_decimal, date_str, is_fallback). Hardcoded fallback 14.75% on failure. Redis cached 24h.
- `DataFetchError`: Exception with ticker, source, detail fields.

### dcf.py - DCF Calculation Engine
- `calculate_wacc()`: CAPM formula (Ke = SELIC + beta * ERP_BRAZIL=0.07, Kd = SELIC + 2pp). Tax rate 34% (Brazil corporate).
- `calculate_dcf()`: 5-year explicit FCF projections + Gordon Growth terminal value. Returns fair_value, enterprise_value, projected_fcfs, terminal_value.
- `calculate_dcf_with_sensitivity()`: 3 scenarios (bear: growth-2pp/WACC+2pp, base, bull: growth+2pp/WACC-2pp). Subtracts net_debt from EV for equity value. Includes key_drivers analysis.
- `estimate_growth_rate()`: CAGR from last 5 years FCF. Falls back to 5% default for insufficient/negative data.

### tasks.py - Wired Real Functions
- Deleted `_fetch_fundamentals_stub()` and `_calculate_dcf_stub()`
- `run_dcf()` now: BRAPI data -> BCB SELIC -> CAPM WACC -> growth estimation -> DCF sensitivity -> LLM narrative
- Result includes projected_fcfs, key_drivers, scenarios, data_completeness, BCB data source

### schemas.py - New Request Types
- `EarningsRequest`, `DividendRequest`, `SectorRequest` ready for Plans 02/03

### Tests - 20 Passing
- Data parsing, Redis caching, cache hits, BCB parsing, BCB fallback
- WACC CAPM formula, beta=None default, zero capital edge case
- DCF basic, WACC<=terminal_growth ValueError, projections increase
- Sensitivity bear<base<bull, key_drivers, projected_fcfs
- Growth rate estimation, insufficient data fallback, negative FCF, empty history
- Stub removal verification, real import verification

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | 59be76c | data.py + dcf.py created |
| 2 | e275c1a | tasks.py wired + schemas + 20 tests |

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. All Phase 12 DCF stubs have been replaced with real implementations.

## Self-Check: PASSED

All 5 files found. Both commits (59be76c, e275c1a) verified. 20/20 tests passing.
