---
phase: 19-opportunity-detector-page
plan: 02
subsystem: frontend
tags: [nextjs, react, react-query, typescript, tailwind, playwright]

# Dependency graph
requires:
  - phase: 19-opportunity-detector-page
    plan: 01
    provides: "GET /opportunity-detector/history and PATCH /{id}/follow API endpoints"
provides:
  - "/opportunity-detector page protected by auth middleware"
  - "OpportunityDetectorContent client component with filters, table, risk badges, follow buttons"
  - "useOpportunityHistory React Query hook with filter-aware cache"
  - "getOpportunityHistory + markAsFollowed API client functions"
  - "TypeScript types OpportunityRow + OpportunityHistoryResponse"
  - "Playwright e2e stubs for future implementation"
affects:
  - "Frontend auth coverage: /fii and /opportunity-detector now in PROTECTED_PATHS"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "useMutation with queryClient.invalidateQueries for optimistic-adjacent follow toggle"
    - "Expandable table rows via expandedId state toggling"
    - "Filter-aware React Query key: ['opportunity-history', filters] triggers refetch on filter change"
    - "renda_fixa PITFALL 5: show cause_explanation instead of drop_pct in Queda column"

key-files:
  created:
    - frontend/e2e/opportunity-detector.spec.ts
    - frontend/src/features/opportunity_detector/types.ts
    - frontend/src/features/opportunity_detector/api.ts
    - frontend/src/features/opportunity_detector/hooks/useOpportunityHistory.ts
    - frontend/src/features/opportunity_detector/components/OpportunityDetectorContent.tsx
    - frontend/app/opportunity-detector/page.tsx
  modified:
    - frontend/middleware.ts

key-decisions:
  - "Both /fii and /opportunity-detector added to PROTECTED_PATHS — /fii was previously missing per RESEARCH.md Section 5"
  - "Filters passed to API (server-side) not useMemo (client-side) — opportunities dataset can grow unbounded unlike FII screener"
  - "expandedId tracks single expanded row to avoid DOM clutter with multiple open rows simultaneously"
  - "renda_fixa drop_pct column shows cause_explanation (a rate change, not a price drop) per RESEARCH.md PITFALL 5"

# Metrics
duration: ~30min
completed: 2026-04-05
---

# Phase 19 Plan 02: Opportunity Detector Frontend Summary

**Next.js page at /opportunity-detector with filter bar, sortable table, risk badges, follow toggle, and expandable detail rows — wired to the Plan 19-01 backend API**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-04-05T01:16:16Z
- **Completed:** 2026-04-05T08:43:29Z
- **Tasks:** 7 (Task 0 through Task 6)
- **Files modified/created:** 7

## Accomplishments

- `/opportunity-detector` page rendered as Next.js server component, delegating interactivity to `OpportunityDetectorContent`
- Filter bar: asset type (Todos / Ações / Crypto / Renda Fixa) and period (7 / 30 / 90 / 365 dias) — both wired to API query params
- Risk badges color-coded by level: baixo=green, medio=yellow, alto=red, evitar=black
- Follow toggle via `useMutation` PATCH call with automatic cache invalidation on success
- Expandable rows display cause_explanation, risk_rationale, telegram_message (in mono code block), recommended_amount_brl, target_upside_pct
- Renda fixa rows show `cause_explanation` in the Queda column instead of a meaningless drop% (PITFALL 5 from RESEARCH.md)
- `/fii` and `/opportunity-detector` now both protected by auth middleware
- Next.js build passes cleanly — page appears at 4.62 kB First Load JS
- Playwright e2e stubs created for 4 future tests

## Task Commits

| Task | Name | Commit |
|------|------|--------|
| 0 | Playwright e2e stub | `e4e3b98` |
| 1 | Middleware PROTECTED_PATHS | `9bdcdfb` |
| 2 | TypeScript types | `088b424` |
| 3 | API client functions | `cb515c4` |
| 4 | React Query hook | `510dbf7` |
| 5 | OpportunityDetectorContent component | `011d44a` |
| 6 | Page shell at /opportunity-detector | `591624f` |

## Files Created/Modified

- `frontend/e2e/opportunity-detector.spec.ts` — 4 skipped Playwright tests (stub for future implementation)
- `frontend/middleware.ts` — Added `/fii` and `/opportunity-detector` to PROTECTED_PATHS
- `frontend/src/features/opportunity_detector/types.ts` — OpportunityRow (17 fields) + OpportunityHistoryResponse
- `frontend/src/features/opportunity_detector/api.ts` — getOpportunityHistory + markAsFollowed using apiClient
- `frontend/src/features/opportunity_detector/hooks/useOpportunityHistory.ts` — useQuery with filter-aware key
- `frontend/src/features/opportunity_detector/components/OpportunityDetectorContent.tsx` — Full client component (filters, table, badges, mutation, expandable rows)
- `frontend/app/opportunity-detector/page.tsx` — Server component page shell with metadata

## Decisions Made

- Server-side filtering (API params) instead of client-side useMemo: opportunities dataset can grow without bound (new detections added every scan), unlike FII screener which is capped at ~400 tickers
- Single expandedId state (not Set) intentionally: only one row expanded at a time reduces visual clutter when reviewing opportunities with long telegram_message fields
- `/fii` added to PROTECTED_PATHS alongside `/opportunity-detector` since RESEARCH.md Section 5 flagged it as missing

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

- `frontend/e2e/opportunity-detector.spec.ts` — 4 tests are `test.skip` stubs. These are intentional placeholder tests documented in the plan; they will be implemented in a future E2E hardening phase.

## Self-Check: PASSED
