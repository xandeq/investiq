# Phase 18: FII Detail Page + IA Analysis — Research

**Researched:** 2026-04-04
**Domain:** FastAPI async jobs + Celery tasks + Next.js 15 + Recharts + BRAPI FII data
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCRF-04 | Usuário pode ver página de detalhe de um FII (`/fii/[ticker]`) com histórico de DY, P/VP, dados básicos do portfólio e análise IA assíncrona (narrativa sobre qualidade de dividendo, P/VP e sustentabilidade dos proventos) | Full pattern reuse from stock analysis (Phases 12-16). BRAPI dividendsData already parsed in data.py. Recharts BarChart + LineChart available. Async job pattern established. CVM disclaimer component ready. |
</phase_requirements>

---

## Summary

Phase 18 adds the FII detail page at `/fii/[ticker]`. The entire technical stack — async Celery jobs, LLM provider chain, polling hooks, CVM disclaimer, Recharts charts — already exists from v1.2 (Phases 12-16). This phase is primarily wiring existing pieces together with FII-specific data and prompts.

The `analysis` module (Phase 12-16) provides the authoritative pattern: `POST /analysis/dcf` → returns `job_id` → `GET /analysis/{job_id}` polls until `status == "completed"`. For FII analysis, the plan is to add a new endpoint `POST /fii-analysis/{ticker}` + `GET /fii-analysis/{job_id}` — either by adding a `job_type="fii"` to the existing `AnalysisJob` model or reusing `AIAnalysisJob` from `app.modules.ai.models`. The simpler choice is extending the existing `analysis` module (same DB table, same polling endpoint pattern, minimal migration footprint).

BRAPI `dividendsData.cashDividends` is already parsed in `analysis/data.py` (`fetch_fundamentals`). The existing `parsed_dividends` list (up to 20 most recent) is already stored in Redis under `brapi:fundamentals:{ticker}`. For FII detail, we need to extract the last 12 months of monthly dividends to build the DY history bar chart, and derive historical P/VP by querying BRAPI's historical price data (already implemented in `BrapiClient.fetch_historical`). The `fii_metadata` table already stores current `pvp` and `dy_12m` from Phase 17.

**Primary recommendation:** Extend `analysis` module with `job_type="fii_detail"`, add `POST /analysis/fii/{ticker}` + Celery task `run_fii_analysis`, fetch FII data via BRAPI (reusing existing `fetch_fundamentals` pattern), build BarChart (DY monthly) + LineChart (P/VP history) from Recharts already installed, and render with a `FIIDetailContent` client component mirroring `StockDetailContent`.

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI + SQLAlchemy async | existing | Backend API + DB | Already in use; no change |
| Celery + Redis | existing | Async job queue | Same task pattern as Phase 12-16 |
| Next.js 15 | 15.2.3 | Frontend framework | Existing |
| Recharts | 2.15.4 | DY bar chart + P/VP line chart | Already installed; AllocationChart.tsx proves pattern |
| @tanstack/react-query | 5.x | Job polling | `useAnalysisPolling` hook already exists |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| BRAPI | free tier | FII quotes + dividendsData + summaryProfile | FII-specific: use `modules=dividendsData,summaryProfile` |
| psycopg2 (sync) | existing | Celery task DB writes | Celery tasks are sync — same pattern as analysis/tasks.py |
| Pydantic v2 | existing | Request/response schemas | Existing across all modules |

### No New Dependencies Needed
All required libraries are already installed. No new `npm install` or `pip install` required.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/modules/analysis/
├── router.py           # ADD: POST /fii/{ticker}, GET /fii/{job_id} (or use existing GET /{job_id})
├── tasks.py            # ADD: run_fii_analysis Celery task
├── schemas.py          # ADD: FIIAnalysisRequest, FIIDataPayload schemas
└── fii_data.py         # NEW: fetch_fii_data() — BRAPI call for FII-specific fields

frontend/app/fii/[ticker]/
├── page.tsx            # NEW: thin server component (same as stock/[ticker]/page.tsx)
└── FIIDetailContent.tsx # NEW: client component with data + charts + IA card

