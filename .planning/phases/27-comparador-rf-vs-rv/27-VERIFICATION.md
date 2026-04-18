---
phase: 27-comparador-rf-vs-rv
verified: 2026-04-18T00:00:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 27: Comparador RF vs RV Verification Report

**Phase Goal:** Usuário informa valor, prazo e tipo de produto RF e vê tabela comparativa de retorno líquido nominal e real versus CDI, SELIC e IPCA+, com gráfico de evolução do patrimônio ao longo do prazo
**Verified:** 2026-04-18
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /renda-fixa/macro-rates response includes a selic field | VERIFIED | `MacroRatesResponse` in schemas.py line 217: `selic: Decimal \| None` |
| 2 | Backend reads market:macro:selic from Redis and returns it | VERIFIED | service.py line 454: `selic_raw = r.get("market:macro:selic")` + line 458: `selic=_safe_decimal(selic_raw)` + line 462: `selic=None` fallback |
| 3 | Frontend MacroRatesResponse type exposes selic | VERIFIED | types.ts line 113: `selic: string \| null` |
| 4 | User lands on /comparador and sees form with valor, prazo, tipo RF dropdown (5 options) | VERIFIED | ComparadorContent.tsx: 5 `<option>` elements (CDB, LCI, LCA, Tesouro Selic, Tesouro IPCA+), valor and prazo inputs present |
| 5 | Taxa field defaults to catalog representative rate and is editable | VERIFIED | `effectiveTaxa = taxaPct ?? defaultTaxa`; `getDefaultRateForTipo()` uses catalog midpoint; `onChange` handler updates taxaPct |
| 6 | Tesouro IPCA+ shows Spread input | VERIFIED | ComparadorContent.tsx lines 135-146: conditional render `{tipoRF === "TESOURO_IPCA" && (...)` with Spread input |
| 7 | User sees 4-row table with all required columns | VERIFIED | Table has 6 columns (Alternativa, Taxa Bruta, Taxa Liquida IR, Retorno Nominal, Retorno Real, Total Acumulado); `result.rows.map()` renders 4 rows |
| 8 | LCI/LCA rows display IRBadge Isento | VERIFIED | `IRBadge` component at line 18; renders `<span>Isento</span>` when `isExempt=true`; `tipoRfIsExempt()` returns true for LCI/LCA |
| 9 | Form field changes recompute table instantly (no API round-trip) | VERIFIED | `useComparadorCalc` uses `useMemo` with input fields as deps (line 166); calculation is 100% client-side |
| 10 | LineChart below table shows monthly patrimonio for 4 alternatives | VERIFIED | ComparadorChart.tsx: 4 `<Line>` elements for produto_rf, cdi, selic, ipca; `ResponsiveContainer` + `LineChart` present |
| 11 | E2E test covers /comparador with form + table + chart | VERIFIED | v1.6-comparador.spec.ts: 4 tests covering page load, table columns, chart SVG, spread input |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/modules/screener_v2/schemas.py` | MacroRatesResponse with cdi, ipca, selic fields | VERIFIED | Line 217: `selic: Decimal \| None = Field(None, ...)` |
| `backend/app/modules/screener_v2/service.py` | query_macro_rates() reads market:macro:selic | VERIFIED | Lines 454, 458, 462 — reads Redis key, passes to response, fallback to None |
| `backend/tests/test_renda_fixa_macro_rates.py` | Test asserts selic key in response and null fallback | VERIFIED | Line 35: `assert "selic" in data`; line 51: `assert data["selic"] is None`; dedicated COMP-01/02 test at line 63 |
| `frontend/src/features/screener_v2/types.ts` | MacroRatesResponse with selic in TypeScript | VERIFIED | Line 113: `selic: string \| null` |
| `frontend/src/features/comparador/types.ts` | TipoRF union + ComparadorRow + ProjectionPoint | VERIFIED | TipoRF (line 4), ComparadorRow (line 14), ProjectionPoint (line 26), ComparadorResult (line 34) |
| `frontend/src/features/comparador/hooks/useComparadorCalc.ts` | Client-side useMemo projection | VERIFIED | 167 lines; `useMemo` at line 119; full compound math; buildRow + projection loop |
| `frontend/src/features/comparador/components/ComparadorContent.tsx` | Form + 4-row table with IRBadge and spread input | VERIFIED | 227 lines; all form inputs; table; IRBadge; conditional spread input |
| `frontend/src/features/comparador/components/ComparadorChart.tsx` | Recharts LineChart with 4 series | VERIFIED | 109 lines; `LineChart` import; 4 `<Line>` elements |
| `frontend/e2e/v1.6-comparador.spec.ts` | E2E tests for /comparador | VERIFIED | 55 lines; 4 tests under `test.describe` |
| `frontend/app/comparador/page.tsx` | Page wrapper renders ComparadorContent | VERIFIED | Imports and renders `<ComparadorContent />` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| service.py:query_macro_rates | Redis key market:macro:selic | `r.get("market:macro:selic")` | WIRED | Line 454 confirmed |
| schemas.py:MacroRatesResponse | frontend MacroRatesResponse | JSON shape — selic on both sides | WIRED | Backend selic Decimal, frontend selic string \| null — contract aligned |
| ComparadorContent.tsx | useMacroRates() + useFixedIncomeCatalog() | hooks import from screener_v2 | WIRED | Line 3 import; lines 47-48 call with destructured data |
| ComparadorContent.tsx | useComparadorCalc hook | passes inputs + macro/catalog | WIRED | Line 64: `useComparadorCalc(inputs, macro, catalog)` |
| useComparadorCalc.ts | annualizeRate compound math | local function | WIRED | Lines 25-27; used in buildRow |
| ComparadorContent.tsx | ComparadorChart.tsx | props data={result.projection} | WIRED | Line 216: `<ComparadorChart data={result.projection} ...>` |
| ComparadorChart.tsx | recharts LineChart | import from "recharts" | WIRED | Line 11 import confirmed |
| v1.6-comparador.spec.ts | /comparador page | page.goto('/comparador') | WIRED | Lines 13, 31, 44 |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| COMP-01 | 27-01, 27-02 | Tabela comparativa retorno liquido nominal vs CDI/SELIC/IPCA+ com IR regressivo | SATISFIED | useComparadorCalc builds 4 rows; IR regressivo via irRatePctByDays(); taxaLiquidaAnualPct in ComparadorRow |
| COMP-02 | 27-03 | Coluna rentabilidade real + grafico evolucao patrimonio | SATISFIED | retornoRealPct in ComparadorRow; ComparadorChart with 4 lines; ProjectionPoint month-by-month array |

Both COMP-01 and COMP-02 are marked Complete in REQUIREMENTS.md — assignment matches Phase 27.

### Anti-Patterns Found

No anti-patterns detected. Scan of all phase-27 files found:
- No TODO/FIXME/PLACEHOLDER comments
- No `return null` or empty stub implementations  
- No hardcoded empty arrays passed to rendering paths
- `data.length === 0` guard in ComparadorChart returns a "no data" message (not a stub — data always has length prazoMeses+1 from the hook)

### Human Verification Required

#### 1. Visual rendering of the 4-row table

**Test:** Log into the app, navigate to /comparador, confirm the table shows 4 rows (selected produto RF + CDI + SELIC + IPCA+) with numeric values in all columns.
**Expected:** All 6 columns populated with numbers; selected produto row highlighted in blue.
**Why human:** Visual formatting and color coding cannot be verified programmatically.

#### 2. Spread input appears when Tesouro IPCA+ is selected

**Test:** On /comparador, change the Tipo RF dropdown to "Tesouro IPCA+". Confirm a "Spread (% a.a.)" input appears.
**Expected:** Spread input visible; changing it updates Total Acumulado row instantly.
**Why human:** Conditional rendering and real-time DOM update requires browser execution.

#### 3. Chart animates correctly with form changes

**Test:** Change Prazo from 24 to 60 months. Confirm the LineChart redraws immediately with 61 data points (0–60) and 4 distinct colored lines.
**Expected:** Chart redraws without page reload; 4 lines remain distinct and labeled.
**Why human:** Chart reactivity and visual output require browser.

---

_Verified: 2026-04-18_
_Verifier: Claude (gsd-verifier)_
