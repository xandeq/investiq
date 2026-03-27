---
phase: 03-dashboard-core-ux
plan: 03
subsystem: ui
tags: [react, nextjs, tanstack-query, lightweight-charts, typescript, recharts]

# Dependency graph
requires:
  - phase: 03-02
    provides: "Backend dashboard API, DashboardSummary with portfolio_timeseries, market data adapters"
  - phase: 03-01
    provides: "Portfolio types (PositionResponse, PnLResponse, DividendResponse, BenchmarkResponse), API functions (getPositions, getPnl, getDividends, getBenchmarks), formatters (formatBRL, formatPct, formatDate)"
provides:
  - "/portfolio page with P&L table, benchmark chart, and dividend history"
  - "PnlTable — P&L per asset with unrealized_pnl, green/red coloring, 'desde a compra / no mês / no ano' labeling"
  - "DividendHistory — dividend table with client-side year + asset_class filter dropdowns"
  - "BenchmarkChart — portfolio area series (lightweight-charts v5) with CDI/IBOVESPA annotations in legend"
  - "PositionsTable — current holdings summary chips with live prices"
  - "PortfolioContent — client-side page assembler for all 4 portfolio panels"
  - "Four TanStack Query hooks: usePositions, usePnl, useDividends, useBenchmarks"
affects: [04-tax-reporting, 05-notifications]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Client-side filter state with useMemo — all dividends fetched once, filtered in React without extra API calls"
    - "v1 benchmark approximation — portfolio timeseries line + CDI/IBOVESPA current rates as legend annotations (not chart lines)"
    - "PnlCell component — value=null renders dash (stale), value>=0 renders green, value<0 renders red"
    - "overflow-x-auto on all tables — prevents horizontal viewport overflow on mobile"

key-files:
  created:
    - frontend/src/features/portfolio/hooks/usePositions.ts
    - frontend/src/features/portfolio/hooks/usePnl.ts
    - frontend/src/features/portfolio/hooks/useDividends.ts
    - frontend/src/features/portfolio/hooks/useBenchmarks.ts
    - frontend/src/features/portfolio/components/PnlTable.tsx
    - frontend/src/features/portfolio/components/PositionsTable.tsx
    - frontend/src/features/portfolio/components/DividendHistory.tsx
    - frontend/src/features/portfolio/components/BenchmarkChart.tsx
    - frontend/src/features/portfolio/components/PortfolioContent.tsx
    - frontend/app/portfolio/page.tsx
  modified: []

key-decisions:
  - "v1 BenchmarkChart uses portfolio timeseries from /dashboard/summary as the only line — CDI and IBOVESPA shown as current snapshot values in legend, labeled clearly; historical timeseries deferred"
  - "DividendHistory filtering is purely client-side (no query param refetch) — all dividends loaded once, memoized filter avoids re-fetching on filter change"
  - "PnlCell null check — when current_price_stale=true, unrealized_pnl comes back null from backend; UI renders dash, never crashes"

patterns-established:
  - "Hook-per-endpoint pattern: one useQuery hook file per API endpoint — usePositions, usePnl, useDividends, useBenchmarks"
  - "Stale data handling: current_price_stale=true shows amber dash in Preço Atual column; unrealized_pnl null shows dash in P&L column"
  - "Footer totals row in tables — tfoot with total_portfolio_value and unrealized_pnl_total for at-a-glance summary"

requirements-completed: [VIEW-02, VIEW-03, VIEW-04]

# Metrics
duration: 15min
completed: 2026-03-14
---

# Phase 3 Plan 03: Portfolio Analytics Page Summary

**P&L table per asset with green/red coloring, dividend history with client-side year+class filters, and benchmark chart using lightweight-charts v5 portfolio area series — completing Phase 3 analytics view at /portfolio**

## Performance

- **Duration:** ~15 min (continuation of prior session — Tasks 1+2 committed, Task 3 verified in this session)
- **Started:** 2026-03-14T16:19:00Z
- **Completed:** 2026-03-14T17:42:00Z
- **Tasks:** 3 (2 feat commits + 1 verification-only)
- **Files modified:** 10 created, 0 modified

