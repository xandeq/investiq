# Phase 22: Catálogo Renda Fixa - Research

**Researched:** 2026-04-12
**Domain:** Frontend extension (useMemo filters + sort + beat indicator) + one thin backend endpoint
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Filtros — inline useMemo, sem botão de aplicar**
- D-01: Filtros inline/instant — atualizam tabela ao clicar/digitar, sem botão "Aplicar" — mesmo padrão do Phase 21 (AcoesUniverseContent useMemo)
- D-02: Filtro de tipo: botões toggle (Todos | Tesouro | CDB | LCI | LCA) — não dropdown
- D-03: Filtro de prazo mínimo: input numérico em meses (ex: "12" para ≥12 meses) — filtra por `min_months >= valor`
- D-04: Implementar como extensão do `RendaFixaContent.tsx` existente — não criar novo componente ou feature dir

**Sort por retorno líquido**
- D-05: Sort por coluna de retorno líquido (net_pct) aplicado a um prazo selecionado — o usuário escolhe o prazo (6m | 1a | 2a | 5a) e a tabela ordena por esse net_pct
- D-06: Prazo de ordenação selecionável via tabs ou botões de prazo — estado local `selectedPrazo` controla qual coluna é referência para sort
- D-07: Sort via `useMemo` sobre os dados já carregados — sem chamada adicional ao backend

**Indicador CDI/IPCA (beat indicator)**
- D-08: CDI e IPCA disponíveis em `market:macro:cdi` e `market:macro:ipca` no Redis — já populados pelo python-bcb Celery beat
- D-09: Criar endpoint `GET /renda-fixa/macro-rates` que lê `market:macro:cdi` e `market:macro:ipca` do Redis e retorna `{cdi: "10.65", ipca: "5.06"}` — mesmo padrão de `query_tesouro_rates()` em `service.py`
- D-10: No frontend, buscar macro rates via `useQuery` com staleTime longo (1h) — chamada leve, dados raramente mudam
- D-11: Para cada célula de retorno líquido: mostrar ícone verde ✓ se `net_pct > cdi_anualizado_para_prazo` OU `net_pct > ipca_anualizado_para_prazo` — exibir qual benchmark supera (CDI ou IPCA ou ambos)
- D-12: LCI/LCA com `is_exempt: true` têm badge "Isento IR" já implementado — manter, não alterar

**Prazos — manter "6m" (não corrigir para "90d")**
- D-13: Labels de prazo permanecem: `6m | 1a | 2a | 5a` — não alterar o existing `ir_breakdowns` period_label

### Claude's Discretion

- Layout exato do filtro bar (acima da tabela, card separado, ou linha inline)
- Ícone específico para o beat indicator (✓ verde / ✗ vermelho ou texto "bate CDI" / "abaixo CDI")
- Empty state quando nenhum produto passa no filtro
- Skeleton/loading enquanto macro rates carregam

### Deferred Ideas (OUT OF SCOPE)

- Nenhuma sugestão de escopo adicional surgiu durante a discussão

</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RF-01 | Usuário pode ver catálogo com Tesouro Direto, CDB, LCI/LCA agrupados por tipo, mostrando taxa, vencimento e valor mínimo de aplicação | Already implemented — `GET /renda-fixa/catalog` + `RendaFixaContent.tsx` render both Tesouro and CDB/LCI/LCA sections |
| RF-02 | Cada produto exibe retorno líquido IR por prazo (6m, 1a, 2a, 5a) calculado via TaxEngine — LCI/LCA têm destaque visual de isenção IR | Already implemented — `ir_breakdowns[]` in catalog response + `IRBadge` component exists |
| RF-03 | Usuário pode filtrar catálogo por tipo e prazo mínimo, ordenar por retorno líquido, e ver indicador visual se produto bate CDI/IPCA no prazo | Gap — filters/sort/beat indicator do not exist yet; `GET /renda-fixa/macro-rates` endpoint to create |

</phase_requirements>

---

## Summary

