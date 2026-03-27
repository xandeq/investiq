---
phase: 03-dashboard-core-ux
plan: 01
subsystem: ui
tags: [tanstack-query, react-query, lightweight-charts, recharts, shadcn, typescript, api-types]

requires:
  - phase: 02-portfolio-engine-market-data
    provides: portfolio backend endpoints (positions, pnl, dividends, benchmarks) and Python schemas that TypeScript types mirror
  - phase: 01-foundation
    provides: api-client.ts with credentials:include cookie auth pattern; Next.js App Router layout structure

provides:
  - QueryClientProvider singleton wrapping entire Next.js app via root layout
  - Typed TypeScript API functions for 5 endpoints: getDashboardSummary, getPositions, getPnl, getDividends, getBenchmarks
  - DashboardSummary, PositionResponse, PnLResponse, DividendResponse, BenchmarkResponse TypeScript interfaces
  - formatBRL, formatPct, formatDate utility functions in src/lib/formatters.ts
  - shadcn chart component (Recharts-based, React 19 compatible) at src/components/ui/chart.tsx
  - Wave 0 failing test stubs for dashboard endpoint (7 tests, all 404 until Plan 03-02)

affects:
  - 03-02 (dashboard backend endpoint — will make Wave 0 tests green)
  - 03-03 (dashboard UI components — will import getDashboardSummary and DashboardSummary types)
  - 03-04 (portfolio feature — will import getPositions, getPnl, getDividends, getBenchmarks and portfolio types)
  - all Phase 3 plans (QueryProvider required for useQuery hooks)

tech-stack:
  added:
    - "@tanstack/react-query ^5.x"
    - "@tanstack/react-query-devtools ^5.x (devDependency)"
    - "lightweight-charts ^5.x"
    - "recharts (via shadcn chart)"
  patterns:
    - "QueryProvider uses useState(() => new QueryClient()) pattern — singleton per component tree, no module-scope client"
    - "All monetary TypeScript types use string (not number) — matches Pydantic v2 Decimal JSON serialization"
    - "Feature-based directory structure: src/features/{name}/types.ts + api.ts"
    - "Wave 0 test stubs: write tests against endpoints before implementing them (TDD at integration level)"

key-files:
  created:
    - "frontend/src/providers/query-provider.tsx — QueryClientProvider with ReactQueryDevtools in dev"
    - "frontend/src/features/dashboard/types.ts — DashboardSummary, AllocationItem, TimeseriesPoint, RecentTransaction"
    - "frontend/src/features/dashboard/api.ts — getDashboardSummary()"
    - "frontend/src/features/portfolio/types.ts — PositionResponse, PnLResponse, DividendResponse, BenchmarkResponse, AllocationItem"
    - "frontend/src/features/portfolio/api.ts — getPositions, getPnl, getDividends, getBenchmarks"
    - "frontend/src/lib/formatters.ts — formatBRL, formatPct, formatDate"
    - "frontend/src/lib/utils.ts — cn() helper for shadcn components"
    - "frontend/src/components/ui/chart.tsx — shadcn chart (Recharts-based)"
    - "frontend/src/components/ui/card.tsx — shadcn card"
    - "backend/tests/test_dashboard_api.py — 7 Wave 0 failing test stubs"
  modified:
    - "frontend/app/layout.tsx — wrapped body children with QueryProvider"
    - "frontend/package.json — added @tanstack/react-query, lightweight-charts deps"
    - "frontend/app/(auth)/reset-password/page.tsx — Suspense boundary fix for useSearchParams"
    - "frontend/app/(auth)/verify-email/page.tsx — Suspense boundary fix for useSearchParams"

key-decisions:
  - "Use useState(() => new QueryClient()) pattern — prevents cache discard on re-render if client created at module scope"
  - "All monetary TypeScript types use string — mirrors Pydantic v2 Decimal to JSON string serialization; parseFloat only at display layer"
  - "Wave 0 tests fail with 404 not xfail/skip — this documents the missing endpoint state clearly and turns green when 03-02 ships"
  - "No @tremor/react — React 19 incompatible; use shadcn Chart (Recharts-based) per plan constraint"

patterns-established:
  - "Feature API modules: src/features/{name}/api.ts imports apiClient and re-exports typed async functions"
  - "Feature types: src/features/{name}/types.ts mirrors backend Pydantic schemas with string monetaries"
  - "Suspense boundary wrapping: any page using useSearchParams must wrap the hook-using component in Suspense"

requirements-completed: [VIEW-01, VIEW-02, VIEW-03, VIEW-04]

duration: 11min
completed: 2026-03-14
---

# Phase 3 Plan 01: Frontend Foundation Summary

**TanStack Query v5 provider wired to Next.js root layout, typed API contracts for all 5 dashboard/portfolio endpoints, and Wave 0 failing test stubs establishing the dashboard integration test suite.**

## Performance

- **Duration:** 11 min
- **Started:** 2026-03-14T18:15:39Z
- **Completed:** 2026-03-14T18:26:44Z
- **Tasks:** 3
- **Files modified:** 14

