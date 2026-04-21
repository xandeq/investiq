# Phase 27: Comparador RF vs RV - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Standalone comparison tool at `/comparador` — user selects a RF product type + holding period + initial value, sees a comparison table and patrimônio chart against CDI, SELIC and IPCA+ benchmarks. No portfolio context required. Does NOT compare against IBOVESPA or user's portfolio (out of scope for this phase).

An early v1.0-era comparador exists (`/comparador/compare` + `ComparadorContent.tsx`) that compares ALL RF products vs IBOVESPA + portfolio. Phase 27 replaces/overhauls the frontend and adds the month-by-month projection — no new backend endpoint needed.

</domain>

<decisions>
## Implementation Decisions

### Architecture — Projection calculation
- **D-01:** Calculation is 100% client-side via `useMemo` — zero backend round-trip
- **D-02:** Rates source: `GET /screener/macro-rates` (already exists, Redis-cached) returns `{ cdi, ipca, selic }` annual rates
- **D-03:** RF product rate: fetched from `fixed_income_catalog` via existing endpoint (or `/renda-fixa`), keyed by `tipo_rf`
- **D-04:** Month-by-month compound loop in TypeScript — `annualizeRate()` helper already exists in `RendaFixaContent.tsx`, copy/reuse pattern
- **D-05:** TaxEngine not called directly — net annual rate comes from the catalog's `ir_breakdowns` (already computed by backend at catalog build time); for IPCA+ Tesouro, net rate = IPCA + spread - IR bracket
- **D-06:** Changing any form field triggers useMemo recompute instantly — no debounce needed (4 rows × N months is trivial computation)

### UI Layout — Table (not cards)
- **D-07:** Comparison rendered as a `<table>` — NOT the existing card grid from `ComparadorContent.tsx`
- **D-08:** Table rows (4 total): produto RF selecionado, CDI, SELIC, IPCA+
- **D-09:** Table columns: Taxa Bruta (% a.a.), Taxa Líquida IR (% a.a.), Retorno Nominal (%), Retorno Real (%), Total Acumulado (R$)
- **D-10:** "Isento IR" badge on LCI/LCA rows in the Taxa Líquida IR column (reuse IRBadge pattern from RendaFixaContent)
- **D-11:** Mobile: table scrolls horizontally (overflow-x-auto wrapper)

### Gráfico
- **D-12:** LineChart (simple, like FII detail page) — Claude decides specific styling during build
- **D-13:** X-axis: months; Y-axis: patrimônio acumulado (R$); one line per alternative (4 series)

### Tipo RF selector + taxa
- **D-14:** Dropdown with 5 options: CDB / LCI / LCA / Tesouro Selic / Tesouro IPCA+
  - Tesouro is split into two because their rate logic differs (Selic = CDI-like; IPCA+ = inflation-indexed with spread)
- **D-15:** Default rate = `fixed_income_catalog` average/representative rate for the selected type
- **D-16:** Taxa field is editable — user can override with their actual proposal rate
- **D-17:** For Tesouro IPCA+: rate = IPCA projetado (from Redis macro rates) + spread digitado pelo usuário; spread input shows alongside taxa field when IPCA+ is selected

### Claude's Discretion
- Exact Recharts LineChart styling (colors, dot size, tooltip format, legend placement)
- Handling of "Tesouro Selic" rate when catalog doesn't have a clean entry (fallback to SELIC rate from Redis)
- Empty/loading state design for table and chart
- How to present "Retorno Real" when IPCA data is unavailable

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing comparador (to extend/replace frontend)
- `frontend/src/features/comparador/components/ComparadorContent.tsx` — existing component to replace; reuse fmt/fmtBRL helpers, prazo tabs pattern, disclaimer banner
- `frontend/src/features/comparador/api.ts` — existing API client (check if still used)
- `frontend/src/features/comparador/hooks/useComparador.ts` — existing hook; may need new hook `useComparador27` or replace
- `frontend/app/comparador/page.tsx` — existing page wrapper to update

### Rate data sources
- `backend/app/modules/screener_v2/router.py` — `GET /screener/macro-rates` response shape `{ cdi, ipca, selic }`, `GET /screener/catalog` for RF product rates
- `frontend/src/features/screener_v2/hooks/useRendaFixa.ts` — `useMacroRates()` and `useFixedIncomeCatalog()` hooks — REUSE these directly

### Compound math reference
- `frontend/src/features/screener_v2/components/RendaFixaContent.tsx` — `annualizeRate()` function (lines ~50–70) — copy or import this helper

### Chart patterns
- `frontend/src/features/fii_detail/components/FIIPVPChart.tsx` — LineChart with ResponsiveContainer pattern
- `frontend/src/components/ui/chart.tsx` — ChartContainer wrapper for theme consistency (use this)

### TaxEngine (read-only reference — not called by new code)
- `backend/app/modules/market_universe/tax_engine.py` — understand IR brackets; catalog already stores computed net rates

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `useMacroRates()` hook: returns `{ cdi, ipca, selic }` — drop-in for rates source
- `useFixedIncomeCatalog()` hook: returns catalog rows with `ir_breakdowns` per prazo — use to get default rate for selected tipo_rf
- `fmt()` / `fmtBRL()` helpers: already in ComparadorContent.tsx — copy to new component
- `IRBadge` component: exists in RendaFixaContent.tsx — reuse for "Isento IR" display
- `annualizeRate(annualPct, holdingDays)`: compound math — in RendaFixaContent.tsx
- AppNav: already has `/comparador` link at line ~70 — NO changes needed

### Established Patterns
- Table with overflow-x-auto for mobile: see RendaFixaContent.tsx catalog section
- Prazo tabs (button group toggle): existing pattern in ComparadorContent.tsx
- Recharts LineChart: `import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer }` — wrap in `ChartContainer` from `ui/chart.tsx`

### Integration Points
- `frontend/app/comparador/page.tsx` → renders new `ComparadorV2Content` (or replace `ComparadorContent`)
- New component reads: `useMacroRates()` + `useFixedIncomeCatalog()` (both already exist)
- No new backend endpoints — all data from existing /screener/macro-rates and /screener/catalog

</code_context>

<specifics>
## Specific Ideas

- "Taxa field is editable — user overrides with their actual proposal rate" → this makes the tool immediately actionable when a bank sends a CDB proposal
- Tesouro IPCA+ has a separate spread input: "IPCA + X%" — spread is what the Tesouro auction shows
- The 4-row table (produto RF, CDI, SELIC, IPCA+) with total acumulado column makes the decision obvious at a glance

</specifics>

<deferred>
## Deferred Ideas

- Comparação com IBOVESPA histórico — out of scope for v1.6 (no historical index feed available)
- Comparação com carteira real do usuário — out of scope for v1.6 (standalone tool, no portfolio context)
- Simulador de Alocação (SIM-01–03) — v1.7 milestone
- Salvar simulações / histórico de comparações — future enhancement
- Múltiplos prazos simultâneos na mesma tabela — future enhancement

</deferred>

---

*Phase: 27-comparador-rf-vs-rv*
*Context gathered: 2026-04-18*
