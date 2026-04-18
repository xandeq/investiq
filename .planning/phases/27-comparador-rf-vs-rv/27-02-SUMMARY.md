---
phase: 27-comparador-rf-vs-rv
plan: "02"
subsystem: frontend
tags: [comparador, renda-fixa, client-side-calc, useMemo, IR-regressivo]
dependency_graph:
  requires: ["27-01"]
  provides: ["COMP-01"]
  affects: ["frontend/app/comparador"]
tech_stack:
  added: []
  patterns: [useMemo-client-calc, IR-regressivo-brackets, compound-annualize]
key_files:
  created:
    - frontend/src/features/comparador/hooks/useComparadorCalc.ts
  modified:
    - frontend/src/features/comparador/types.ts
    - frontend/src/features/comparador/components/ComparadorContent.tsx
  deleted:
    - frontend/src/features/comparador/api.ts
    - frontend/src/features/comparador/hooks/useComparador.ts
decisions:
  - "IR applied to gross annual rate (not compound return) — standard market tool approximation, precision <0.1%"
  - "ipcaNominalForReal = annualizeRate(ipca, days) — IPCA real-return denominator is compound IPCA over holding period, not raw annual rate"
  - "Benchmark rows (CDI/SELIC/IPCA) use same CDB IR bracket — apples-to-apples comparison per D-05"
  - "taxaPct null = use defaultTaxa; type change resets to null (triggers re-derive from catalog)"
metrics:
  duration: 254s
  completed: "2026-04-18"
  tasks_completed: 4
  files_changed: 5
---

# Phase 27 Plan 02: Comparador RF vs RV — Form + Table Summary

One-liner: Client-side comparador form + 4-row table with IR-regressivo brackets, LCI/LCA Isento badge, and Tesouro IPCA+ spread input — 100% useMemo, no API round-trip.

## What Was Built

### New Types (`frontend/src/features/comparador/types.ts`)

Replaced the v1.0-era `ComparadorRow` / `ComparadorResponse` / `PrazoLabel` with Phase 27 shapes:

- `TipoRF` union: `"CDB" | "LCI" | "LCA" | "TESOURO_SELIC" | "TESOURO_IPCA"`
- `ComparadorInputs`: valor, prazoMeses, tipoRF, taxaPct, spreadPct
- `ComparadorRow`: taxaBrutaAnualPct, taxaLiquidaAnualPct, isExempt, irRateAnualPct, retornoNominalPct, retornoRealPct, totalAcumuladoBRL
- `ProjectionPoint`: mes, produto_rf, cdi, selic, ipca (for Plan 03 chart)
- `ComparadorResult`: rows (4), projection (prazoMeses+1), ipcaAvailable

### New Hook (`frontend/src/features/comparador/hooks/useComparadorCalc.ts`)

Pure `useMemo` transform — no data fetching. Accepts `ComparadorInputs + MacroRatesResponse + FixedIncomeCatalogResponse`, returns `ComparadorResult`.

**IR Regressivo Brackets:**
- ≤ 180 days → 22.5%
- 181–360 days → 20%
- 361–720 days → 17.5%
- > 720 days → 15%
- LCI/LCA → 0% (isExempt)

**Default Rate Resolution (`getDefaultRateForTipo`):**
- CDB/LCI/LCA: catalog midpoint; if `indexer === "CDI"` → `(mid/100) * cdi` (absolute rate); otherwise raw midpoint
- Tesouro Selic: `macro.selic` (14.75 fallback)
- Tesouro IPCA+: 0 (spread field drives the rate)
- Fallback when no catalog row: `macro.cdi` or 10

**TESOURO_IPCA gross rate:** `macro.ipca + spreadPct` (spread is user-editable, default 5.5)

**Projection:** Month 0..prazoMeses compound using monthly-compounded net rate per series.

### Rewritten Component (`frontend/src/features/comparador/components/ComparadorContent.tsx`)

- `"use client"` — named export `ComparadorContent` (unchanged import path in `page.tsx`)
- Form: valor (R$), prazo (meses), tipo RF dropdown (5 options), taxa (% a.a., editable, shows default hint), spread (% a.a., conditional on TESOURO_IPCA)
- Type change in dropdown resets `taxaPct` to `null` (triggers re-derive from catalog)
- Loading skeleton while `loadingMacro || loadingCatalog`
- Comparison table in `overflow-x-auto` wrapper with 6 columns
- IRBadge: green "Isento" for LCI/LCA, gray `{irPct}%` otherwise
- Retorno Nominal highlighted green when > CDI row (beats benchmark)
- Retorno Real shows "—" with tooltip when IPCA unavailable
- CVM Res. 19/2021 disclaimer banner
- `{/* Plan 03 will render the chart here using result.projection */}` placeholder

### Deleted (stale v1.0 code)

- `frontend/src/features/comparador/api.ts` — called `/comparador/compare` (unused)
- `frontend/src/features/comparador/hooks/useComparador.ts` — depended on deleted api

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Enhancement] Added ipcaNominalForReal for compound real return**
- **Found during:** Task 2 implementation
- **Issue:** The plan's pseudocode passed raw `ipca` annual rate as the real-return denominator. Using the raw annual rate for Retorno Real would be incorrect for multi-year scenarios — the denominator should be the compound IPCA over the holding period.
- **Fix:** Added `ipcaNominalForReal = annualizeRate(ipca, days)` before building rows; passed this as the denominator instead of raw `ipca`.
- **Files modified:** `frontend/src/features/comparador/hooks/useComparadorCalc.ts`

None other — plan executed as written.

## Known Stubs

None. The new ComparadorContent reads live data from `useMacroRates()` and `useFixedIncomeCatalog()` which are populated by the backend Redis cache (BCB pipeline, 6h TTL). The `projection` array is computed but not yet rendered (intentional — Plan 03 will add the chart).

## Open Decisions (deferred to Plan 03)

- Chart line colors per series (produto_rf / CDI / SELIC / IPCA+)
- Chart Y-axis label formatting (R$ absolute vs % return)
- Chart hover tooltip format

## Self-Check: PASSED

- `frontend/src/features/comparador/types.ts` — exists with TipoRF, ComparadorInputs, ComparadorRow, ComparadorResult
- `frontend/src/features/comparador/hooks/useComparadorCalc.ts` — exists with useComparadorCalc + getDefaultRateForTipo
- `frontend/src/features/comparador/components/ComparadorContent.tsx` — exists with form + table
- `frontend/src/features/comparador/api.ts` — deleted
- `frontend/src/features/comparador/hooks/useComparador.ts` — deleted
- Commits: 18c0a13 (types), 3fe3173 (hook), 6e4b024 (component), d1cf4ea (cleanup)
- `npx tsc --noEmit` — zero errors
- `npx next build` — succeeded