## Accomplishments

- /portfolio page assembled with 4 panels: PositionsTable chips, PnlTable, BenchmarkChart, DividendHistory
- Backend test suite confirmed green at 103 passed, 7 skipped, 0 failures — no regressions from Phase 3 work
- All VIEW-02, VIEW-03, VIEW-04 requirements satisfied

## Task Commits

Each task was committed atomically:

1. **Task 1: Portfolio hooks and P&L table** - `93605d9` (feat)
2. **Task 2: Dividend history, benchmark chart, portfolio page assembly** - `f5f4138` (feat)
3. **Task 3: Backend test suite verification** - no commit (verification-only, 103 tests passed)

## Files Created/Modified

- `frontend/src/features/portfolio/hooks/usePositions.ts` — TanStack Query hook for GET /portfolio/positions, staleTime 60s
- `frontend/src/features/portfolio/hooks/usePnl.ts` — TanStack Query hook for GET /portfolio/pnl, staleTime 60s
- `frontend/src/features/portfolio/hooks/useDividends.ts` — TanStack Query hook for GET /portfolio/dividends, staleTime 5min
- `frontend/src/features/portfolio/hooks/useBenchmarks.ts` — TanStack Query hook for GET /portfolio/benchmarks, staleTime 5min
- `frontend/src/features/portfolio/components/PnlTable.tsx` — P&L table with PnlCell (green/red), stale price dash, tfoot totals row
- `frontend/src/features/portfolio/components/PositionsTable.tsx` — Current holdings chips with live prices
- `frontend/src/features/portfolio/components/DividendHistory.tsx` — Dividend table with yearFilter + classFilter useState, useMemo filtered rows, totalFiltered recalculation
- `frontend/src/features/portfolio/components/BenchmarkChart.tsx` — lightweight-charts v5 addSeries(AreaSeries) portfolio line; CDI/IBOVESPA as legend annotations
- `frontend/src/features/portfolio/components/PortfolioContent.tsx` — Client-side assembler for all 4 portfolio panels
- `frontend/app/portfolio/page.tsx` — /portfolio route page; server component wrapping PortfolioContent

## Decisions Made

- BenchmarkChart v1 approximation: portfolio timeseries is the only chart series; CDI and IBOVESPA are not historical series yet (no adapter for it) — shown as current rates in legend, footer note explains future intent clearly
- DividendHistory client-side filtering chosen over query-param refetch — lower latency, no extra server roundtrip for filter changes
- PnlCell handles null gracefully — when price cache is stale, null P&L renders as "—" not crash or zero

## Deviations from Plan

None - plan executed exactly as written. All tasks completed as specified in 03-03-PLAN.md. Tasks 1 and 2 were committed in a prior session; Task 3 verified in this session.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 complete — /dashboard and /portfolio both functional
- Checkpoint task (Task 4) requires human visual verification of /portfolio page at http://localhost:3000/portfolio
- Phase 4 (tax reporting) can begin once visual checkpoint is approved
- No blockers on Phase 4 from this plan

---
*Phase: 03-dashboard-core-ux*
*Completed: 2026-03-14*

## Self-Check: PASSED

Files verified:
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/hooks/usePositions.ts
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/hooks/usePnl.ts
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/hooks/useDividends.ts
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/hooks/useBenchmarks.ts
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/components/PnlTable.tsx
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/components/PositionsTable.tsx
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/components/DividendHistory.tsx
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/components/BenchmarkChart.tsx
- FOUND: D:/_DEV/claude-code/financas/frontend/src/features/portfolio/components/PortfolioContent.tsx
- FOUND: D:/_DEV/claude-code/financas/frontend/app/portfolio/page.tsx

Commits verified:
- FOUND: 93605d9 feat(03-03): portfolio hooks and P&L table
- FOUND: f5f4138 feat(03-03): dividend history, benchmark chart, portfolio page assembly

Build verified: npm run build exits 0, /portfolio route at 3.4 kB first load JS
Backend tests: 103 passed, 7 skipped, 0 failures