Phase 22 is confirmed to be almost entirely a **frontend extension** of already-working code. The page `/renda-fixa`, the component `RendaFixaContent.tsx`, endpoints `GET /renda-fixa/catalog` and `GET /renda-fixa/tesouro`, and the `TaxEngine` are all fully operational from v1.1. Requirements RF-01 and RF-02 are effectively already satisfied by existing code — Phase 22 only needs to confirm they render correctly and then deliver RF-03.

The single backend addition is a thin `GET /renda-fixa/macro-rates` endpoint that reads two Redis string keys (`market:macro:cdi`, `market:macro:ipca`) and returns a JSON object. The pattern is a direct copy of `query_tesouro_rates()` — no DB query, no external call, just `redis.get()`. The router is already mounted at `/renda-fixa` in `main.py` (line 126), so adding the route requires zero changes to `main.py`.

The frontend work adds four capabilities to `RendaFixaContent.tsx`: (1) type toggle buttons that useMemo-filter the catalog rows, (2) a prazo-mínimo number input filtering on `row.min_months`, (3) a selectedPrazo state controlling which `net_pct` column the sort targets, and (4) a beat indicator on each net_pct cell comparing against CDI and IPCA annualized to the holding period. All patterns have direct precedent in `AcoesUniverseContent.tsx` (Phase 21).

**Primary recommendation:** Create two plans — Plan 1 (backend: macro-rates endpoint + schema + test), Plan 2 (frontend: filters + sort + beat indicator in RendaFixaContent.tsx + E2E update). The backend plan is small enough to consider merging into Plan 2, but separating keeps each plan focused.

---

## Standard Stack

### Core (confirmed from codebase inspection)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| React `useState` + `useMemo` | React 18 (Next.js 15) | Client-side filter/sort state | Phase 17 + 21 established this pattern |
| `@tanstack/react-query` `useQuery` | Already in project | Data fetching + cache | `useFixedIncomeCatalog`, `useTesouroRates` use it |
| FastAPI `APIRouter` | Already in project | Add `/renda-fixa/macro-rates` route | Router already registered in main.py |
| `redis` (sync, `decode_responses=True`) | Already in project | Read `market:macro:cdi/ipca` | Same call as `_get_cdi_annual()` in comparador/service.py |
| Tailwind CSS | Already in project | Toggle button styling (active/inactive) | Established in Phase 21 mcap tier buttons |

### No New Dependencies

This phase requires zero new packages. All tools are already installed and in use.

**Installation:** None required.

---

## Architecture Patterns

### Recommended Project Structure (files to modify/add)

```
backend/app/modules/screener_v2/
├── schemas.py          — ADD MacroRatesResponse Pydantic model
├── service.py          — ADD query_macro_rates() function
└── router.py           — ADD GET /macro-rates route

frontend/src/features/screener_v2/
├── types.ts            — ADD MacroRatesResponse interface
├── api.ts              — ADD getMacroRates() fetch function
├── hooks/
│   └── useRendaFixa.ts — ADD useMacroRates() hook
└── components/
    └── RendaFixaContent.tsx — ADD filters + sort + beat indicator
```

### Pattern 1: Backend — query_macro_rates() following query_tesouro_rates()

**What:** Sync Redis read of two string keys, returning a Pydantic schema.
**When to use:** Any time macro indicator values are needed without a DB query.

```python
# Source: backend/app/modules/comparador/service.py line 52-59
# backend/app/modules/screener_v2/service.py — ADD this function

async def query_macro_rates() -> MacroRatesResponse:
    """Fetch CDI and IPCA annual rates from Redis macro cache.

    Keys set by refresh_macro Celery beat task (every 7h).
    Falls back to None values if Redis unavailable.
    """
    try:
        import redis as redis_lib
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis_lib.Redis.from_url(redis_url, decode_responses=True)
        cdi_raw = r.get("market:macro:cdi")
        ipca_raw = r.get("market:macro:ipca")
        return MacroRatesResponse(
            cdi=_safe_decimal(cdi_raw),
            ipca=_safe_decimal(ipca_raw),
        )
    except Exception as exc:
        logger.error("query_macro_rates: Redis unavailable: %s", exc)
        return MacroRatesResponse(cdi=None, ipca=None)
```

### Pattern 2: Backend — MacroRatesResponse schema

