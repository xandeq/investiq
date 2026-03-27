---
phase: 03-dashboard-core-ux
plan: 02
subsystem: ui
tags: [fastapi, pydantic, sqlalchemy, nextjs, react, tanstack-query, lightweight-charts, recharts, shadcn]

# Dependency graph
requires:
  - phase: 03-01
    provides: "TypeScript types (DashboardSummary, AllocationItem, TimeseriesPoint, RecentTransaction), getDashboardSummary() API function, Wave 0 test stubs in test_dashboard_api.py"
  - phase: 02-04
    provides: "PortfolioService.get_pnl() single DB pass, MarketDataService Redis reads"
provides:
  - "GET /dashboard/summary backend endpoint — 200 for auth, 401 without cookie, data_stale=true on Redis miss"
  - "DashboardService delegating to PortfolioService.get_pnl() once (no N+1)"
  - "DashboardSummaryResponse Pydantic schema with Decimal -> string auto-serialization"
  - "/dashboard frontend page with NetWorthCard, AllocationChart, PortfolioChart, MacroIndicators, RecentTransactions"
  - "Responsive 1-col mobile / 2-col desktop layout"
affects:
  - 03-03
  - 03-04

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DashboardService orchestrator pattern: calls PortfolioService once, reuses result for all derived metrics"
    - "lightweight-charts v5 addSeries(AreaSeries, opts) — NOT addAreaSeries() (v4 API, removed)"
    - "dashboard _get_redis override in conftest mirrors portfolio _get_redis override"
    - "data_stale=true on any Redis cache miss — never 500"
    - "Timeseries built from transaction history using running CMP accumulation (no external data needed)"

key-files:
  created:
    - backend/app/modules/dashboard/__init__.py
    - backend/app/modules/dashboard/schemas.py
    - backend/app/modules/dashboard/service.py
    - backend/app/modules/dashboard/router.py
    - frontend/src/features/dashboard/hooks/useDashboardSummary.ts
    - frontend/src/features/dashboard/components/NetWorthCard.tsx
    - frontend/src/features/dashboard/components/AllocationChart.tsx
    - frontend/src/features/dashboard/components/PortfolioChart.tsx
    - frontend/src/features/dashboard/components/MacroIndicators.tsx
    - frontend/src/features/dashboard/components/RecentTransactions.tsx
    - frontend/src/features/dashboard/components/DashboardContent.tsx
    - frontend/app/dashboard/page.tsx
    - frontend/src/components/ui/skeleton.tsx
  modified:
    - backend/app/main.py
    - backend/tests/conftest.py

key-decisions:
  - "DashboardService calls PortfolioService.get_pnl() once — never calls get_positions() separately — prevents N+1 DB scans"
  - "data_stale flag propagated from any position.current_price_stale=True — graceful degradation, never 500"
  - "portfolio_timeseries built from transaction history using running weighted-average-cost accumulation — no Redis dependency for historical data"
  - "PortfolioChart uses lightweight-charts v5 addSeries(AreaSeries) API (breaking change from v4 addAreaSeries)"
  - "skeleton.tsx created (shadcn pattern) — not in existing components"
  - "DashboardContent is client component assembler; dashboard/page.tsx is server component entry — clean SSR/CSR boundary"

patterns-established:
  - "Dashboard endpoint pattern: single service call, derived metrics from single result"
  - "Test isolation: dependency_overrides for _get_redis on each new router"
  - "Chart component pattern: useEffect + createChart in browser only, 'use client' directive"

requirements-completed:
  - VIEW-01
  - VIEW-02

# Metrics
duration: 35min
completed: 2026-03-14
---

# Phase 3 Plan 02: Dashboard Backend + Frontend Summary

**GET /dashboard/summary endpoint + /dashboard page with 5 components: NetWorthCard, AllocationChart (donut), PortfolioChart (area), MacroIndicators, RecentTransactions — full suite 103 tests green**