frontend/src/features/fii_detail/
├── api.ts              # NEW: startFIIAnalysis(), getFIIAnalysisJob()
├── hooks/
│   └── useFIIAnalysis.ts  # NEW: POST on user click + polling
└── components/
    ├── FIIDYChart.tsx      # NEW: Recharts BarChart — DY monthly 12m
    ├── FIIPVPChart.tsx     # NEW: Recharts LineChart — P/VP history
    ├── FIIPortfolioSection.tsx  # NEW: portfolio data with "Dado não disponível" fallback
    └── FIIAnalysisCard.tsx # NEW: IA analysis card with spinner + disclaimer
```

### Pattern 1: FII Analysis Celery Task (mirrors run_fii_analysis in ai/tasks.py)

**What:** Sync Celery task that calls `asyncio.run()` for LLM call, updates job row via `get_superuser_sync_db_session`.
**When to use:** All FII IA analysis requests.

```python
# Source: backend/app/modules/analysis/tasks.py (existing pattern)
@shared_task(name="analysis.run_fii_analysis", bind=True, max_retries=1)
def run_fii_analysis(self, job_id: str, ticker: str, tenant_id: str) -> dict:
    _mark_job_running(job_id, tenant_id=tenant_id)
    try:
        fii_data = fetch_fii_data(ticker)  # new helper — BRAPI dividendsData
        result_text = asyncio.run(call_fii_analysis_llm(ticker, fii_data))
        result = {"job_id": job_id, "ticker": ticker, "narrative": result_text, ...}
        _mark_job_completed(job_id, result, tenant_id=tenant_id)
        return result
    except Exception as exc:
        _mark_job_failed(job_id, str(exc), tenant_id=tenant_id)
        raise
```

### Pattern 2: FII Data Fetch — BRAPI dividendsData

**What:** Fetch FII quote + dividendsData + summaryProfile from BRAPI. Same `fetch_fundamentals` base but FII-specific module list.
**When to use:** At job dispatch time, not at request time (Celery task fetches data).

```python
# Source: backend/app/modules/analysis/data.py (existing pattern adapted for FII)
def fetch_fii_data(ticker: str) -> dict:
    """Fetch FII-specific data: current price, DY history, P/VP, portfolio fields."""
    cache_key = f"brapi:fii_detail:{ticker.upper()}"
    # Check Redis cache (24h TTL — same as fundamentals)
    # Fetch: GET /v2/quote/{ticker}?modules=dividendsData,summaryProfile&token=...
    # Parse: cashDividends list for DY history, summaryProfile for portfolio fields
    # Return: {current_price, pvp, dy_12m, dividends_12m: [...], portfolio: {...}}
```

**BRAPI endpoint for FII detail:**
```
GET https://brapi.dev/api/quote/{TICKER11}?modules=dividendsData,summaryProfile&token={TOKEN}
```

**cashDividends structure** (already confirmed in `analysis/data.py`):
```python
cash_dividends = dividends_data.get("cashDividends", [])
# Each item: {"rate": float, "paymentDate": "2024-01-15", "lastDatePrior": "...", "label": "..."}
```

### Pattern 3: Frontend Polling — User-Triggered (not auto-start)

**What:** Unlike stock analysis (auto-starts on mount), FII analysis starts when user clicks "Gerar Análise IA" button.
**When to use:** FII detail page only.

```typescript
// Source: frontend/src/features/analysis/hooks/useStockAnalysis.ts (adapted)
// Key difference: triggered by user click, not useEffect on mount
export function useFIIAnalysis(ticker: string) {
  const [jobId, setJobId] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  const startAnalysis = async () => {
    setIsStarting(true);
    const { job_id } = await startFIIAnalysis(ticker);
    setJobId(job_id);
    setIsStarting(false);
  };

  const polling = useAnalysisPolling(jobId);  // reuse existing hook
  return { startAnalysis, isStarting, polling };
}
```

### Pattern 4: Recharts BarChart — DY Monthly History

**What:** 12-bar chart with month labels on X-axis, DY % on Y-axis.
**Example (based on AllocationChart.tsx pattern):**

```typescript
// Source: frontend/src/features/dashboard/components/AllocationChart.tsx (pattern)
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts";

