---
phase: 22-catalogo-renda-fixa
verified: 2026-04-12T20:00:00Z
status: passed
score: 9/9 must-haves verified
---

# Phase 22: Catalogo Renda Fixa — Verification Report

**Phase Goal:** Usuário compara produtos de renda fixa com retorno líquido real (após IR regressivo) por prazo, sem precisar sair da plataforma
**Verified:** 2026-04-12
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /renda-fixa/macro-rates returns 200 with cdi/ipca decimal strings when Redis has data | VERIFIED | `router.py` line 276–292: endpoint exists, calls `query_macro_rates()`, `MacroRatesResponse` has `cdi: Decimal|None` and `ipca: Decimal|None` |
| 2 | GET /renda-fixa/macro-rates returns 200 with null cdi/ipca when Redis is unavailable | VERIFIED | `service.py` lines 458–460: `except Exception` returns `MacroRatesResponse(cdi=None, ipca=None)`; test `test_macro_rates_redis_fallback` asserts `data["cdi"] is None` |
| 3 | GET /renda-fixa/macro-rates returns 401 for unauthenticated requests | VERIFIED | `router.py` line 285: `current_user: dict = Depends(get_current_user)`; test `test_macro_rates_requires_auth` asserts 401 |
| 4 | User sees type toggle buttons (Todos, Tesouro, CDB, LCI, LCA) above the catalog table | VERIFIED | `RendaFixaContent.tsx` lines 150–156: `typeOptions` array with all 5 labels; rendered as buttons lines 170–182 |
| 5 | User clicks a type button and only that section/type is visible — table updates instantly without page reload | VERIFIED | `typeFilter` state wired to `useMemo filteredCatalog` (line 126–148); Tesouro section gated on `typeFilter === "" or "Tesouro"` (line 226); CDB/LCI/LCA section gated on `typeFilter !== "Tesouro"` (line 283) |
| 6 | User enters a prazo minimo in months and CDB/LCI/LCA rows with min_months < value are hidden | VERIFIED | `RendaFixaContent.tsx` lines 133–138: `minMonths` filter in `useMemo` — `rows.filter(r => r.min_months >= m)`; input rendered lines 184–196 |
| 7 | User selects a prazo (6m/1a/2a/5a) and CDB/LCI/LCA table sorts by net_pct for that period | VERIFIED | `RendaFixaContent.tsx` lines 140–147: sort by `ir_breakdowns.find(bd => bd.period_label === selectedPrazo)` with `asc/desc`; prazo buttons rendered lines 198–218 |
| 8 | Each net_pct cell shows a green/amber/gray indicator based on whether it beats CDI, only IPCA, or neither | VERIFIED | `RendaFixaContent.tsx` lines 60–86 (CatalogRow): `beatsCDI`/`beatsIPCA` calculated via `annualizeRate()`; indicators rendered: green `&#10003; CDI`, amber `~ IPCA`, gray `— abaixo` |
| 9 | When macro rates are loading, net_pct cells render without beat indicator (no flash of wrong colors) | VERIFIED | Lines 76: `{(cdiForPeriod !== null || ipcaForPeriod !== null) && ...}` — when `macroRates` is undefined/loading, `cdiForPeriod` and `ipcaForPeriod` are `null`, so the indicator block does not render |