```python
# Source: backend/app/modules/market_data/schemas.py — MacroCache reference
# backend/app/modules/screener_v2/schemas.py — ADD

class MacroRatesResponse(BaseModel):
    """Response for GET /renda-fixa/macro-rates."""
    cdi: Decimal | None   # Annual CDI rate as percentage, e.g. "10.65"
    ipca: Decimal | None  # Annual IPCA rate as percentage, e.g. "5.06"
```

### Pattern 3: Backend — Router endpoint (no auth change needed)

```python
# Source: backend/app/modules/screener_v2/router.py — tesouro_rates() pattern

@router.get(
    "/macro-rates",
    response_model=MacroRatesResponse,
    summary="CDI e IPCA anuais do cache Redis",
    tags=["renda-fixa"],
)
@limiter.limit("30/minute")
async def macro_rates(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> MacroRatesResponse:
    return await query_macro_rates()
```

### Pattern 4: Frontend — Type toggle buttons (copy of mcap tier buttons in AcoesUniverseContent)

**What:** Toggle buttons that set filter state, triggering useMemo re-filter.
**When to use:** Discrete category filter with 4–5 options.

```typescript
// Source: AcoesUniverseContent.tsx line 178-180 (toggleMcap pattern)
type InstrumentType = "" | "Tesouro" | "CDB" | "LCI" | "LCA";

const [typeFilter, setTypeFilter] = useState<InstrumentType>("");

// In useMemo filtered:
let rows = catalog?.results ?? [];
if (typeFilter === "Tesouro") {
  rows = tesouro?.results ?? [];  // switch to tesouro section
}
if (typeFilter === "CDB" || typeFilter === "LCI" || typeFilter === "LCA") {
  rows = (catalog?.results ?? []).filter(r => r.instrument_type === typeFilter);
}
if (minMonths) {
  const m = parseInt(minMonths, 10);
  rows = rows.filter(r => r.min_months >= m);
}
```

**Note:** Tesouro rows come from a different data source than CDB/LCI/LCA. The type filter "Todos" shows both sections; type-specific filters show only the selected section. The Tesouro section doesn't have `ir_breakdowns` or `min_months` — the prazo filter and sort should only apply to the CDB/LCI/LCA catalog section.

### Pattern 5: Frontend — selectedPrazo + sort useMemo

**What:** State controlling which `ir_breakdown.period_label` column is the sort key.
**When to use:** Multi-column numeric sort where the reference column is user-selectable.

```typescript
// Source: AcoesUniverseContent.tsx line 115-133 (sort pattern)
const [selectedPrazo, setSelectedPrazo] = useState<"6m" | "1a" | "2a" | "5a">("1a");
const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");

// In useMemo (applied to CDB/LCI/LCA rows only):
const sortedRows = useMemo(() => {
  return [...filteredRows].sort((a, b) => {
    const aBreakdown = a.ir_breakdowns.find(bd => bd.period_label === selectedPrazo);
    const bBreakdown = b.ir_breakdowns.find(bd => bd.period_label === selectedPrazo);
    const aVal = aBreakdown ? parseFloat(aBreakdown.net_pct) : null;
    const bVal = bBreakdown ? parseFloat(bBreakdown.net_pct) : null;
    if (aVal === null) return 1;
    if (bVal === null) return -1;
    return sortDir === "desc" ? bVal - aVal : aVal - bVal;
  });
}, [filteredRows, selectedPrazo, sortDir]);
```

### Pattern 6: Frontend — Beat indicator calculation

**What:** Compare net_pct against CDI and IPCA annualized to the holding period.
**When to use:** Each net_pct cell in the CDB/LCI/LCA table.

```typescript
// Source: backend/app/modules/comparador/service.py _compound_return() — same math in JS
function annualizeRate(annualPct: number, holdingDays: number): number {
  // (1 + r/100)^(days/365) - 1, expressed as percentage
  return ((1 + annualPct / 100) ** (holdingDays / 365) - 1) * 100;
}

// Usage in CatalogRow:
const holdingDays = breakdown.holding_days;
const cdiForPeriod = macroRates?.cdi
  ? annualizeRate(parseFloat(macroRates.cdi), holdingDays)
  : null;
const ipcaForPeriod = macroRates?.ipca
  ? annualizeRate(parseFloat(macroRates.ipca), holdingDays)
  : null;
const netPct = parseFloat(breakdown.net_pct);
const beatsCDI  = cdiForPeriod !== null && netPct > cdiForPeriod;
const beatsIPCA = ipcaForPeriod !== null && netPct > ipcaForPeriod;
```

