---
phase: 28-simulador-de-alocacao
plan: "01"
subsystem: frontend/simulador
tags: [simulador, client-side-calc, types, hooks, ir-regressivo, phase-28]
dependency_graph:
  requires:
    - "frontend/src/features/screener_v2/types.ts (MacroRatesResponse)"
  provides:
    - "frontend/src/features/simulador/types.ts — Phase 28 simulador types"
    - "frontend/src/features/simulador/hooks/useSimuladorCalc.ts — 3-scenario projection hook"
  affects:
    - "frontend/src/features/simulador/components/SimuladorContent.tsx (Plan 02 will rewrite)"
    - "frontend/app/simulador/page.tsx (Plan 02 consumer)"
tech_stack:
  added: []
  patterns:
    - "Pure useMemo hook pattern (mirrors useComparadorCalc from Phase 27)"
    - "Feature-isolated IR helpers (re-declared, not imported from comparador)"
    - "Tuple typing for fixed-length scenarios array"
key_files:
  created:
    - frontend/src/features/simulador/hooks/useSimuladorCalc.ts
  modified:
    - frontend/src/features/simulador/types.ts
    - frontend/src/features/simulador/api.ts
    - frontend/src/features/simulador/hooks/useSimulador.ts
    - frontend/src/features/simulador/components/SimuladorContent.tsx
decisions:
  - "Re-declared IR helpers (irRatePctByDays, annualizeRate, netAnnualRate) inside useSimuladorCalc rather than importing from useComparadorCalc — keeps simulador feature self-contained (D-12 precedent from Phase 27)"
  - "Ações: 12% a.a. gross, no IR — IBOV historical annualized nominal, PF holding >1y simplification"
  - "FIIs: 8% a.a. gross, no IR — DY médio proxy, PF isento em rendimentos de FII"
  - "macro?.cdi is the ONLY macro field consumed — IPCA and SELIC deliberately NOT dependencies (Phase 28 does not use them)"
  - "SimuladorContent.tsx stubbed (returns null) because v1.0 content used deleted types — Plan 02 will fully rewrite"
metrics:
  duration: "~4 minutes"
  completed: "2026-04-19"
  tasks_completed: 2
  files_created: 1
  files_modified: 4
---

# Phase 28 Plan 01: useSimuladorCalc Hook + Phase 28 Types Summary

**One-liner:** Phase 28 simulador types (9 exports) + pure client-side `useSimuladorCalc` hook computing 3 allocation scenarios (conservador/moderado/arrojado) with IR regressivo for RF and fixed proxy rates for ações/FIIs.

## What Was Built

### Types (`frontend/src/features/simulador/types.ts`)

Replaced v1.0-era types (pessimista/base/otimista + caixa shape) with 9 Phase 28 exports:

| Export | Kind | Purpose |
|--------|------|---------|
| `ScenarioKey` | type | `"conservador" \| "moderado" \| "arrojado"` |
| `ScenarioAllocation` | interface | `{ rf_pct, acoes_pct, fiis_pct }` — percentages |
| `SimuladorInputs` | interface | `{ valor, prazoMeses }` — form inputs |
| `ClassProjection` | interface | Per-class projection with IR, rates, and BRL values |
| `ScenarioResult` | interface | Full scenario: allocation + rf/acoes/fiis + totals |
| `SimuladorResult` | interface | `{ scenarios[3], holdingDays, cdiUsed }` |
| `SCENARIO_ALLOCATIONS` | const | Hardcoded record: conservador 80/10/10, moderado 50/35/15, arrojado 20/65/15 |
| `ACOES_GROSS_ANNUAL_PCT` | const | `12` — IBOV proxy |
| `FIIS_GROSS_ANNUAL_PCT` | const | `8` — FII DY proxy |

### Hook (`frontend/src/features/simulador/hooks/useSimuladorCalc.ts`)

```typescript
export function useSimuladorCalc(
  inputs: SimuladorInputs,
  macro: MacroRatesResponse | undefined,
): SimuladorResult
```