// Data format: [{month: "Jan/24", dy: 0.85}, ...]  (values as % decimal)
<ResponsiveContainer width="100%" height={200}>
  <BarChart data={chartData}>
    <XAxis dataKey="month" tick={{ fontSize: 11 }} />
    <YAxis tickFormatter={(v) => `${(v * 100).toFixed(1)}%`} />
    <Tooltip formatter={(v: number) => `${(v * 100).toFixed(2)}%`} />
    <Bar dataKey="dy" fill="hsl(var(--chart-2))" radius={[3, 3, 0, 0]} />
  </BarChart>
</ResponsiveContainer>
```

### Pattern 5: Recharts LineChart — P/VP History

**What:** Line chart with price history. P/VP can be approximated as `regularMarketPrice / bookValue`. However, BRAPI's `/quote/{ticker}?range=1y&interval=1d` returns daily close prices, but not daily P/VP. Options:
1. Use current P/VP only (single data point) — simplest but fails the "historical" requirement
2. Use `regularMarketPrice` series + static `bookValue` to derive daily P/VP approximate — available from `BrapiClient.fetch_historical`
3. The Phase 17 `fii_metadata` only stores current `pvp`, not historical

**Recommended approach:** Fetch 1-year daily price via `fetch_historical` + use current `bookValue` from BRAPI summaryProfile as static denominator. This gives a relative price-to-book approximation over time. Alternative: show "P/VP não disponível historicamente — dado atual: X.XX" and render a single KPI card instead. Given the ROADMAP says "gráfico histórico de P/VP (linha)", use approach #2.

### Pattern 6: job_type Addition to AnalysisJob Model

**What:** Add `job_type = "fii_detail"` to existing `AnalysisJob` model (already supports `analysis_type` field as String(50)). This avoids a new DB table.

**Migration:** No schema change needed. `analysis_jobs.analysis_type` is already String(50) — just use value `"fii_detail"`.

### Anti-Patterns to Avoid
- **Auto-starting FII analysis on page mount:** Stock analysis does this, but FII analysis is a user-triggered action (per success criteria #4: "Usuário clica 'Gerar Análise IA'"). Use onClick, not useEffect.
- **New DB table for FII jobs:** Reuse `analysis_jobs` with `analysis_type="fii_detail"`. No migration needed.
- **Fetching BRAPI at request time in the router:** Always dispatch to Celery and fetch inside the task (same pattern as analysis/tasks.py).
- **Hand-rolling chart components:** Recharts is installed; use `BarChart` and `LineChart` directly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async job polling | Custom WebSocket or SSE | `useAnalysisPolling` (already exists) | Handles refetchInterval, status checks |
| LLM provider fallback | Custom retry logic | `call_analysis_llm` in `analysis/providers.py` | Already has Claude → Groq fallback chain |
| Job lifecycle (pending → running → completed) | Custom state machine | `_mark_job_running` / `_mark_job_completed` / `_mark_job_failed` helpers in `analysis/tasks.py` | Already handles superuser DB writes, RLS bypass |
| CVM disclaimer | New disclaimer component | `AnalysisDisclaimer` from `features/analysis/components/` | Already CVM-compliant |
| Bar/Line charts | Custom SVG | Recharts `BarChart` / `LineChart` | Already installed, `AllocationChart.tsx` proves the pattern |
| BRAPI token resolution | New token lookup | `_resolve_brapi_token()` in `analysis/data.py` | Handles env → AWS SM fallback |
| Redis caching | Custom cache layer | Pattern from `fetch_fundamentals` in `analysis/data.py` | TTL + cache-miss fetch already patterned |

**Key insight:** This phase is ~80% wiring and ~20% new code. The analysis module infrastructure (jobs, tasks, polling, disclaimer, LLM calls) is fully operational from v1.2.

---

## Common Pitfalls

### Pitfall 1: BRAPI MODULES_NOT_AVAILABLE for Some FII Tickers
**What goes wrong:** Some FIIs on BRAPI return 400 with `{"code": "MODULES_NOT_AVAILABLE"}` when requesting `dividendsData` or `summaryProfile` modules.
**Why it happens:** BRAPI data coverage varies by FII — smaller/less-traded FIIs may not have all modules indexed.
**How to avoid:** Implement the same fallback already in `BrapiClient.fetch_fundamentals`: catch 400+MODULES_NOT_AVAILABLE, fall back to base quote fields, return partial data.
**Warning signs:** `DataFetchError` or empty `cashDividends` list in response.

### Pitfall 2: dy_12m Already Stored in fii_metadata (Don't Double-Fetch)
**What goes wrong:** Fetching DY 12m from BRAPI live when it's already in `fii_metadata.dy_12m` (pre-calculated nightly by Phase 17 task).
**Why it happens:** Forgetting Phase 17 pre-populated this data.
**How to avoid:** For the summary header (current DY 12m, P/VP), read from `fii_metadata` via `GET /fii-screener/ranked` response — no BRAPI call needed. Only fetch BRAPI for the monthly DY history breakdown and portfolio fields that aren't in `fii_metadata`.

### Pitfall 3: cashDividends Date Format Parsing
**What goes wrong:** `paymentDate` from BRAPI can be in formats `"YYYY-MM-DD"` or `"DD/MM/YYYY"` or missing.
**Why it happens:** BRAPI inconsistency across tickers.
**How to avoid:** Use `dateutil.parser.parse()` with try/except fallback, or normalize in the `fetch_fii_data` helper before storing in Redis.

### Pitfall 4: FII Ticker Format (Always 11 chars ending in 11)
**What goes wrong:** FII tickers like `HGLG11` — user navigates to `/fii/hglg11` (lowercase).
**Why it happens:** URL case sensitivity.
**How to avoid:** Always `ticker.upper()` in both the page component and backend endpoint. Already established in `StockDetailContent` and stock analysis endpoints.

### Pitfall 5: P/VP Historical Data — bookValue is Static
**What goes wrong:** Plotting "historical P/VP" using static `bookValue` and daily prices gives a curve that represents price movement, not true P/VP movement (bookValue changes quarterly at most).
**Why it happens:** BRAPI doesn't provide daily bookValue series.
**How to avoid:** Label the chart explicitly as "Preço Histórico (base para P/VP)" or compute P/VP only for the most recent data points and show a smaller KPI set. The ROADMAP says "gráfico histórico de P/VP (linha)" — implement as `price / current_bookValue` for each historical date and label clearly as approximate.

### Pitfall 6: FII IA Analysis Should NOT Be Premium-Gated for Free Users
**What goes wrong:** Applying the same premium gate as stock analysis (`_require_premium(plan)` in `ai/router.py`) to FII analysis.
**Why it happens:** Copying the stock analysis endpoint verbatim.
**How to avoid:** Check the product decision. ROADMAP and success criteria make no mention of premium gating for FII analysis. Implement without premium gate, but WITH the standard rate limiting (5/hour via slowapi). The `analysis` module (not `ai` module) is the correct base — it has quota enforcement but is available to all users.

### Pitfall 7: Registration in celery_app.py Beat Schedule
**What goes wrong:** New `run_fii_analysis` Celery task not included in task autodiscover, causing "Received unregistered task" error.
**Why it happens:** Celery autodiscovery requires the task module to be imported.
**How to avoid:** Add `analysis.tasks` (or wherever the new task lives) to `celery_app.py` `include=` list. Already includes `"app.modules.analysis.tasks"` — adding to that file means automatic registration.

---

## Code Examples

Verified patterns from existing codebase:

### FII Analysis POST Endpoint (backend)
```python
# Pattern from: backend/app/modules/analysis/router.py (existing DCF endpoint)
@router.post(
    "/fii/{ticker}",
    response_model=AnalysisJobStatus,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["analysis"],
)
async def request_fii_analysis(
    ticker: str,
    current_user: dict = Depends(get_current_user),
    plan: str = Depends(get_user_plan),
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
):
    # Rate limit check (reuse check_analysis_rate_limit)
    # Quota check (reuse check_analysis_quota)
    # Create AnalysisJob with analysis_type="fii_detail", ticker=ticker.upper()
    # Dispatch Celery: celery_app.send_task("analysis.run_fii_analysis", ...)
    # Return 202 with job_id
