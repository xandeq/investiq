---
phase: 28-simulador-de-alocacao
plan: 02
subsystem: ui
tags: [react, nextjs, tanstack-query, tailwind, typescript]

# Dependency graph
requires:
  - phase: 28-simulador-de-alocacao plan 01
    provides: useSimuladorCalc hook, SimuladorInputs/ScenarioResult types, SCENARIO_ALLOCATIONS constants
  - phase: 23-portfolio-health-check
    provides: usePortfolioHealth hook, PortfolioHealth type with has_portfolio field
  - phase: 22-catalogo-renda-fixa
    provides: useMacroRates hook, GET /screener/macro-rates with CDI/SELIC/IPCA
  - phase: portfolio-pnl-existing
    provides: usePnl hook, PnLResponse with allocation[] + total_portfolio_value
provides:
  - "useSimuladorPortfolio hook: bridges advisor/health + portfolio/pnl, maps 5 AssetClass → 3 buckets"
  - "SimuladorContent: full /simulador page with form, 3 scenario cards, delta section with auth gate"
  - "SIM-01 (3 scenario cards with RF/Ações/FIIs allocations) — complete"
  - "SIM-02 (projected returns per class with IR) — complete"
  - "SIM-03 (delta vs current portfolio, auth-gated) — complete"
affects:
  - "28-03-PLAN.md (Playwright E2E for /simulador)"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Auth gate pattern: loadingPortfolio → !hasPortfolio (CTA) → hasPortfolio (delta table)"
    - "Multi-query bridge hook: useMemo over 2 react-query results → single derived state object"
    - "data-testid on scenario card buttons (data-testid=scenario-{key}) for E2E targeting"

key-files:
  created:
    - frontend/src/features/simulador/hooks/useSimuladorPortfolio.ts
    - (SimuladorContent.tsx fully rewritten from 8-line stub)
  modified:
    - frontend/src/features/simulador/components/SimuladorContent.tsx

key-decisions:
  - "Used getPnl().allocation[] as allocation source (not advisor/health.allocation_by_class — that field does NOT exist in shipped PortfolioHealth schema)"
  - "AssetClass mapping LOCKED: renda_fixa→rf, acao+bdr+etf→acoes, fii→fiis"
  - "hasPortfolio=false during loading AND on error — Delta CTA renders until both queries resolve cleanly"
  - "delta threshold 0.01 BRL — avoids floating-point 'Comprar R$ 0.00' noise"
  - "data-testid=scenario-{key} on card buttons for Plan 03 Playwright selectors"

patterns-established:
  - "SimuladorPortfolio bridge pattern: 2 queries → 1 derived hook with isLoading+hasError+hasPortfolio+portfolioTotalBRL+currentAllocation"
  - "Scenario card as <button> with selected/unselected border ring (border-blue-500 vs border-gray-200)"

requirements-completed: [SIM-01, SIM-02, SIM-03]

# Metrics
duration: 15min
completed: 2026-04-19
---

# Phase 28 Plan 02: Simulador de Alocação — UI Layer Summary

**React SimuladorContent delivering SIM-01/SIM-02/SIM-03: form → 3 selectable scenario cards with per-class IR projections → delta table vs current portfolio (auth-gated), sourcing allocation from getPnl() not advisor/health**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-19T03:00:00Z
- **Completed:** 2026-04-19T03:04:23Z
- **Tasks:** 2
- **Files modified:** 2 (1 created, 1 fully rewritten)

## Accomplishments

- Created `useSimuladorPortfolio` hook that bridges `usePortfolioHealth` (auth gate via `has_portfolio`) and `usePnl` (allocation source) — maps 5 backend AssetClass values to 3 UI buckets
- Rewrote `SimuladorContent.tsx` (stub → 326 lines) with form, 3 scenario cards, and conditional delta section
- Delta section has 3-state auth gate: skeleton (loading) → CTA card with `/portfolio/transactions` link (no portfolio) → 3-row delta table with Comprar/Reduzir/Manter labels (has portfolio)
- All TypeScript types compile cleanly (`npx tsc --noEmit` exits 0)

## Task Commits

1. **Task 1: useSimuladorPortfolio hook** - `85e0074` (feat)
2. **Task 2: SimuladorContent rewrite** - `6672fd4` (feat)

## Files Created/Modified

- `frontend/src/features/simulador/hooks/useSimuladorPortfolio.ts` — New hook bridging advisor/health + portfolio/pnl; 96 lines; exports `useSimuladorPortfolio`, `UseSimuladorPortfolioResult`, `CurrentAllocationBRL`
- `frontend/src/features/simulador/components/SimuladorContent.tsx` — Full rewrite from 8-line stub to 326-line component; exports named `SimuladorContent()` only

## Decisions Made

1. **Allocation source: getPnl() not advisor/health** — The shipped `PortfolioHealth` schema (`backend/app/modules/advisor/schemas.py`) does not include `allocation_by_class`. The STATE.md architecture note was aspirational, not implemented. `getPnl().allocation[]` is the correct allocation source for the delta section.

2. **hasPortfolio requires total_portfolio_value > 0** — Guards against edge case where PnL response returns empty allocation (e.g., all positions closed). The delta section should not render with all-zero rows.

3. **Delta threshold 0.01 BRL** — Uses `delta > 0.01` / `delta < -0.01` to avoid floating-point "Comprar R$ 0.00" noise in the delta action cell.

4. **data-testid on scenario cards** — Added `data-testid="scenario-{key}"` on `<button>` elements (e.g., `scenario-conservador`, `scenario-moderado`, `scenario-arrojado`) to enable Plan 03 Playwright selectors without text dependency.

## Auth Gate Behavior Matrix

| State | hasPortfolio | loadingPortfolio | Delta Section |
|-------|--------------|------------------|---------------|
| Queries loading | false | true | Skeleton div (animate-pulse) |
| Unauthenticated (401) | false | false | CTA card → /portfolio/transactions |
| Authenticated, no portfolio | false | false | CTA card → /portfolio/transactions |
| Authenticated, has portfolio | true | false | 3-row delta table (RF / Ações / FIIs) |

## Deviations from Plan

None — plan executed exactly as written. The implementation follows the provided code verbatim for `useSimuladorPortfolio.ts` and the specified layout spec for `SimuladorContent.tsx`.

## Issues Encountered

None.

## Confirmation: No Changes to page.tsx or AppNav.tsx

- `frontend/app/simulador/page.tsx` already imports `{ SimuladorContent }` from the correct path — no changes needed
- `frontend/src/components/AppNav.tsx` already links `/simulador` — no changes needed

## Known Stubs

None — all data sources are wired:
- Scenario projections: `useSimuladorCalc` consuming live `useMacroRates` CDI
- Delta target: `selectedScenario.rf/acoes/fiis.valor_alocado_brl` (computed from form inputs)
- Delta current: `useSimuladorPortfolio().currentAllocation` (from live `usePnl`)
- Portfolio total: `useSimuladorPortfolio().portfolioTotalBRL` (from live `usePnl`)

## Next Phase Readiness

- `/simulador` page is fully functional and renders correctly at build time
- Plan 03 (Playwright E2E) can use `data-testid="scenario-conservador"`, `data-testid="scenario-moderado"`, `data-testid="scenario-arrojado"` for card selection tests
- Delta section text selectors: "Delta vs carteira atual", "Cadastrar transações", "Comprar", "Reduzir", "Manter"

---
*Phase: 28-simulador-de-alocacao*
*Completed: 2026-04-19*
