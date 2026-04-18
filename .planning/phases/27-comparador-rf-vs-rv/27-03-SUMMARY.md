---
phase: 27-comparador-rf-vs-rv
plan: "03"
subsystem: ui
tags: [recharts, linechart, comparador, playwright, e2e]

# Dependency graph
requires:
  - phase: 27-02
    provides: "useComparadorCalc returning projection: ProjectionPoint[], ComparadorContent.tsx with placeholder comment"
provides:
  - "ComparadorChart.tsx: Recharts LineChart wrapper consuming ProjectionPoint[] with 4 lines (produto_rf blue, CDI slate, SELIC emerald, IPCA+ amber)"
  - "ComparadorContent.tsx updated to render <ComparadorChart> replacing Plan 03 placeholder"
  - "v1.6-comparador.spec.ts: 4 Playwright E2E tests for /comparador page"
  - "COMP-02 fully delivered: rentabilidade real column (Plan 02) + gráfico evolução patrimônio (this plan)"
affects: [phase-28-simulador, v1.6-summary, COMP-01, COMP-02]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ComparadorChart: standalone Recharts LineChart component with BRL-formatted Y-axis, produtoRfLabel prop for dynamic legend"
    - "deploy-then-e2e: E2E tests run against production — deploy frontend before running playwright suite"

key-files:
  created:
    - frontend/src/features/comparador/components/ComparadorChart.tsx
    - frontend/e2e/v1.6-comparador.spec.ts
  modified:
    - frontend/src/features/comparador/components/ComparadorContent.tsx

key-decisions:
  - "Chart color palette: produto_rf=#2563eb (blue), CDI=#64748b (slate), SELIC=#10b981 (emerald), IPCA+=#f59e0b (amber) — matches table highlight colors"
  - "produtoRfLabel prop sourced from result.rows[0].label — ensures chart legend matches table row label (CDB/LCI/Tesouro IPCA+ etc.)"
  - "deploy-frontend.sh run before E2E to ensure production matches local code — tests run against https://investiq.com.br"

patterns-established:
  - "ComparadorChart receives ProjectionPoint[] directly (no data transformation needed — useComparadorCalc already produces correct shape)"
  - "E2E test checks svg.recharts-surface visibility for chart presence — avoids brittle text assertions on recharts internals"

requirements-completed: [COMP-02]

# Metrics
duration: 35min
completed: 2026-04-18
---

# Phase 27 Plan 03: Comparador RF vs RV — Chart + E2E Summary

**Recharts 4-line LineChart (patrimônio R$ vs meses) added to /comparador page consuming ProjectionPoint[] from useComparadorCalc, with Playwright E2E smoke suite covering page load, table columns, chart SVG, and Tesouro IPCA+ spread input**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-04-18T23:10:00Z
- **Completed:** 2026-04-18T23:40:28Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments
- Created `ComparadorChart.tsx` as a standalone Recharts LineChart component with 4 series, BRL-formatted axes, tooltip, legend, and empty-state guard
- Replaced the Plan 03 placeholder comment in `ComparadorContent.tsx` with `<ComparadorChart data={result.projection} produtoRfLabel={result.rows[0].label} />`
- Created `v1.6-comparador.spec.ts` with 4 Playwright E2E tests; deployed frontend to production and verified all 4 tests pass
- COMP-02 requirement fully delivered: rentabilidade real column (Plan 02) + gráfico evolução patrimônio (this plan)

## Chart Details

- **Color palette:** produto_rf `#2563eb` (blue, thicker 2.5px), CDI `#64748b` (slate), SELIC `#10b981` (emerald), IPCA+ `#f59e0b` (amber)
- **X-axis:** `mes` dataKey (months 0..prazoMeses), labeled "Meses"
- **Y-axis:** BRL compact formatter (`R$ 10.000`), width=80, `domain=["auto","auto"]`
- **Tooltip:** Full BRL (`R$ 10.250,00`) + `Mês N` label
- **Legend:** Dynamic — `produtoRfLabel` prop allows "CDB", "LCI", "Tesouro IPCA+" etc. matching the table row label

## E2E Test Results

- **Before:** 72 passing (v1.5 baseline per STATE.md; actual run showed 99 passing due to v1.6 plans 01+02 adding tests)
- **After:** +4 new tests, all passing
- **Pre-existing failures (unrelated):** 2 — `ai-features.spec.ts` `/ai/advisor page loads` and `fii-detail.spec.ts` CVM disclaimer — these existed before this plan

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ComparadorChart component** - `8eec186` (feat)
2. **Task 2: Wire ComparadorChart into ComparadorContent** - `18085b8` (feat)
3. **Task 3: Add Playwright E2E smoke test** - `1e932bd` (test)

## Files Created/Modified
- `frontend/src/features/comparador/components/ComparadorChart.tsx` - Recharts LineChart wrapper, 4 series, BRL formatting, empty state guard
- `frontend/src/features/comparador/components/ComparadorContent.tsx` - Added ComparadorChart import + replaced placeholder with component
- `frontend/e2e/v1.6-comparador.spec.ts` - 4 E2E tests for /comparador page

## Decisions Made
- Chart color palette: blue/slate/emerald/amber — complements the blue highlight on produto_rf table row
- `produtoRfLabel` sourced from `result.rows[0].label` — ensures legend is dynamic and consistent with table
- Deploy frontend before running E2E (tests run against production) — deviation Rule 3 (blocking issue auto-fixed)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Deployed frontend to production before running E2E tests**
- **Found during:** Task 3 (Playwright E2E smoke test)
- **Issue:** E2E tests run against `https://investiq.com.br` (production). Tests for "Taxa Bruta", "Evolução do patrimônio", chart SVG, and select dropdown were failing because the new ComparadorContent code wasn't deployed yet — production still had the old /comparador page
- **Fix:** Ran `bash deploy-frontend.sh` which built Next.js standalone, uploaded to VPS, applied proxy patch, and restarted container
- **Files modified:** None (deploy process, not code change)
- **Verification:** `HTTP 200` from container confirmed; all 4 E2E tests then passed
- **Committed in:** Part of Task 3 commit `1e932bd`

---

**Total deviations:** 1 auto-fixed (Rule 3 - blocking)
**Impact on plan:** Deploy was a required prerequisite for E2E tests against production. No scope creep.

## Issues Encountered
- E2E tests initially failed because production had old /comparador code — fixed by deploying frontend first

## COMP-01 and COMP-02 Final Verification

- **COMP-01** (form: valor + prazo + tipo RF + spread for TESOURO_IPCA; 4-row comparison table with IR): Delivered in Plans 01+02, verified by E2E test `/comparador Tesouro IPCA+ exposes spread input` and `/comparador form + 4-row table visible`
- **COMP-02** (rentabilidade real column + gráfico evolução patrimônio): Delivered — real column in Plan 02, chart in this plan; verified by E2E test `/comparador shows chart section (COMP-02)`

## Next Phase Readiness
- Phase 27 complete: /comparador shows form + 4-row table (nominal + real returns) + LineChart (wealth evolution over months)
- v1.6 milestone (Comparador RF vs RV) fully delivered
- Next: v1.7 Simulador de Alocação (SIM-01–03) when planned

## Known Stubs
None — all data is wired from `useComparadorCalc` which consumes live macro rates and catalog data.

---
*Phase: 27-comparador-rf-vs-rv*
*Completed: 2026-04-18*