```

### Polling Hook (frontend)
```typescript
// Pattern from: frontend/src/features/analysis/hooks/useAnalysisPolling.ts
// Reuse as-is. FII job_id returned by POST /analysis/fii/{ticker}
// GET /analysis/{job_id} already supports any analysis_type
const polling = useAnalysisPolling(jobId);  // zero changes needed
```

### FII Data Fetch (new helper)
```python
# Pattern from: backend/app/modules/analysis/data.py fetch_fundamentals()
def fetch_fii_data(ticker: str) -> dict:
    cache_key = f"brapi:fii_detail:{ticker.upper()}"
    # Redis cache check (same pattern)
    token = _resolve_brapi_token()
    url = f"{_BRAPI_BASE_URL}/quote/{ticker.upper()}"
    params = {"modules": "dividendsData,summaryProfile", "token": token}
    # Handle MODULES_NOT_AVAILABLE (same as fetch_fundamentals)
    # Parse: current_price, pvp, dividend history, portfolio fields
    # Cache with 24h TTL
    return {
        "current_price": ...,
        "pvp": ...,
        "dy_12m": ...,
        "dividends_monthly": [{"month": "2024-01", "rate": 0.0085}, ...],
        "portfolio": {
            "num_imoveis": ...,  # summaryProfile — may be None
            "tipo_contrato": ...,  # may be None
            "vacancia": ...,  # may be None
        },
        "last_dividend": ...,
        "daily_liquidity": ...,
    }
