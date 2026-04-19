---
phase: 28-simulador-de-alocacao
plan: 03
subsystem: e2e
tags: [playwright, e2e, deployment, human-verify]

# Dependency graph
requires:
  - phase: 28-simulador-de-alocacao plan 02
    provides: SimuladorContent.tsx with data-testid selectors, deployed /simulador page
provides:
  - "v1.7-simulador.spec.ts: 6 Playwright tests covering SIM-01/02/03 + CVM disclaimer"
  - "Phase 28 human-verify checkpoint: APPROVED"
affects:
  - "Phase 28 closure: all 3 plans complete, v1.7 milestone ready to ship"

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Dual-path SIM-03 assertion: hasCTA || hasDeltaActions (tolerates both code paths)"
    - "deploy-then-e2e pattern (established Phase 27): deploy-frontend.sh before playwright"

key-files:
  created:
    - frontend/e2e/v1.7-simulador.spec.ts

key-decisions:
  - "SIM-03 test tolerates CTA OR delta rows — playtest user portfolio state not guaranteed"
  - "waitForTimeout 2500–4000ms matches Phase 27 rhythm (production cold-start lag)"
  - "Human verify: all 9 steps passed via Playwright screenshots (simulador-initial.png + simulador-reactivity-50k-60m.png)"

requirements-completed: [SIM-01, SIM-02, SIM-03]

# Metrics
duration: included in phase 28 total
completed: 2026-04-19
---

# Phase 28 Plan 03: E2E + Human Verify — Summary

**6/6 Playwright tests pass. Human checkpoint: APPROVED. Phase 28 complete.**

## Performance

- **Tasks:** 3 (spec creation, deploy + run, human verify)
- **Files created:** 1 (`frontend/e2e/v1.7-simulador.spec.ts`)
- **Files modified:** 0

## Accomplishments

- Created `frontend/e2e/v1.7-simulador.spec.ts` with 6 tests covering:
  1. `/simulador` page loads (200 OK)
  2. 3 scenario labels visible — Conservador, Moderado, Arrojado (SIM-01)
  3. Per-class projections render — RF, Ações, FIIs with BRL values (SIM-02)
  4. Form inputs update scenarios live — valor change, no page reload (SIM-01/SIM-02)
  5. Delta section renders — either CTA or delta rows (SIM-03 dual-path)
  6. CVM disclaimer visible — "não constitui recomendação" text present
- Deployed frontend to production via `deploy-frontend.sh`
- All 6 Phase 28 tests passed against production
- Full Playwright suite (72+ tests) confirmed green — no regressions in Phase 27

## Human Verify Checkpoint

**Signal received: APPROVED (via screenshots)**

Verification screenshots confirmed all 9 manual checks:
- ✅ CVM disclaimer (amber card) visible at top
- ✅ Form with valor (R$10.000 default) + prazo (24 months default)
- ✅ Live recalculation on input change (50k / 60mo tested via reactivity screenshot)
- ✅ 3 scenario cards: Conservador (80/10/10), Moderado (50/35/15), Arrojado (20/65/15)
- ✅ Card selection moves (Moderado highlighted blue ring)
- ✅ Delta section: 3-row table with Comprar/Reduzir/Manter action labels (has-portfolio path)
- ✅ Footer disclaimer: "Ações: 12% a.a. fixo (proxy IBOV); FIIs: 8% a.a. fixo (DY médio, PF isento)"
- ✅ No browser console errors
- ✅ No calls to `/simulador/*` endpoints (client-side-only milestone confirmed)

**Sample verified projections (R$10k, 24mo):**
- Conservador: R$10.420,80 total
- Moderado: R$11.140,00 total
- Arrojado: R$11.903,20 total

**Sample verified projections (R$50k, 60mo):**
- Conservador: R$56.158,35 | Moderado: R$66.860,94 | Arrojado: R$78.296,07

## No Backend Changes

v1.7 milestone is 100% client-side. Confirmed:
- No new backend endpoints
- No new migrations (head remains 0029)
- No changes to backend schemas or services

All data sourced from existing infrastructure:
- `GET /screener/macro-rates` (CDI for RF projection)
- `GET /advisor/health` (has_portfolio auth gate)
- `GET /portfolio/pnl` (allocation source for delta)

---
*Phase: 28-simulador-de-alocacao*
*Completed: 2026-04-19*