**Beat indicator colors (Claude's discretion — recommended):**
- green cell bg / green ✓ : bate CDI (stronger benchmark)
- amber cell bg / amber ~ : bate IPCA mas não CDI
- gray cell bg / gray — : não bate nenhum

### Pattern 7: Frontend — useMacroRates hook

**What:** Direct copy of `useTesouroRates()` with different endpoint and staleTime.

```typescript
// Source: frontend/src/features/screener_v2/hooks/useRendaFixa.ts
export function useMacroRates() {
  return useQuery({
    queryKey: ["renda-fixa", "macro-rates"],
    queryFn: getMacroRates,
    staleTime: 60 * 60_000,  // 1h — macro rates rarely change
  });
}
```

### Anti-Patterns to Avoid

- **Putting Tesouro rows through the CDB/LCI/LCA filter pipeline:** Tesouro rows have no `ir_breakdowns`, no `min_months`, and no `instrument_type` from `FixedIncomeCatalog`. The two sections remain separate — type filter hides sections, not mixes them.
- **Calling backend for filter/sort:** All filtering and sorting happens in `useMemo` over already-loaded data (D-01, D-07).
- **Modifying `main.py`:** The `/renda-fixa` prefix router is already registered at line 126. Adding `/macro-rates` to router.py is sufficient.
- **Creating new feature directory:** D-04 locks RendaFixaContent.tsx as the single file to extend — no new feature dir or page file.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Annualizing rates for different periods | Custom compound interest formula | Copy `_compound_return()` from comparador/service.py (same math in JS) | Formula is established and tested in the backend |
| IR regressivo rates | Custom tax tables | TaxEngine already in every `ir_breakdown.ir_rate_pct` | Already calculated and stored in catalog response |
| Redis client connection | Custom connection pooling | `redis.Redis.from_url(os.environ.get("REDIS_URL", ...))` | Established pattern across 8+ service files |

**Key insight:** The project's established pattern is "data pre-calculated by Celery, served from DB or Redis, frontend renders". Do not introduce any request-time calculations beyond the simple annualization math in the beat indicator.

---

## Common Pitfalls

### Pitfall 1: Tesouro section vs CDB/LCI/LCA section have different data shapes

**What goes wrong:** Applying the type filter or sort to Tesouro rows which come from `useTesouroRates()` (different hook, different shape — `TesouroRateRow` has no `ir_breakdowns`).
**Why it happens:** The page has two distinct data sources merged into one view.
**How to avoid:** Type filter "Tesouro" should show/hide the Tesouro section div, not filter catalog rows. Sort and min_months filter apply only to CDB/LCI/LCA catalog rows.
**Warning signs:** TypeScript errors accessing `.ir_breakdowns` on `TesouroRateRow`.

### Pitfall 2: selectedPrazo and typeFilter state reset timing

**What goes wrong:** User selects prazo "5a", switches type to "Tesouro" (which has no prazo concept), UI shows stale prazo selection.
**Why it happens:** selectedPrazo state persists across type changes.
**How to avoid:** The prazo buttons only affect CDB/LCI/LCA section. When type is "Tesouro", hide the prazo selector and sort controls. Or: keep prazo state visible but grayed out.

### Pitfall 3: Beat indicator shows stale/null CDI before macro-rates loads

**What goes wrong:** Brief flash of "no indicator" or "gray" on every cell during initial load because `useMacroRates` hasn't returned yet.
**Why it happens:** `useQuery` is async; data is undefined on first render.
**How to avoid:** When `macroRates` is undefined/loading, render cells without beat indicator (show just net_pct, no color). Do not show error. This is the established loading pattern in RendaFixaContent.tsx.

### Pitfall 4: Redis key `market:macro:ipca` stores annual or monthly IPCA?

**What goes wrong:** Comparing net_pct (annual equivalent) against raw monthly IPCA stored in Redis.
**Why it happens:** IPCA is officially reported monthly (e.g., 0.42% for March) but CDI is reported annually.
**How to verify:** Check `market_data/tasks.py` to see how IPCA is stored. From the schema comment: "market:macro:ipca — Decimal string" — inspect the task to confirm it stores the annual rate.
**How to avoid:** Read the task code before implementing the beat indicator. If IPCA is monthly, convert: `ipca_annual = ((1 + ipca_monthly/100)^12 - 1) * 100` before using in `annualizeRate()`.

---

## Code Examples

### Verified: Redis CDI read pattern (from comparador/service.py)

```python
# Source: backend/app/modules/comparador/service.py lines 52-59
def _get_cdi_annual() -> Decimal | None:
    try:
        r = _get_redis()
        raw = r.get("market:macro:cdi")
        return _safe_dec(raw)
    except Exception as exc:
        logger.warning("_get_cdi_annual: Redis error: %s", exc)
        return None
```

### Verified: Compound return math (from comparador/service.py)

```python
# Source: backend/app/modules/comparador/service.py lines 62-66
def _compound_return(annual_pct: Decimal, holding_days: int) -> Decimal:
    """Compound annual rate for holding_days: (1 + r)^(d/365) - 1 in %."""
    r = float(annual_pct) / 100
    compound = (1 + r) ** (holding_days / 365) - 1
    return Decimal(str(round(compound * 100, 4)))
```

### Verified: HOLDING_PERIODS mapping (from screener_v2/schemas.py)

```python
# Source: backend/app/modules/screener_v2/schemas.py lines 20-25
HOLDING_PERIODS = {
    "6m": 180,
    "1a": 365,
    "2a": 730,
    "5a": 1825,
}
```

### Verified: useMemo filter pattern (from AcoesUniverseContent.tsx)

```typescript
// Source: frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx lines 74-136
const filtered = useMemo(() => {
  if (!data?.results) return [];
  let rows = data.results.filter((row) => { ... });
  if (sortCol) {
    rows = [...rows].sort((a, b) => { ... });
  }
  return rows;
}, [data, minDy, maxPl, sectorFilter, mcapTier, sortCol, sortDir]);
```

### Verified: Toggle button pattern (from AcoesUniverseContent.tsx)

```typescript
// Source: frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx lines 255-285
<button
  onClick={() => toggleMcap("small")}
  className={`px-3 py-2 rounded-md text-xs font-medium border transition-colors ${
    mcapTier === "small"
      ? "bg-blue-500 text-white border-blue-500"
      : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
  }`}
>
  Small &lt;2B
</button>
```

---

## Open Questions

1. **Is IPCA stored annually or monthly in Redis?**
   - What we know: `market_data/tasks.py` populates `market:macro:ipca`; the schema says "Decimal string"; the comparador service does NOT read IPCA (only CDI).
   - What's unclear: Whether the value is annual rate (e.g., 4.83%) or monthly (e.g., 0.42%)
   - Recommendation: Read `backend/app/modules/market_data/tasks.py` lines around the ipca write before implementing beat indicator. If monthly, annualize before use.

2. **Does the CDB/LCI/LCA catalog have "Tesouro Direto" rows with `instrument_type == "Tesouro"`?**
   - What we know: The DB model is `FixedIncomeCatalog`; the type filter D-02 includes "Tesouro" as a button
   - What's unclear: Whether Tesouro items appear in `fixed_income_catalog` table or only in Redis tesouro:rates:* keys
   - From the existing code: Tesouro data comes exclusively from `useTesouroRates()` (Redis), NOT from `useFixedIncomeCatalog()` (DB). The type filter "Tesouro" means hide/show the Tesouro section, not filter catalog rows.
   - Recommendation: Type toggle implementation should be: "Todos" shows both sections, "Tesouro" hides CDB section, "CDB/LCI/LCA" hides Tesouro section and filters catalog rows by instrument_type.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend), Playwright (E2E) |
