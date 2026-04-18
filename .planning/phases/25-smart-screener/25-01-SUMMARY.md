---
phase: 25-smart-screener
plan: "01"
subsystem: advisor
tags: [smart-screener, portfolio-advisor, backend, frontend, react-query]
dependency_graph:
  requires: [23-01]
  provides: [GET /advisor/screener, useSmartScreener, SmartScreenerSection]
  affects: [AdvisorContent.tsx, advisor/service.py, advisor/router.py]
tech_stack:
  added: [ComplementaryAssetRow Pydantic schema, useSmartScreener React Query hook]
  patterns: [sector-gap-filtering, relevance-scoring, client-side-useMemo-filtering]
key_files:
  created:
    - backend/tests/test_advisor_smart_screener.py
    - frontend/src/features/advisor/hooks/useSmartScreener.ts
  modified:
    - backend/app/modules/advisor/service.py
    - backend/app/modules/advisor/router.py
    - frontend/src/features/advisor/api.ts
    - frontend/src/features/advisor/types.ts
    - frontend/src/features/ai/components/AdvisorContent.tsx
decisions:
  - "Field mapping: ComplementaryAssetRow.preco_atual = ScreenerSnapshot.regular_market_price; dy_12m_pct = ScreenerSnapshot.dy (actual column names differ from plan)"
  - "Relevance score formula: dy*200 + (50 - variacao*100); DY fractional (0.12=12%), variacao fractional — yields 0-100 range"
  - "Empty portfolio: returns full screener universe with neutral score=50 (no sector gaps to compute)"
  - "Screener hook enabled only when health.has_portfolio=true — avoids unnecessary API call for empty portfolios"
  - "useSmartScreener uses apiClient from advisor/api.ts (not raw fetch) — consistent with usePortfolioHealth pattern"
metrics:
  duration_seconds: 408
  completed_date: "2026-04-18"
  tasks_completed: 3
  files_created: 2
  files_modified: 5
---

# Phase 25 Plan 01: Smart Screener — Complementary Assets Summary

**One-liner:** GET /advisor/screener filters screener universe to sectors not in user's portfolio, ranked by DY-weighted relevance score, with frontend table + sector filter in AdvisorContent.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create test file for smart screener (Wave 0 TDD) | 6f8acac | backend/tests/test_advisor_smart_screener.py |
| 2 | Implement GET /advisor/screener + get_complementary_assets | a51d576 | advisor/service.py, advisor/router.py |
| 3 | Create useSmartScreener hook and SmartScreener section | 6021421 | useSmartScreener.ts, AdvisorContent.tsx, api.ts, types.ts |

## What Was Built

**Backend:**
- `ComplementaryAssetRow` Pydantic schema in `service.py` with fields: `ticker`, `sector`, `preco_atual`, `dy_12m_pct`, `variacao_12m_pct`, `market_cap`, `relevance_score`
- `get_complementary_assets()` service function: loads portfolio tickers from tenant DB, joins with screener_snapshots (global DB) to identify held sectors, queries for tickers in other sectors, scores by `dy*200 + (50 - variacao*100)`, sorts descending
- `GET /advisor/screener` endpoint: auth required, rate limit 30/min, query param `limit=100`

**Frontend:**
- `ComplementaryAsset` TypeScript interface in `advisor/types.ts`
- `getSmartScreener()` API function in `advisor/api.ts` using `apiClient`
- `useSmartScreener` hook (React Query, `staleTime=10min`, `enabled` param gated on `has_portfolio`)
- `SmartScreenerSection` component in `AdvisorContent.tsx`: table with ticker/sector/DY/variação/preço columns, sector dropdown filter, shows first 50 of N results, tickers link to `/stock/[ticker]`
- Integrated in `AdvisorMain` after AI Diagnosis section, only rendered when `health?.has_portfolio` is true

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Corrected ScreenerSnapshot field names**
- **Found during:** Task 2 (reading actual model)
- **Issue:** Plan specified `dy_12m_pct` and `preco_atual` as ScreenerSnapshot fields. Actual model uses `dy` and `regular_market_price`
- **Fix:** ComplementaryAssetRow maps `preco_atual` → `s.regular_market_price` and `dy_12m_pct` → `s.dy` internally; external API surface keeps plan's field names for frontend compatibility
- **Files modified:** backend/app/modules/advisor/service.py

**2. [Rule 2 - Pattern] Used apiClient instead of raw fetch in hook**
- **Found during:** Task 3 (per extra_context instruction)
- **Issue:** Plan specified `fetch("/api/advisor/screener")` in hook. Project pattern uses `apiClient` from `@/lib/api-client` (handles auth headers, base URL, error handling)
- **Fix:** Added `getSmartScreener()` to `advisor/api.ts`, hook calls it via apiClient
- **Files modified:** frontend/src/features/advisor/api.ts, frontend/src/features/advisor/hooks/useSmartScreener.ts

**3. [Rule 3 - Pre-existing] Dashboard test failure**
- **Found during:** Full suite run
- **Issue:** `test_dashboard_api.py::test_dashboard_summary_returns_allocation` fails pre-existing (confirmed by git stash verification)
- **Fix:** Not caused by this plan's changes — scope boundary applies
- **Status:** Deferred to deferred-items

## Verification Results

- `python -m pytest tests/test_advisor_smart_screener.py -v`: 3 passed
- `npx tsc --noEmit` from frontend/: 0 errors
- Full suite: 179+ passed (1 pre-existing failure unrelated to this plan)

## Known Stubs

None. All data flows from real database queries via screener_snapshots table.

## Self-Check: PASSED