- Returns `SimuladorResult` with 3 scenarios typed as exact-length tuple
- RF projection: CDI (from macro) × IR regressivo brackets (22.5/20/17.5/15 by holding days)
- Ações projection: 12% a.a. gross, isExempt=true (no IR)
- FIIs projection: 8% a.a. gross, isExempt=true (no IR)
- Defensive: `macro?.cdi` null/undefined → `cdiUsed = 0`, hook still returns 3 well-formed scenarios
- `useMemo` deps: `[inputs.valor, inputs.prazoMeses, macro?.cdi]` — IPCA/SELIC not needed

### Stale Files Neutralized

| File | Action | Reason |
|------|--------|--------|
| `frontend/src/features/simulador/api.ts` | Emptied to `export {}` | Was calling `/simulador/simulate` (non-existent endpoint); Phase 28 is client-side |
| `frontend/src/features/simulador/hooks/useSimulador.ts` | Emptied to `export {}` | Was useQuery wrapper for deleted endpoint |
| `frontend/src/features/simulador/components/SimuladorContent.tsx` | Stubbed to `return null` | v1.0 component used deleted types; Plan 02 will rewrite with full Phase 28 UI |

## Decisions Made

1. **IR helpers re-declared (not imported):** `irRatePctByDays`, `annualizeRate`, `netAnnualRate` are re-declared inside `useSimuladorCalc.ts` rather than exported from `useComparadorCalc`. Rationale: feature isolation — simulador should not depend on comparador internals (precedent D-12 from Phase 27).

2. **Ações: 12% a.a. hardcoded:** IBOV historical annualized nominal. Phase 28 does not model equity risk or volatility — the value is documented in `types.ts` comments and STATE.md.

3. **FIIs: 8% a.a. hardcoded:** DY médio proxy. Brazilian tax law exempts PF investors from IR on FII distributions.

4. **macro?.cdi only:** IPCA and SELIC are deliberately not in the `useMemo` dependency array — Phase 28 uses CDI as the RF proxy rate. RF is never benchmarked against IPCA+ or SELIC in this tool.

5. **SimuladorContent.tsx stubbed:** v1.0 content imported `useSimulador`, `Cenario`, `PrazoLabel`, `PerfilLabel`, `RebalancingItem` — all deleted in this plan. Stub prevents TS compile failure and keeps page.tsx functional until Plan 02.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Stubbed SimuladorContent.tsx to fix TypeScript compile**
- **Found during:** Task 1 verification (`npx tsc --noEmit`)
- **Issue:** `SimuladorContent.tsx` imported `useSimulador`, `Cenario`, `PrazoLabel`, `PerfilLabel`, `RebalancingItem` — all removed from types.ts and hooks; caused 10 TS errors
- **Fix:** Overwrote `SimuladorContent.tsx` with a minimal stub `export function SimuladorContent() { return null; }` — Plan 02 will fully replace this with Phase 28 implementation
- **Files modified:** `frontend/src/features/simulador/components/SimuladorContent.tsx`
- **Commit:** e8c08e3

## Commits

| Task | Hash | Message |
|------|------|---------|
| Task 1 | e8c08e3 | feat(28-01): replace simulador types with Phase 28 types and neutralize v1.0 stubs |
| Task 2 | a7e4941 | feat(28-01): add useSimuladorCalc hook with 3-scenario client-side projection |

## Known Stubs

- `frontend/src/features/simulador/components/SimuladorContent.tsx` — returns `null`, Plan 02 will rewrite with full Phase 28 UI (form + scenario cards + delta section)

## Self-Check: PASSED

- [x] `frontend/src/features/simulador/types.ts` exists — 9 exports verified
- [x] `frontend/src/features/simulador/hooks/useSimuladorCalc.ts` exists — 1 export (`useSimuladorCalc`)
- [x] Commit e8c08e3 exists in git log
- [x] Commit a7e4941 exists in git log
- [x] `npx tsc --noEmit` — zero simulador errors
- [x] No active `/simulador/simulate` calls remain (comments only)
- [x] Hook is pure: no fetch, useQuery, apiClient, or async in useSimuladorCalc.ts