```

### Recharts BarChart for DY History
```typescript
// Pattern from: frontend/src/features/dashboard/components/AllocationChart.tsx
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";

// chartData: [{month: "Jan/24", dy_pct: 0.85}, ...]
<ResponsiveContainer width="100%" height={180}>
  <BarChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
    <XAxis dataKey="month" tick={{ fontSize: 10 }} />
    <YAxis tickFormatter={(v) => `${v.toFixed(1)}%`} width={36} />
    <Tooltip formatter={(v: number) => [`${v.toFixed(2)}%`, "DY"]} />
    <Bar dataKey="dy_pct" fill="hsl(var(--chart-2))" radius={[3, 3, 0, 0]} />
  </BarChart>
</ResponsiveContainer>
```

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.x (pytest.ini at backend/) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd backend && python -m pytest tests/test_phase18_fii_detail.py -x -q` |
| Full suite command | `cd backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRF-04 | `fetch_fii_data` returns expected dict structure | unit | `pytest tests/test_phase18_fii_detail.py::test_fetch_fii_data_structure -x` | ❌ Wave 0 |
| SCRF-04 | `POST /analysis/fii/{ticker}` returns 202 + job_id | integration | `pytest tests/test_phase18_fii_detail.py::test_post_fii_analysis_returns_202 -x` | ❌ Wave 0 |
| SCRF-04 | `GET /analysis/{job_id}` with fii_detail type returns result | integration | `pytest tests/test_phase18_fii_detail.py::test_get_fii_analysis_job -x` | ❌ Wave 0 |
| SCRF-04 | FII data: dividends_monthly has ≤12 entries, each has month + rate | unit | `pytest tests/test_phase18_fii_detail.py::test_dividends_monthly_format -x` | ❌ Wave 0 |
| SCRF-04 | `/fii/{ticker}` page loads without JS errors | e2e | `cd frontend && npx playwright test e2e/fii-detail.spec.ts` | ❌ Wave 0 |
| SCRF-04 | CVM disclaimer visible on FII detail page | e2e | `cd frontend && npx playwright test e2e/fii-detail.spec.ts::fii-disclaimer` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_phase18_fii_detail.py -x -q`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green + Playwright `e2e/fii-detail.spec.ts` passing before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_phase18_fii_detail.py` — all unit + integration tests for SCRF-04
- [ ] `frontend/e2e/fii-detail.spec.ts` — smoke + disclaimer regression tests

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSocket for job status | React Query `refetchInterval` polling | Phase 12 | No WebSocket infra needed; simpler |
| Separate job table per analysis type | Single `analysis_jobs` table with `analysis_type` column | Phase 12 | Reuse GET /analysis/{job_id} for all types including FII |
| `ai_analysis_jobs` (ai module) | `analysis_jobs` (analysis module) | Phase 12 | analysis module has quota, cost tracking, data versioning |

**Clarification on two job models:**
The project has TWO job models:
1. `AIAnalysisJob` in `app.modules.ai.models` — used by `ai/router.py` (macro, portfolio, asset analysis). Premium-gated.
2. `AnalysisJob` in `app.modules.analysis.models` — used by `analysis/router.py` (DCF, earnings, dividend, sector). Has quota system + plan gates.

**For Phase 18, use `AnalysisJob` (analysis module)** — it has the more complete infrastructure (quota, cost tracking, data versioning) and is what `StockDetailContent` already uses via `/analysis/` endpoints.

---

## Open Questions

1. **Is `summaryProfile.numberOfProperties` (or equivalent) actually returned by BRAPI for FII tickers?**
   - What we know: BRAPI `summaryProfile` is documented to have `sector`, `industry`, `longBusinessSummary` for stocks. FIIs may return different fields.
   - What's unclear: Whether FII-specific fields (num imóveis, tipo contrato) are actually populated.
   - Recommendation: Implement with defensive null handling — all portfolio fields use "Dado não disponível" fallback per success criteria #3. Do not make BRAPI FII portfolio fields blocking; treat them as optional enrichment.

2. **Rate limiting for FII analysis endpoint — same quota as stock analysis?**
   - What we know: Stock analysis uses `check_analysis_quota` (monthly limits per plan) and `check_analysis_rate_limit` (per-request cooldown).
   - What's unclear: Whether FII analysis should share the same quota pool or have a separate counter.
   - Recommendation: Share the same quota pool (increment the same `analysis_quota_logs` counter). Less infrastructure, same UX.

3. **Historical P/VP chart — bookValue availability for FIIs**
   - What we know: BRAPI `defaultKeyStatistics.bookValue` is available for stocks. FIIs may return this as NAV (Valor Patrimonial por Cota).
   - What's unclear: Whether BRAPI reliably returns `bookValue` for FII tickers.
   - Recommendation: Fallback gracefully — if `bookValue` is None, omit the P/VP line chart and show a single KPI badge for current P/VP from `fii_metadata`. Implement the chart as an optional section.

---

## Sources

### Primary (HIGH confidence)
- Codebase: `backend/app/modules/analysis/` — authoritative pattern for all async analysis jobs
- Codebase: `backend/app/modules/analysis/data.py` — confirmed BRAPI `dividendsData.cashDividends` parsing
- Codebase: `frontend/src/features/analysis/hooks/useAnalysisPolling.ts` — polling hook pattern
- Codebase: `frontend/src/features/dashboard/components/AllocationChart.tsx` — Recharts integration pattern
- Codebase: `frontend/package.json` — confirmed recharts 2.15.4 installed
- Codebase: `backend/app/modules/ai/models.py` + `analysis/models.py` — two-model clarification
- Codebase: `backend/app/modules/market_universe/models.py` — FIIMetadata columns (Phase 17 additions confirmed)
- Codebase: `frontend/src/features/analysis/components/AnalysisDisclaimer.tsx` — CVM disclaimer component ready

### Secondary (MEDIUM confidence)
- ROADMAP.md + STATE.md — architecture decisions and reuse guidelines documented by project author
- BRAPI documentation (via existing code usage) — dividendsData structure confirmed from `data.py` line 185-193

### Tertiary (LOW confidence)
- BRAPI summaryProfile FII-specific fields (num_imoveis, tipo_contrato) — not directly verified in existing code; defensive implementation required

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries verified present in package.json and requirements
- Architecture: HIGH — all patterns directly observed in existing codebase (analysis module)
- BRAPI data structure: HIGH (for cashDividends) / LOW (for FII portfolio fields in summaryProfile)
- Pitfalls: HIGH — derived from existing code patterns and BRAPI adapter implementation

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (BRAPI API structure is stable; internal patterns are stable)
