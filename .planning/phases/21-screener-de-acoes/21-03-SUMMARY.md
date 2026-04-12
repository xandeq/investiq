---
phase: 21-screener-de-acoes
plan: "03"
subsystem: frontend
tags: [screener, acoes, client-side-filtering, react-query, useMemo, pagination]
dependency_graph:
  requires:
    - "21-02 (backend /screener/universe endpoint)"
  provides:
    - "/acoes/screener page route"
    - "AcoesUniverseContent component"
    - "acoes_screener feature directory"
  affects:
    - "frontend navigation (link to /acoes/screener)"
tech_stack:
  added: []
  patterns:
    - "client-side useMemo filter+sort (same as Phase 17 FII Screener)"
    - "React Query with 1h staleTime for nightly snapshot data"
    - "Next.js App Router page.tsx pattern with AppNav + max-w-7xl"
key_files:
  created:
    - frontend/src/features/acoes_screener/types.ts
    - frontend/src/features/acoes_screener/api.ts
    - frontend/src/features/acoes_screener/hooks/useAcoesUniverse.ts
    - frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx
    - frontend/app/acoes/screener/page.tsx
  modified: []
decisions:
  - "Reused apiClient from @/lib/api-client (same pattern as fii_screener and screener_v2)"
  - "Sector dropdown dynamically built from data.results via useMemo (not hardcoded)"
  - "Market cap tier buttons toggle: clicking active tier deselects it"
  - "Null values sorted to end in all sort directions"
  - "Page reset to 0 on every filter/sort change (setPage(0) in each onChange handler)"
metrics:
  duration: "197s"
  completed: "2026-04-12T14:38:47Z"
  tasks_completed: 2
  files_created: 5
  files_modified: 0
---

# Phase 21 Plan 03: Acoes Screener Frontend Summary

Acoes screener frontend with client-side filtering (DY min, P/L max, Setor dropdown, Market Cap tier buttons), sortable columns, and 50-row pagination at `/acoes/screener`.

## Tasks Completed

| # | Task | Commit | Files |
|---|------|--------|-------|
| 1 | Feature directory scaffolding — types, api, hook | e58cd64 | types.ts, api.ts, hooks/useAcoesUniverse.ts |
| 2 | AcoesUniverseContent component + page route | df0d24c | components/AcoesUniverseContent.tsx, app/acoes/screener/page.tsx |

## What Was Built

**`frontend/src/features/acoes_screener/types.ts`**
- `AcoesUniverseRow`: 8 fields (ticker, short_name, sector, regular_market_price, variacao_12m_pct, dy, pl, market_cap)
- `AcoesUniverseResponse`: disclaimer + results array

**`frontend/src/features/acoes_screener/api.ts`**
- `getAcoesUniverse()`: calls `/screener/universe` via `apiClient`

**`frontend/src/features/acoes_screener/hooks/useAcoesUniverse.ts`**
- `useAcoesUniverse()`: React Query hook, `staleTime: 1h`, queryKey `["acoes-universe"]`

**`frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx`** (460 lines)
- Client-side filtering: DY min (input), P/L max (input), Setor (dropdown from useMemo), Market Cap (small/mid/large toggle buttons)
- Filter thresholds: Small < R$2B, Mid R$2B–10B, Large > R$10B
- useMemo pipeline: filter first, then sort — DY stored as decimal multiplied by 100 for comparison
- Sortable column headers: click toggles asc/desc, active column shows arrow indicator
- Pagination: PAGE_SIZE=50, prev/next buttons, page resets on filter/sort change
- Ticker column: `<Link href="/stock/[ticker]">` with font-mono + short_name below
- DY formatted as `parseFloat(row.dy) * 100` % (decimal convention)
- Var. 12m%: `changeBadge()` with `parseFloat(row.variacao_12m_pct) * 100`
- Skeleton loading (8 rows x 7 cols animate-pulse), empty state, error state
- Utility functions: `fmtBRL`, `changeBadge`, `fmt` (copied from screener_v2 pattern)

**`frontend/app/acoes/screener/page.tsx`**
- Next.js App Router page at `/acoes/screener`
- AppNav + max-w-7xl container + heading "Screener de Acoes"
- Metadata for SEO

## Verification

- `npm run build` exits 0 (static route `/acoes/screener` appears in build output)
- All 5 files exist
- useMemo present (3 usages)
- PAGE_SIZE = 50
- Link to /stock/[ticker] present
- Market cap thresholds 2_000_000_000 and 10_000_000_000 present

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — AcoesUniverseContent is fully wired to useAcoesUniverse hook which calls the real `/screener/universe` API endpoint built in Plan 02. No hardcoded empty values or placeholder data.

## Self-Check: PASSED
