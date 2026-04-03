# Phase 16: Frontend Integration & Launch - Research

**Researched:** 2026-04-03
**Domain:** Next.js 15 / React 19 frontend integration, async polling UX, stock detail page, E2E testing
**Confidence:** HIGH (all findings from direct source file inspection)

---

## Summary

Phase 16 is a pure integration phase — all backend analysis APIs (DCF, earnings, dividend, sector) are complete and working. The frontend already has a polling infrastructure (`useAnalysisJob` with React Query's `refetchInterval`) and a `DisclaimerBadge` component. There is **no stock detail page** yet — the app currently has per-feature pages (`/ai`, `/screener`, `/wizard`) but no `/stock/[ticker]` or `/ativo/[ticker]` route. Phase 16 must create this unified route.

**No WebSocket infrastructure exists** in either backend or frontend. The codebase uses HTTP polling for async jobs (2-second intervals in `useWizard`, 2-second intervals in `useAnalysisJob`). The wizard's `useWizard.ts` hook uses `setInterval`, while the newer `useAnalysisJob.ts` uses React Query's `refetchInterval`. React Query's approach is more idiomatic and should be the standard for this phase. For 30-60 second analysis jobs, polling at 3-second intervals is appropriate — adding WebSocket infrastructure would require a backend library, new connection management, and nginx proxy config. Polling is the right call here.

**Primary recommendation:** Build `/stock/[ticker]` page using React Query polling (same pattern as `useAnalysisJob`), create 4 analysis section components, reuse existing `DisclaimerBadge`, add data freshness display. No WebSocket implementation needed — polling covers the 30-60s job latency cleanly.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AI-14 | Per-stock detail page displays analysis results (single unified view, not scattered) | New `/stock/[ticker]` Next.js route needed; 4 analysis section components; triggers all 4 job types on load |
| AI-15 | Analysis load time target 30-60s (async job, progress indicator, WebSocket notification on complete) | React Query polling at 3s intervals is sufficient; "Calculando..." spinner pattern from existing `AnalysisRequestForm` is the template; no WebSocket infra needed |
</phase_requirements>

---

## Standard Stack

### Core (already installed — no new packages needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.2.3 | App Router, file-based routing, `/api/*` rewrite proxy | Already deployed in prod |
| React | 19.0.0 | Component model, hooks | Already in use |
| @tanstack/react-query | 5.90.21 | `refetchInterval` polling for async jobs | Already used in `useAnalysisJob` |
| Tailwind CSS | 3.4.17 | Styling | All existing components use Tailwind |
| Recharts | 2.15.4 | Charts for earnings history, DCF scenarios | Already installed |
| lucide-react | 0.474.0 | Icons (spinner, info, warning) | Already used across components |

### Supporting (existing patterns)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| @playwright/test | 1.58.2 | E2E integration tests | New `/stock/[ticker]` spec file |
| pytest + httpx | (existing) | Backend integration tests | `test_phase16_integration.py` |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| React Query polling | WebSocket (socket.io, native WS) | WS requires FastAPI `websockets` dep, nginx WS proxy config, client reconnect logic — polling is adequate for 30-60s jobs |
| React Query polling | Server-Sent Events (SSE) | SSE requires streaming response from FastAPI, new endpoint — polling is simpler and already working |

**Installation:** No new packages required. All dependencies already present.

---

## Architecture Patterns

### Recommended Project Structure

```
frontend/src/
├── app/
│   └── stock/
│       └── [ticker]/
│           └── page.tsx          # New: stock detail route
├── features/
│   └── analysis/                  # New feature directory
│       ├── api.ts                 # API calls to /analysis/* endpoints
│       ├── types.ts               # AnalysisJobStatus, result types per analysis type
│       ├── hooks/
│       │   ├── useAnalysisPolling.ts   # React Query polling hook (reuse useAnalysisJob pattern)
│       │   └── useStockAnalysis.ts     # Orchestrates all 4 jobs for a ticker
│       └── components/
│           ├── AnalysisDisclaimer.tsx  # Upgraded DisclaimerBadge + data freshness
│           ├── DCFSection.tsx          # Fair value, range, upside, scenarios
│           ├── EarningsSection.tsx     # EPS history, CAGR, quality metrics
│           ├── DividendSection.tsx     # Yield, payout, sustainability flag
│           ├── SectorSection.tsx       # Peer comparison table/chart
│           ├── NarrativeSection.tsx    # LLM narrative text
│           └── AnalysisLoadingSkeleton.tsx  # "Calculando..." spinner skeleton
```

### Pattern 1: React Query Polling for Async Job (canonical)

**What:** POST to start job → receive job_id → poll GET /{job_id} with `refetchInterval` until completed/failed
**When to use:** All 4 analysis types follow this pattern

```typescript
// Source: frontend/src/features/ai/hooks/useAnalysisJob.ts (existing)
export function useAnalysisPolling(jobId: string | null) {
  return useQuery({
    queryKey: ["analysis", "job", jobId],
    queryFn: () => getAnalysisResult(jobId!),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "completed" || status === "failed") return false;
      return 3000; // 3s for analysis jobs (vs 2s for wizard — jobs are longer)
    },
  });
}
```

### Pattern 2: Orchestrated Multi-Job Hook

**What:** Single hook that triggers all 4 analysis types and tracks their independent job IDs
**When to use:** Stock detail page needs all 4 simultaneously

```typescript
// New pattern for Phase 16
export function useStockAnalysis(ticker: string) {
  // State: jobIds for each analysis type
  const [jobIds, setJobIds] = useState<Record<string, string | null>>({
    dcf: null, earnings: null, dividend: null, sector: null
  });
  
  // 4 independent polling queries
  const dcf = useAnalysisPolling(jobIds.dcf);
  const earnings = useAnalysisPolling(jobIds.earnings);
  const dividend = useAnalysisPolling(jobIds.dividend);
  const sector = useAnalysisPolling(jobIds.sector);
  
  // On mount: POST to start all 4 jobs
  useEffect(() => {
    startAllAnalysis(ticker).then(ids => setJobIds(ids));
  }, [ticker]);
  
  return { dcf, earnings, dividend, sector };
}
```

### Pattern 3: Section Skeleton Loading

**What:** Each section renders independently — shows spinner until its job completes
**When to use:** All 4 sections load in parallel, each populates as it finishes

```typescript
function DCFSection({ jobId }: { jobId: string | null }) {
  const { data: job } = useAnalysisPolling(jobId);
  
  if (!jobId || job?.status === "pending" || job?.status === "running") {
    return <AnalysisLoadingSkeleton title="Valuation DCF" />;
  }
  if (job?.status === "failed") {
    return <AnalysisErrorCard message={job.error_message} />;
  }
  // job.status === "completed"
  return <DCFResultCard result={job.result} />;
}
```

### Pattern 4: CVM Disclaimer Placement

**What:** Full disclaimer shown at top of analysis section, before any results
**When to use:** Must be non-dismissible and visible before user reads analysis

```typescript
// Upgrade existing DisclaimerBadge with data freshness
function AnalysisDisclaimer({ dataTimestamp }: { dataTimestamp?: string }) {
  return (
    <div className="rounded-lg bg-amber-50 border border-amber-200 p-4 mb-6">
      <p className="text-sm text-amber-800 font-medium">
        Análise informativa — não constitui recomendação de investimento pessoal 
        (CVM Res. 19/2021). Consulte um assessor financeiro registrado.
      </p>
      {dataTimestamp && (
        <p className="text-xs text-amber-600 mt-1">
          Dados de: {new Date(dataTimestamp).toLocaleDateString("pt-BR")}
        </p>
      )}
    </div>
  );
}
```

### Anti-Patterns to Avoid

- **Single "Analyze" button for all 4 types:** Forces sequential analysis. Start all 4 jobs in parallel on page load (quota already enforced server-side).
- **Blocking page load on analysis:** Stock detail page must render instantly with skeleton sections; analysis populates async.
- **WebSocket implementation:** No existing infrastructure; polling at 3s is adequate and already tested.
- **Re-using `/ai` page pattern:** The existing `/ai` feature is a form-based "request on demand" UI. The new stock detail page should auto-start analysis on load (for Pro users) or show an "Analyze" CTA (for free users hitting quota).
- **Displaying job_id in the URL:** Job IDs are UUIDs; the URL should be `/stock/[ticker]` only.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Polling async jobs | Custom interval + fetch | React Query `refetchInterval` | Already implemented in `useAnalysisJob`; handles cleanup, deduplication, caching |
| API calls | Raw `fetch()` in components | `apiClient()` from `@/lib/api-client` | Handles credentials, error parsing, LimitError typing |
| CVM disclaimer text | New disclaimer component | Extend existing `DisclaimerBadge` | Already CVM-compliant text; just add data freshness prop |
| Chart for DCF scenarios | Custom SVG | Recharts `BarChart` or `LineChart` | Already installed for earnings history |
| E2E test helpers | New login/page utilities | `helpers.ts` (`login`, `pageIsOk`) | Already present with prod test credentials |

---

## API Shape Reference

### Backend Endpoints (all exist, Phase 12-14 delivered)

```
POST /analysis/dcf         → { job_id, status: "pending", message }
POST /analysis/earnings    → { job_id, status: "pending", message }
POST /analysis/dividend    → { job_id, status: "pending", message }
POST /analysis/sector      → { job_id, status: "pending", message }
GET  /analysis/{job_id}    → AnalysisResponse
```

### AnalysisResponse shape (from schemas.py)

```typescript
interface AnalysisResponse {
  analysis_id: string;
  analysis_type: "dcf" | "earnings" | "dividend" | "sector";
  ticker: string;
  status: "pending" | "running" | "completed" | "failed" | "stale";
  result: AnalysisResult | null;  // type varies per analysis_type
  data_metadata: DataMetadata | null;
  disclaimer: string;
  error_message: string | null;
}
```

### DCF result dict (from tasks.py)

```typescript
interface DCFResult {
  ticker: string;
  fair_value: number;
  fair_value_range: { low: number; high: number };
  current_price: number;
  upside_pct: number | null;
  assumptions: { growth_rate: number; discount_rate: number; terminal_growth: number; selic_rate: number; beta: number | null };
  projected_fcfs: number[];
  key_drivers: string[];
  scenarios: { bear: object; base: object; bull: object };
  narrative: string;
  data_completeness: object;
  data_version_id: string;
  data_timestamp: string;  // ISO 8601
  data_sources: Array<{ source: string; type: string; date: string }>;
  disclaimer: string;
}
```

### Earnings result dict

```typescript
interface EarningsResult {
  ticker: string;
  eps_history: Array<{ year: number; eps: number }>;
  eps_cagr_5y: number | null;
  quality_metrics: { earnings_quality: string; accrual_ratio: number | null; fcf_conversion: number | null };
  narrative: string;
  data_completeness: object;
  data_version_id: string;
  data_timestamp: string;
}
```

### Dividend result dict

```typescript
interface DividendResult {
  ticker: string;
  current_yield: number | null;
  payout_ratio: number | null;
  coverage_ratio: number | null;
  consistency: { score: number };
  sustainability: "safe" | "warning" | "risk";
  dividend_history: Array<{ year: number; dps: number }>;
  narrative: string;
}
```

### Sector result dict

```typescript
interface SectorResult {
  ticker: string;
  sector: string;
  sector_key: string;
  peers_found: number;
  peers_attempted: number;
  target_metrics: { pe_ratio: number | null; price_to_book: number | null; dividend_yield: number | null; roe: number | null };
  sector_averages: object;
  sector_medians: object;
  target_percentiles: object;
  peers: Array<{ ticker: string; metrics: object }>;
  narrative: string;
  data_completeness: object;
}
```

---

## Async Loading UX Pattern

### Recommended: Parallel job start + independent section polling

1. User navigates to `/stock/PETR4`
2. Page renders immediately with 4 skeleton sections + full CVM disclaimer above
3. `useStockAnalysis("PETR4")` fires on mount: POST 4 jobs simultaneously
4. Each section polls its own job_id at 3s intervals
5. Sections populate independently as their jobs complete (DCF likely first ~15s, sector last ~45s)
6. No page refresh needed — React Query state updates re-render the section

### Quota Gate UX

- If user is on Free plan: Show "Upgrade para Pro para ver análises" CTA instead of auto-starting jobs
- If quota exhausted: Show "Você atingiu o limite de análises este mês" with upgrade link
- Error response from POST is `403 QUOTA_EXCEEDED` or `403 LIMIT` — `apiClient` parses this as `LimitError`

### Polling vs WebSocket Decision

**Verdict: Use polling.** Rationale:
- Backend has zero WebSocket infrastructure — would require `fastapi-websockets`, Redis pub/sub or Celery task result channel, nginx proxy upgrade, client reconnect logic
- Analysis jobs complete in 15-60s — 3s polling = max 20 round trips per job, negligible load
- `useAnalysisJob` hook already exists and is battle-tested in production
- p95 latency SLA is 30s — at 3s polling, user sees result within 3s of completion
- WebSocket provides ~3s improvement at 10x implementation complexity

---

## Common Pitfalls

### Pitfall 1: Starting jobs on every render

**What goes wrong:** If analysis jobs are started in `useEffect` without proper dependency tracking, navigating back/forth to a stock page triggers new jobs on every visit, consuming quota unnecessarily.

**Why it happens:** React StrictMode double-invokes effects; missing cleanup.

**How to avoid:** Check if a job already exists for the ticker+tenant in the current session before POSTing. Store job IDs in component state (not React Query cache) — job IDs are single-use per page visit.

**Warning signs:** Quota depleting faster than expected; duplicate job records in DB.

### Pitfall 2: Displaying stale analysis from wrong job type

**What goes wrong:** All 4 analysis types return `AnalysisResponse` with identical shape. If job_id references are mixed up, DCF section could render earnings data.

**Why it happens:** All 4 POST endpoints return the same `AnalysisJobStatus` schema — easy to misassign the returned `job_id` to the wrong state variable.

**How to avoid:** Type-safe state: `{ dcf: string | null; earnings: string | null; dividend: string | null; sector: string | null }` — never use array indexing.

### Pitfall 3: CVM disclaimer hidden on mobile

**What goes wrong:** Success criteria explicitly states "users cannot scroll past disclaimer on mobile." If disclaimer is placed at bottom or hidden behind a tab, this fails.

**Why it happens:** Designers position disclaimers below the fold.

**How to avoid:** Disclaimer must be the first visible element in the analysis section, before any result cards. Test on 375px viewport in Playwright.

### Pitfall 4: Quota consumed even when analysis fails immediately

**What goes wrong:** `increment_quota_used` is called in the router after job creation, before the Celery task runs. If data fetch fails (stock not in BRAPI), quota is still consumed.

**Why it happens:** Quota increment in router (Phase 12 design decision).

**How to avoid:** Frontend should handle `job?.status === "failed"` gracefully. Show "Dados insuficientes para análise" with explanation. Do not retry automatically.

### Pitfall 5: Next.js App Router and `"use client"` for polling

**What goes wrong:** React Query hooks require Client Components. Forgetting `"use client"` causes "Hooks can only be called inside a function component" error.

**Why it happens:** Next.js 15 defaults to Server Components.

**How to avoid:** Stock detail page is a hybrid: outer `page.tsx` is Server Component (for metadata), inner analysis content is Client Component. Pattern established in `AIContent.tsx`, `AcoesScreenerContent.tsx`.

### Pitfall 6: `/stock/[ticker]` route conflict with app directory

**What goes wrong:** Next.js App Router requires `[ticker]` folder with `page.tsx`. Creating the wrong directory structure (`stock.tsx` without bracket folder) results in 404.

**How to avoid:** Directory structure: `src/app/stock/[ticker]/page.tsx` — the bracket is part of the folder name.

---

## E2E Test Strategy

### New spec file: `e2e/stock-detail.spec.ts`

Pattern follows `e2e/ai-features.spec.ts` exactly: `login()` + `pageIsOk()` helpers.

**Test groups:**

1. **Smoke:** `/stock/PETR4` loads without JS errors, redirects to login if unauthenticated
2. **Regression:** Page shows all 4 section headings (DCF, Earnings, Dividend, Sector), disclaimer is visible above results, "Calculando..." appears while polling
3. **Integration:** For Pro user — submit all 4 analyses, poll until all sections show completed state or fail gracefully (no crash), verify disclaimer text visible

```typescript
// Pattern: wait up to 90s for analysis sections to populate
test('stock detail page loads PETR4 analysis', async ({ page }) => {
  await login(page);
  await page.goto('/stock/PETR4');
  // Disclaimer must be visible immediately (before analysis completes)
  await expect(page.getByText(/recomendação de investimento/i)).toBeVisible({ timeout: 5000 });
  // Sections eventually populate (up to 90s for p99 latency)
  await page.waitForTimeout(30000);
  const body = await page.textContent('body');
  expect(body).toMatch(/DCF|Valuation|Calculando/i);
});
```

### Backend integration test: `test_phase16_integration.py`

**Key tests:**
1. Start all 4 analysis jobs for same ticker → all 4 return distinct job_ids with `status: "pending"`
2. Poll `GET /analysis/{job_id}` → status transitions `pending → running → completed`
3. Tenant isolation: Job created by tenant A returns 404 when queried by tenant B
4. Quota gate: After quota exhausted, 5th POST returns 403 with `QUOTA_EXCEEDED`
5. E2E smoke: Mock Celery task execution → verify result_json shape matches TypeScript interfaces

### Tenant Isolation Security Test

The `test_rls.py` file already tests PostgreSQL RLS at the DB layer. For analysis jobs:

```python
# Pattern: create job as tenant_a, attempt GET as tenant_b
async def test_analysis_tenant_isolation(client_a, client_b):
    # POST job as tenant_a
    resp = await client_a.post("/analysis/dcf", json={"ticker": "PETR4"})
    job_id = resp.json()["job_id"]
    
    # GET as tenant_b → must return 404
    resp = await client_b.get(f"/analysis/{job_id}")
    assert resp.status_code == 404  # Not 403 — don't leak that job exists
```

This test verifies the `tenant_id == tenant_id` filter in `get_analysis_result()` router function.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (backend), Playwright (E2E) |
| Config file | `backend/tests/conftest.py` (SQLite in-memory, fakeredis) |
| Quick run command | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_phase16_integration.py -x -q` |
| Full suite command | `cd D:/claude-code/investiq/backend && python -m pytest tests/ -q` |
| E2E command | `cd D:/claude-code/investiq/frontend && npx playwright test e2e/stock-detail.spec.ts` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AI-14 | Stock detail page renders all 4 analysis sections | E2E (Playwright) | `npx playwright test e2e/stock-detail.spec.ts` | ❌ Wave 0 |
| AI-14 | Each section shows correct result type | Unit (pytest) | `pytest tests/test_phase16_integration.py::test_section_types` | ❌ Wave 0 |
| AI-15 | Sections show spinner while job pending | E2E | `npx playwright test e2e/stock-detail.spec.ts --grep "spinner"` | ❌ Wave 0 |
| AI-15 | Sections populate without page refresh | E2E | `npx playwright test e2e/stock-detail.spec.ts --grep "realtime"` | ❌ Wave 0 |
| AI-09 | CVM disclaimer visible before scroll on mobile | E2E | `npx playwright test e2e/stock-detail.spec.ts --grep "disclaimer"` | ❌ Wave 0 |
| Tenant isolation | Job from tenant A returns 404 for tenant B | Integration (pytest) | `pytest tests/test_phase16_integration.py::test_tenant_isolation` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_phase16_integration.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -q` (full 257+ test suite)
- **Phase gate:** Full suite green + E2E stock-detail spec passing before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_phase16_integration.py` — covers AI-14 backend contract, AI-15 job lifecycle, tenant isolation
- [ ] `frontend/e2e/stock-detail.spec.ts` — covers AI-14 UI rendering, AI-15 async UX, AI-09 disclaimer placement

---

## Recommended Plan Structure (3 plans)

### Plan 16-01: Stock Detail Page + Analysis Feature Module

**Scope:** Create the `/stock/[ticker]` route and all display components.

Tasks:
1. Create `src/app/stock/[ticker]/page.tsx` (Client Component wrapper)
2. Create `src/features/analysis/api.ts` — typed wrappers for 4 POST endpoints + GET polling
3. Create `src/features/analysis/types.ts` — TypeScript interfaces for all 4 result shapes
4. Create `src/features/analysis/hooks/useAnalysisPolling.ts` (React Query, 3s refetchInterval)
5. Create `src/features/analysis/hooks/useStockAnalysis.ts` (orchestrates 4 parallel jobs)
6. Create `src/features/analysis/components/AnalysisDisclaimer.tsx` (full text + data freshness)
7. Create `src/features/analysis/components/DCFSection.tsx`
8. Create `src/features/analysis/components/EarningsSection.tsx`
9. Create `src/features/analysis/components/DividendSection.tsx`
10. Create `src/features/analysis/components/SectorSection.tsx`
11. Create `src/features/analysis/components/AnalysisLoadingSkeleton.tsx`
12. Wire up: quota gate for Free users, error states for failed jobs
13. Add `/stock/[ticker]` link from screener rows (make ticker clickable)

### Plan 16-02: Backend Integration Test + Tenant Isolation

**Scope:** Integration tests for full E2E flow and security verification.

Tasks:
1. Create `backend/tests/test_phase16_integration.py`:
   - Start all 4 jobs for same ticker → verify 4 distinct job_ids
   - Poll until completed → verify result JSON structure matches expected types
   - Tenant isolation: tenant B cannot read tenant A's jobs
   - Quota gate: POST fails with 403 after quota exhausted
   - Mock Celery execution to test full lifecycle in-process
2. Run full test suite → verify 257+ tests still pass
3. Verify `test_rls.py` analysis_jobs table covered

### Plan 16-03: E2E Tests + Production Launch

**Scope:** Playwright E2E tests, production validation, production toggle.

Tasks:
1. Create `frontend/e2e/stock-detail.spec.ts`:
   - Smoke: page loads, redirects unauthenticated
   - Regression: disclaimer visible, sections render, no JS errors
   - Integration: analysis lifecycle visible (spinner → result)
   - Mobile: disclaimer visible on 375px viewport
2. Run E2E suite against staging → verify all tests pass
3. Production load test: 100 concurrent users, verify p50 <15s, p95 <30s, p99 <60s
4. Verify cache hit rate >75% (repeat analysis for same ticker)
5. Deploy to production via docker cp + docker compose restart
6. Post-deploy smoke: verify `/stock/PETR4` renders without errors in production

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WebSocket for async job notification | React Query `refetchInterval` polling | v1.1 wizard (Phase 7) | Simpler, no infra, same UX for 30-60s jobs |
| Per-page AI analysis forms | Unified stock detail page | Phase 16 | Single place for all 4 analysis types per stock |
| Disclaimer in TOS only | On-feature DisclaimerBadge | Phase 12 | CVM compliance (existing component to extend) |

---

## Open Questions

1. **Should `/stock/[ticker]` be accessible to Free users?**
   - What we know: Free quota = 0 analyses/month. Premium gate pattern exists (`PremiumGate` component in `features/ai`).
   - What's unclear: Should Free users see the stock detail page with a "Upgrade" CTA, or be redirected to `/planos`?
   - Recommendation: Show the page with analysis sections locked behind a CTA — same pattern as `PremiumGate`. This gives Free users a preview of the feature.

2. **Do we start all 4 jobs on page load, or let user choose?**
   - What we know: Each job costs 1 quota point (Pro: 50/month total). 1 stock visit = 4 points.
   - What's unclear: Is consuming 4 quota points per stock visit acceptable to Pro users?
   - Recommendation: Start all 4 on page load for maximum UX speed. At 50 points/month, Pro users get 12 full stock analyses. Add a "Refresh" button per section for manual re-analysis.

3. **Where to link from the screener to the stock detail page?**
   - What we know: `AcoesScreenerContent.tsx` renders `AcaoTableRow` — ticker is displayed but not linked.
   - What's unclear: Whether navigating to `/stock/[ticker]` should preserve screener scroll position.
   - Recommendation: Make ticker in screener rows a Next.js `<Link>` to `/stock/[ticker]`. Scroll preservation not required for v1.2.

---

## Sources

### Primary (HIGH confidence)

- `D:/claude-code/investiq/frontend/src/features/ai/hooks/useAnalysisJob.ts` — existing polling hook, canonical pattern for Phase 16
- `D:/claude-code/investiq/frontend/src/features/wizard/hooks/useWizard.ts` — original polling hook (setInterval approach, superseded by React Query approach)
- `D:/claude-code/investiq/backend/app/modules/analysis/router.py` — confirmed: no WebSocket, polling-only design; 4 POST endpoints + GET/{job_id}
- `D:/claude-code/investiq/backend/app/modules/analysis/schemas.py` — AnalysisResponse shape, all fields confirmed
- `D:/claude-code/investiq/backend/app/modules/analysis/tasks.py` — confirmed result dict structure for all 4 analysis types
- `D:/claude-code/investiq/frontend/package.json` — stack: Next.js 15.2.3, React 19, React Query 5.90.21, Recharts 2.15.4, Playwright 1.58.2
- `D:/claude-code/investiq/frontend/src/app/` — confirmed: no `/stock/[ticker]` route exists yet
- `D:/claude-code/investiq/frontend/src/features/ai/components/DisclaimerBadge.tsx` — existing CVM disclaimer component
- `D:/claude-code/investiq/backend/app/modules/analysis/constants.py` — CVM_DISCLAIMER_PT (full), CVM_DISCLAIMER_SHORT_PT
- `D:/claude-code/investiq/frontend/e2e/helpers.ts` — test credentials: `playtest@investiq.com.br`
- `D:/claude-code/investiq/.planning/config.json` — `nyquist_validation: true` confirmed

### Secondary (HIGH confidence — same codebase)

- `D:/claude-code/investiq/backend/tests/test_rls.py` — tenant isolation test pattern confirmed
- `D:/claude-code/investiq/backend/tests/conftest.py` — SQLite in-memory, fakeredis, httpx AsyncClient pattern
- `D:/claude-code/investiq/.planning/STATE.md` — stack decisions, deploy pattern

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — read package.json directly
- Architecture: HIGH — based on existing patterns in wizard, ai-features, all confirmed from source
- API shape: HIGH — read router.py, schemas.py, tasks.py result dicts directly
- Pitfalls: HIGH — derived from existing code patterns and known React/Next.js behaviors
- E2E test strategy: HIGH — based on existing Playwright spec structure

**Research date:** 2026-04-03
**Valid until:** 2026-05-03 (stack is stable; Phase 15 data quality work does not change API shape)
