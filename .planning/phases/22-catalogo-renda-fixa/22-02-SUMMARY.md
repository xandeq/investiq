---
phase: 22-catalogo-renda-fixa
plan: 02
subsystem: frontend
tags: [renda-fixa, filters, useMemo, beat-indicator, react-query]
dependency_graph:
  requires: ["22-01"]
  provides: ["RF-01", "RF-02", "RF-03"]
  affects: ["frontend/src/features/screener_v2/"]
tech_stack:
  added: []
  patterns: ["client-side useMemo filtering", "compound return math in JS", "beat indicator with no-flash guard"]
key_files:
  created: []
  modified:
    - "frontend/src/features/screener_v2/types.ts"
    - "frontend/src/features/screener_v2/api.ts"
    - "frontend/src/features/screener_v2/hooks/useRendaFixa.ts"
    - "frontend/src/features/screener_v2/components/RendaFixaContent.tsx"
decisions:
  - "annualizeRate uses compound math (1+r)^(d/365)-1, matching Python backend formula exactly"
  - "Beat indicator only renders when macroRates is loaded — no-flash guard via conditional on cdiForPeriod/ipcaForPeriod"
  - "typeFilter===Tesouro hides prazo/sort controls since Tesouro section has no IRBreakdown-based filtering"
  - "useMacroRates staleTime 1h (3600s) since CDI/IPCA rates rarely change intraday"
metrics:
  duration: "~4m"
  completed: "2026-04-12T19:34:33Z"
  tasks_completed: 2
  files_changed: 4
---

# Phase 22 Plan 02: Renda Fixa Filters + Sort + Beat Indicator Summary

**One-liner:** Client-side type toggle, prazo minimo filter, net-return sort, and CDI/IPCA beat indicator added to RendaFixaContent.tsx using useMemo pipeline and useMacroRates hook.

## What Was Built

### Task 1: MacroRates type, API, and hook

Added `MacroRatesResponse` interface to `types.ts` with `cdi: string | null` and `ipca: string | null`. Added `getMacroRates()` to `api.ts` calling `GET /renda-fixa/macro-rates` (endpoint created in Plan 01). Added `useMacroRates()` hook to `useRendaFixa.ts` with 1-hour staleTime.

**Commit:** `51a2a0c`

### Task 2: Filters, sort, and beat indicator in RendaFixaContent.tsx

Modified `RendaFixaContent.tsx` with:

1. **Type filter state** — `typeFilter` (`"" | "Tesouro" | "CDB" | "LCI" | "LCA"`), `minMonths`, `selectedPrazo` (`"6m" | "1a" | "2a" | "5a"`), `sortDir`
2. **Filter bar UI** — Type toggle buttons (Todos/Tesouro/CDB/LCI/LCA), prazo minimo input, prazo sort buttons with asc/desc toggle, result count
3. **useMemo filteredCatalog** — Type filter → min_months filter → sort by net_pct for selectedPrazo
4. **Section visibility** — Tesouro section shown when typeFilter is `""` or `"Tesouro"`; CDB/LCI/LCA section shown when typeFilter is not `"Tesouro"`
5. **annualizeRate helper** — `((1 + annualPct/100)^(holdingDays/365) - 1) * 100` — matches Python backend exactly
6. **Beat indicator** — Per cell in CatalogRow: green "✓ CDI" if beats CDI, amber "~ IPCA" if beats only IPCA, gray "— abaixo" if neither. No indicator renders when macroRates is not yet loaded (no-flash guard)
7. **Empty state** — Shown when filters produce 0 results but catalog has data

**Commit:** `f860152`

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| annualizeRate in JS using compound math | Replicates Python `_compound_return()` formula exactly — same (1+r)^(d/365)-1 |
| Beat indicator gated on `cdiForPeriod !== null` | macroRates undefined during load → no flash of wrong colors (per Pitfall 3) |
| Prazo/sort controls hidden when typeFilter==="Tesouro" | Tesouro section has no ir_breakdowns structure — controls irrelevant |
| useMemo deps include all 4 filter/sort state vars | Ensures recompute on any filter change without unnecessary API calls |

## Acceptance Criteria Verification

- [x] `types.ts` contains `export interface MacroRatesResponse` with `cdi/ipca: string | null`
- [x] `api.ts` contains `getMacroRates()` calling `apiClient<MacroRatesResponse>("/renda-fixa/macro-rates")`
- [x] `useRendaFixa.ts` contains `useMacroRates()` with `staleTime: 60 * 60_000` and `queryKey: ["renda-fixa", "macro-rates"]`
- [x] `RendaFixaContent.tsx` imports `useState, useMemo`
- [x] `RendaFixaContent.tsx` imports and calls `useMacroRates`
- [x] `RendaFixaContent.tsx` has `useState<InstrumentType>("")` typeFilter state
- [x] `RendaFixaContent.tsx` has `useState("")` minMonths state
- [x] `RendaFixaContent.tsx` has `useState<"6m" | "1a" | "2a" | "5a">("1a")` selectedPrazo
- [x] `RendaFixaContent.tsx` has `useMemo` with `typeFilter, minMonths, selectedPrazo, sortDir` deps
- [x] Toggle buttons: "Todos", "Tesouro", "CDB", "LCI", "LCA" all present
- [x] `annualizeRate` function present
- [x] `beatsCDI` and `beatsIPCA` variables present
- [x] Beat indicator: green "CDI" for beats CDI, amber "IPCA" for beats IPCA only
- [x] `filteredCatalog.map` used (not raw catalog)
- [x] No `90d` period label
- [x] `IRBadge` component unchanged
- [x] TypeScript compilation: 0 new errors (1 pre-existing error in WatchlistContent.tsx unrelated to our changes)

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — all filters wire to real data from `useFixedIncomeCatalog()` and beat indicator wires to real `useMacroRates()` data from the `/renda-fixa/macro-rates` endpoint built in Plan 01.

## Self-Check: PASSED