| Config file | `backend/pytest.ini` or `pyproject.toml` (existing) |
| Quick run command | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_renda_fixa_macro_rates.py -x -q` |
| Full suite command | `cd D:/claude-code/investiq/backend && python -m pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RF-01 | /renda-fixa page loads and shows catalog sections | E2E smoke | `npx playwright test e2e/tools.spec.ts --grep "renda-fixa"` | ✅ existing test |
| RF-02 | LCI/LCA show "Isento" badge, CDB shows IR% | E2E regression | existing `renda-fixa shows fixed income content` | ✅ existing test |
| RF-03 | GET /renda-fixa/macro-rates returns 200 with cdi + ipca | unit | `pytest tests/test_renda_fixa_macro_rates.py::test_macro_rates_endpoint -x` | ❌ Wave 0 |
| RF-03 | GET /renda-fixa/macro-rates requires auth (401 unauthenticated) | unit | `pytest tests/test_renda_fixa_macro_rates.py::test_macro_rates_requires_auth -x` | ❌ Wave 0 |
| RF-03 | GET /renda-fixa/macro-rates returns null cdi/ipca when Redis unavailable | unit | `pytest tests/test_renda_fixa_macro_rates.py::test_macro_rates_redis_fallback -x` | ❌ Wave 0 |
| RF-03 | /renda-fixa page shows filter buttons and result count | E2E | update `e2e/tools.spec.ts` renda-fixa regression test | ✅ existing (extend) |