## Accomplishments
- Installed @tanstack/react-query, lightweight-charts, shadcn chart; QueryProvider wraps entire Next.js app with staleTime=60s, gcTime=5m, retry=1 QueryClient
- Created 4 TypeScript feature files (dashboard/types.ts, dashboard/api.ts, portfolio/types.ts, portfolio/api.ts) with all monetary fields typed as `string`
- Wave 0 test file with 7 integration stubs for /dashboard/summary — fails 404 now, turns green in Plan 03-02
- Auto-fixed 3 pre-existing bugs: missing utils.ts (cn helper required by shadcn), missing Suspense boundaries on reset-password and verify-email pages

## Task Commits

Each task was committed atomically:

1. **Task 1: Install deps, add shadcn chart, create QueryProvider, wire app layout** - `c5a03d9` (feat)
2. **Task 2: Create typed API functions and TypeScript types for all dashboard + portfolio endpoints** - `57658d0` (feat)
3. **Task 3: Wave 0 — Create failing test stubs for dashboard endpoint** - `8ac60bb` (test)

## Files Created/Modified
- `frontend/src/providers/query-provider.tsx` — QueryClientProvider singleton using useState factory pattern with ReactQueryDevtools in dev
- `frontend/src/features/dashboard/types.ts` — DashboardSummary, AllocationItem, TimeseriesPoint, RecentTransaction (all monetary fields: string)
- `frontend/src/features/dashboard/api.ts` — getDashboardSummary() calling /dashboard/summary
- `frontend/src/features/portfolio/types.ts` — PositionResponse, PnLResponse, DividendResponse, BenchmarkResponse, AllocationItem
- `frontend/src/features/portfolio/api.ts` — getPositions, getPnl, getDividends, getBenchmarks
- `frontend/src/lib/formatters.ts` — formatBRL (pt-BR currency), formatPct, formatDate utilities
- `frontend/src/lib/utils.ts` — cn() combining clsx + tailwind-merge (required by shadcn)
- `frontend/src/components/ui/chart.tsx` — shadcn chart (Recharts wrapper, React 19 compatible)
- `frontend/src/components/ui/card.tsx` — shadcn card component
- `frontend/app/layout.tsx` — body now wrapped with QueryProvider
- `frontend/package.json` — @tanstack/react-query, lightweight-charts added
- `backend/tests/test_dashboard_api.py` — 7 Wave 0 test stubs (all fail 404 until Plan 03-02)
- `frontend/app/(auth)/reset-password/page.tsx` — Suspense boundary fix
- `frontend/app/(auth)/verify-email/page.tsx` — Suspense boundary fix

## Decisions Made
- Used `useState(() => new QueryClient(...))` not module-scope client — prevents infinite refetch from cache discard on re-renders
- All monetary TypeScript types are `string` — Pydantic v2 serializes Decimal as JSON strings; `parseFloat()` only at the display formatting layer in formatters.ts
- Wave 0 tests fail with real 404 (not xfail/skip) — this creates unambiguous pass/fail signal when the endpoint ships in 03-02

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created missing src/lib/utils.ts required by shadcn components**
- **Found during:** Task 1 (npm run build after shadcn chart install)
- **Issue:** `npx shadcn add chart` generated card.tsx and chart.tsx both importing `@/lib/utils` which did not exist
- **Fix:** Created `frontend/src/lib/utils.ts` with `cn()` helper using clsx + tailwind-merge (standard shadcn utility)
- **Files modified:** frontend/src/lib/utils.ts (created)
- **Verification:** Build succeeds after creation
- **Committed in:** c5a03d9 (Task 1 commit)

**2. [Rule 1 - Bug] Fixed missing Suspense boundary on reset-password page**
- **Found during:** Task 1 (npm run build — prerender error)
- **Issue:** `useSearchParams()` in reset-password/page.tsx without Suspense boundary — Next.js build fails at static generation step
- **Fix:** Extracted component using `useSearchParams` into `ResetPasswordForm`, wrapped in `<Suspense>` in the default export
- **Files modified:** frontend/app/(auth)/reset-password/page.tsx
- **Verification:** Build succeeds, page prerendered successfully
- **Committed in:** c5a03d9 (Task 1 commit)

**3. [Rule 1 - Bug] Fixed missing Suspense boundary on verify-email page**
- **Found during:** Task 1 (second npm run build iteration)
- **Issue:** Same `useSearchParams()` without Suspense boundary issue in verify-email/page.tsx
- **Fix:** Extracted `VerifyEmailContent` component, wrapped in `<Suspense>` in the default export
- **Files modified:** frontend/app/(auth)/verify-email/page.tsx
- **Verification:** Build succeeds, all 9 pages prerender cleanly
- **Committed in:** c5a03d9 (Task 1 commit)

---

**Total deviations:** 3 auto-fixed (1 blocking, 2 bug)
**Impact on plan:** All auto-fixes necessary for build to pass. Suspense boundary issues are pre-existing bugs unrelated to this plan's scope but blocking verification. utils.ts is a required dependency of shadcn which was installed as part of this plan.

## Issues Encountered
None beyond the auto-fixed deviations above.

## Next Phase Readiness
- Plan 03-02 can now implement the dashboard backend endpoint and make 7 Wave 0 tests green
- Plan 03-03 can import `getDashboardSummary` and `DashboardSummary` to build dashboard UI components with `useQuery`
- Plan 03-04 can import all 4 portfolio API functions and types for portfolio feature pages
- All Phase 3 plans can use `useQuery`, `useMutation` hooks — QueryProvider is live in the root layout

---
*Phase: 03-dashboard-core-ux*
*Completed: 2026-03-14*