## Performance

- **Duration:** 35 min
- **Started:** 2026-03-14T19:00:00Z
- **Completed:** 2026-03-14T19:35:00Z
- **Tasks:** 2 (Task 0 backend TDD + Task 1 frontend)
- **Files modified:** 15

## Accomplishments
- Backend dashboard module with schemas, service, router — DashboardSummaryResponse with all 10 required fields
- DashboardService calls PortfolioService.get_pnl() exactly once, no N+1 DB scans
- 7 dashboard tests pass (RED → GREEN cycle); full suite 103 passed, 7 skipped
- Frontend /dashboard page with all 5 components, responsive grid (mobile 1-col, desktop 2-col)
- PortfolioChart uses lightweight-charts v5 correct API (addSeries(AreaSeries))
- npm run build exits 0, /dashboard route 167kB

## Task Commits

1. **Task 0: Backend dashboard module** - `55211b6` (feat)
2. **Task 1: Frontend dashboard page** - `591e080` (feat)

## Files Created/Modified

- `backend/app/modules/dashboard/__init__.py` - Module init
- `backend/app/modules/dashboard/schemas.py` - DashboardSummaryResponse, AllocationSummary, TimeseriesPoint, RecentTransaction
- `backend/app/modules/dashboard/service.py` - DashboardService.get_summary() orchestrator
- `backend/app/modules/dashboard/router.py` - GET /dashboard/summary with _get_redis dependency
- `backend/app/main.py` - Added dashboard router at prefix /dashboard
- `backend/tests/conftest.py` - Added dashboard_get_redis override
- `frontend/src/features/dashboard/hooks/useDashboardSummary.ts` - TanStack Query v5 hook
- `frontend/src/features/dashboard/components/NetWorthCard.tsx` - Patrimônio card with return/daily P&L
- `frontend/src/features/dashboard/components/AllocationChart.tsx` - Donut via shadcn + recharts
- `frontend/src/features/dashboard/components/PortfolioChart.tsx` - Area chart via lightweight-charts v5
- `frontend/src/features/dashboard/components/MacroIndicators.tsx` - SELIC/CDI/IPCA/PTAX grid
- `frontend/src/features/dashboard/components/RecentTransactions.tsx` - Last 10 transactions table
- `frontend/src/features/dashboard/components/DashboardContent.tsx` - Client assembler component
- `frontend/app/dashboard/page.tsx` - Server component entry point
- `frontend/src/components/ui/skeleton.tsx` - Loading placeholder (Rule 3 auto-add)

## Decisions Made
- DashboardService orchestrates PortfolioService.get_pnl() once — no separate get_positions() call
- data_stale=true on any Redis miss — returns valid response, never 500
- timeseries built from CMP accumulation over transaction history — no Redis dependency
- lightweight-charts v5 addSeries(AreaSeries) is correct API (addAreaSeries removed in v5)
- DashboardContent "use client" boundary — page.tsx stays as server component

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Created skeleton.tsx component**
- **Found during:** Task 1 (Frontend components)
- **Issue:** Plan referenced `@/components/ui/skeleton` but file did not exist in the project
- **Fix:** Created minimal shadcn animate-pulse skeleton component
- **Files modified:** frontend/src/components/ui/skeleton.tsx
- **Verification:** npm run build succeeds, Skeleton imports resolve
- **Committed in:** 591e080 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 2 - missing critical)
**Impact on plan:** Required for loading states to compile. No scope creep.

## Issues Encountered
None beyond the skeleton.tsx auto-fix.

## Next Phase Readiness
- GET /dashboard/summary is live and tested — ready for Plan 03-03 (dividends, charts deep-dive)
- All 5 dashboard components render; human visual verification required at checkpoint
- /dashboard middleware protection already in place (PROTECTED_PATHS from 03-01)

---
*Phase: 03-dashboard-core-ux*
*Completed: 2026-03-14*