### Sampling Rate

- **Per task commit:** `cd D:/claude-code/investiq/backend && python -m pytest tests/test_renda_fixa_macro_rates.py -x -q`
- **Per wave merge:** `cd D:/claude-code/investiq/backend && python -m pytest -x -q`
- **Phase gate:** Full backend suite green + Playwright `tools.spec.ts` green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_renda_fixa_macro_rates.py` — covers RF-03 backend endpoint (auth, 200 response, Redis fallback)
- [ ] No new conftest fixtures needed — existing `client`, `db_session`, `email_stub` fixtures are sufficient
- [ ] Playwright test extension in `e2e/tools.spec.ts` — add assertion for filter buttons text in the regression test

*(All gaps are Wave 0 for the backend plan — Plan 1 creates test file before implementation.)*

---

## Sources

### Primary (HIGH confidence)
- Direct codebase read — `backend/app/modules/screener_v2/router.py` — confirmed router structure and existing endpoints
- Direct codebase read — `backend/app/modules/screener_v2/service.py` — confirmed `query_tesouro_rates()` pattern to copy
- Direct codebase read — `backend/app/modules/screener_v2/schemas.py` — confirmed `HOLDING_PERIODS`, `FixedIncomeCatalogRow`, `IRBreakdown` schemas
- Direct codebase read — `backend/app/modules/comparador/service.py` — confirmed Redis CDI read + compound return math
- Direct codebase read — `frontend/src/features/screener_v2/components/RendaFixaContent.tsx` — confirmed existing component state and gaps
- Direct codebase read — `frontend/src/features/screener_v2/hooks/useRendaFixa.ts` — confirmed hook pattern for `useMacroRates`
- Direct codebase read — `frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx` — confirmed useMemo + toggle button pattern
- Direct codebase read — `backend/tests/test_screener_universe.py` — confirmed test pattern for new endpoint tests
- Direct codebase read — `frontend/e2e/tools.spec.ts` — confirmed existing E2E test for /renda-fixa

### Secondary (MEDIUM confidence)
- Redis key structure from multiple grep results across 8 backend files — `market:macro:cdi` and `market:macro:ipca` confirmed as real keys

### Tertiary (LOW confidence)
- IPCA value format (annual vs monthly) in Redis — not directly verified by reading `market_data/tasks.py` IPCA write logic; flagged as Open Question 1

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all confirmed from direct file reads, no new dependencies
- Architecture: HIGH — all patterns have exact precedent files in codebase
- Pitfalls: HIGH — derived from actual data shape mismatches visible in existing code
- Beat indicator math: MEDIUM — compound return math confirmed, but IPCA storage format unverified

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable backend, patterns unlikely to change)
