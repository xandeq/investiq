---
phase: 17-fii-screener-table
plan: "02"
subsystem: frontend
tags: [fii, screener, react-query, next-js, client-filtering]
dependency_graph:
  requires: ["17-01"]
  provides: ["/fii/screener page", "FIIScoredScreenerContent component", "useFIIScoredScreener hook"]
  affects: ["frontend/app/fii/screener/page.tsx", "frontend/src/components/AppNav.tsx"]
tech_stack:
  added: []
  patterns: ["client-side filtering with useMemo", "React Query with 1h staleTime", "static Next.js App Router route"]
key_files:
  created:
    - frontend/src/features/fii_screener/types.ts
    - frontend/src/features/fii_screener/api.ts
    - frontend/src/features/fii_screener/hooks/useFIIScreener.ts
    - frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx
    - frontend/app/fii/screener/page.tsx
  modified:
    - frontend/src/components/AppNav.tsx
decisions:
  - "Page created at frontend/app/fii/screener/ (not frontend/src/app/) — Next.js App Router uses frontend/app/ as appDir, not src/app/"
  - "Client-side filtering with useMemo avoids API roundtrips — ~400 FIIs fits comfortably in browser memory"
  - "Score column shows numeric value (0-100 with 1 decimal) — dy_12m converted from decimal to % in display"
metrics:
  duration: "12m"
  completed_date: "2026-04-04"
  tasks_completed: 2
  files_created: 5
  files_modified: 1
---

# Phase 17 Plan 02: FII Scored Screener Frontend Summary

Frontend screener table for ranked FIIs with client-side segment and DY filters, built on React Query with 1h stale time and instant useMemo filtering.

## What Was Built

- **types.ts** — `FIIScoredRow` and `FIIScoredResponse` TypeScript interfaces matching backend schemas from Plan 01
- **api.ts** — `getFIIScreenerRanked()` client function calling `GET /fii-screener/ranked`
- **hooks/useFIIScreener.ts** — `useFIIScoredScreener` React Query hook with `queryKey: ["fii-screener-ranked"]` and 1h staleTime (data refreshed nightly)
- **FIIScoredScreenerContent.tsx** — Full screener table component:
  - Columns: Rank (#), Ticker (link to /fii/[ticker]), Segmento (colored badge), DY 12m (decimal→%), P/VP, Liquidez (R$ formatted), Score
  - Segment dropdown filter with 12 CVM segments
  - DY minimum input filter
  - Clear filters button
  - Loading skeleton (8 rows × 7 cols animated pulse)
  - Error banner, empty state, score-not-available yellow banner
  - CVM disclaimer at bottom
- **app/fii/screener/page.tsx** — Static Next.js App Router page with AppNav + page title
- **AppNav.tsx** — Added "FII Screener" link under Mercado group; added `/fii` to `activePrefixes`

## Verification

- `npx tsc --noEmit` — zero errors in new files (pre-existing unrelated error in WatchlistContent.tsx)
- `npm run build` — `/fii/screener` appears as static route (`○`) in build output
- All 6 files exist at correct paths

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Page created in wrong directory**
- **Found during:** Task 2 — build verification
- **Issue:** Plan specified `frontend/src/app/fii/screener/page.tsx` but Next.js App Router uses `frontend/app/` as the app directory (not `frontend/src/app/`)
- **Fix:** Created page at `frontend/app/fii/screener/page.tsx`. Also added AppNav import since existing screener pages follow that pattern.
- **Files modified:** `frontend/app/fii/screener/page.tsx` (created at correct path)
- **Commit:** 74fcb29

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| Task 1 | c929b3a | feat(17-02): FII scored screener types, API client, hook, and table component |
| Task 2 | 74fcb29 | feat(17-02): /fii/screener page route and AppNav FII Screener link |

## Known Stubs

None — all components wire to real API data from `/fii-screener/ranked`. Score-not-available state is handled gracefully.

## Self-Check: PASSED