**Score:** 9/9 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/modules/screener_v2/schemas.py` | MacroRatesResponse Pydantic model | VERIFIED | Lines 212–216: `class MacroRatesResponse(BaseModel)` with `cdi: Decimal|None` and `ipca: Decimal|None` |
| `backend/app/modules/screener_v2/service.py` | query_macro_rates async function | VERIFIED | Lines 442–460: `async def query_macro_rates()` reads `market:macro:cdi` and `market:macro:ipca` from Redis |
| `backend/app/modules/screener_v2/router.py` | GET /macro-rates endpoint | VERIFIED | Lines 276–292: route `/macro-rates`, `response_model=MacroRatesResponse`, `@limiter.limit("30/minute")`, `Depends(get_current_user)` |
| `backend/tests/test_renda_fixa_macro_rates.py` | 3 test cases for macro-rates endpoint | VERIFIED | 50 lines; 3 `@pytest.mark.asyncio` tests: `test_macro_rates_requires_auth`, `test_macro_rates_endpoint`, `test_macro_rates_redis_fallback` |
| `frontend/src/features/screener_v2/types.ts` | MacroRatesResponse TypeScript interface | VERIFIED | Lines 110–113: `export interface MacroRatesResponse { cdi: string | null; ipca: string | null; }` |
| `frontend/src/features/screener_v2/api.ts` | getMacroRates fetch function | VERIFIED | Lines 43–45: `export async function getMacroRates()` calls `apiClient<MacroRatesResponse>("/renda-fixa/macro-rates")` |
| `frontend/src/features/screener_v2/hooks/useRendaFixa.ts` | useMacroRates hook | VERIFIED | Lines 21–27: `export function useMacroRates()` with `queryKey: ["renda-fixa", "macro-rates"]`, `staleTime: 60 * 60_000` |
| `frontend/src/features/screener_v2/components/RendaFixaContent.tsx` | Filter buttons, sort controls, beat indicator | VERIFIED | `typeFilter` state, `useMemo filteredCatalog`, toggle buttons, prazo sort, `annualizeRate`, `beatsCDI`/`beatsIPCA`, all present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `router.py` | `service.py` | calls `query_macro_rates()` | WIRED | `router.py` line 292: `return await query_macro_rates()` |
| `service.py` | Redis | `r.get("market:macro:cdi")` and `r.get("market:macro:ipca")` | WIRED | `service.py` lines 452–453 |
| `RendaFixaContent.tsx` | `useRendaFixa.ts` | `useMacroRates()` hook call | WIRED | `RendaFixaContent.tsx` line 3 import + line 124 call: `const { data: macroRates } = useMacroRates()` |
| `useRendaFixa.ts` | `/renda-fixa/macro-rates` API | `getMacroRates` fetch function | WIRED | `useRendaFixa.ts` line 3 import; line 24: `queryFn: getMacroRates` |
| `RendaFixaContent.tsx` | useMemo filter pipeline | `typeFilter + minMonths + selectedPrazo` state variables | WIRED | `useMemo` at line 126 depends on all four state vars; `filteredCatalog.map` used at line 324 |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| RF-01 | 22-01, 22-02 | Catálogo com Tesouro, CDB, LCI/LCA agrupados por tipo, mostrando taxa, vencimento e valor mínimo | SATISFIED | Tesouro section with tipo_titulo/vencimento/taxa columns; CDB/LCI/LCA section with instrument_type/min_months/max_months/rate columns in `RendaFixaContent.tsx` |
| RF-02 | 22-01, 22-02 | Retorno líquido IR por prazo (90d, 1a, 2a, 5a) + destaque isenção LCI/LCA | SATISFIED | `ir_breakdowns` for 6m/1a/2a/5a displayed; `IRBadge` shows "Isento" for is_exempt rows; LCI/LCA are_exempt=True per catalog data. Note: plan uses 6m not 90d per decision D-13 — accepted deviation documented in CONTEXT.md |
| RF-03 | 22-01, 22-02 | Filtros por tipo/prazo, ordenação por retorno líquido, indicador CDI/IPCA | SATISFIED | Type toggle buttons, minMonths input, selectedPrazo sort, beat indicator all implemented and wired |

---

### Anti-Patterns Found

None detected. Scan results:

- No TODO/FIXME/HACK/PLACEHOLDER comments in modified files
- No `return null` / `return {}` / `return []` stubs in backend endpoint
- No hardcoded empty arrays flowing to rendering — `filteredCatalog` derives from real `catalog?.results` via useMemo
- `placeholder="ex: 12"` in RendaFixaContent.tsx line 191 is an HTML input placeholder attribute, not a stub indicator
- Beat indicator conditional `(cdiForPeriod !== null || ipcaForPeriod !== null)` is a deliberate no-flash guard, not a stub

---

### Human Verification Required

#### 1. Filter bar visual layout and interactivity

**Test:** Navigate to /renda-fixa page when logged in. Verify the filter bar appears above the catalog with 5 type buttons (Todos, Tesouro, CDB, LCI, LCA), a prazo minimo input, and 4 prazo sort buttons (6m, 1a, 2a, 5a).
**Expected:** Clicking "CDB" hides the Tesouro section and shows only CDB rows. Clicking a prazo button re-sorts the table by net_pct for that period. The active button is highlighted blue/indigo.
**Why human:** Client-side filter and sort behavior with live data cannot be fully verified from static code analysis alone.

#### 2. Beat indicator colors at runtime

**Test:** With Redis populated (CDI and IPCA rates in cache), navigate to /renda-fixa. Observe per-cell indicators in the CDB/LCI/LCA table.
**Expected:** LCI/LCA rows (is_exempt=True) with higher rates show green "✓ CDI". Lower-rate CDB rows may show amber "~ IPCA" or gray "— abaixo". No beat indicators appear momentarily in the wrong color before macroRates loads.
**Why human:** Beat indicator logic depends on live Redis CDI/IPCA values and compound return math — visual correctness requires runtime data.

#### 3. LCI/LCA "Isento" badge unchanged

**Test:** View any LCI or LCA row in the catalog table.
**Expected:** "Isento" text appears in green in the IR column for all prazo cells. No IR percentage is shown for these rows.
**Why human:** IRBadge component rendering requires visual inspection with real catalog data.

---

### Gaps Summary

No gaps. All 9 observable truths are verified, all 8 required artifacts exist and are substantive, all 5 key links are wired, and all 3 requirements (RF-01, RF-02, RF-03) are satisfied with implementation evidence.

---

_Verified: 2026-04-12T20:00:00Z_
_Verifier: Claude (gsd-verifier)_
