# Phase 11: Wizard Onde Investir — Research

**Researched:** 2026-03-24
**Domain:** AI-powered multi-step wizard, FastAPI async job pattern, LLM output validation, Next.js 15 wizard UI
**Confidence:** HIGH — majority of code is already in place; research is primarily gap analysis + validation

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WIZ-01 | Usuário percorre wizard multi-step informando valor disponível, prazo e perfil de risco | Current WizardContent.tsx is a single-form; needs multi-step refactor with step progress indicator and back-navigation |
| WIZ-02 | IA gera alocação recomendada em percentuais por classe apenas — nunca tickers específicos | Backend validation already in `tasks.py` (`_TICKER_RE` + `_parse_and_validate`); frontend needs to never render ticker-like strings |
| WIZ-03 | Wizard lê carteira atual do usuário e inclui contexto de alocação existente na sugestão da IA | `_get_portfolio_allocation()` in tasks.py already implemented; `WizardPortfolioContext` in schemas; delta computation in tasks.py |
| WIZ-04 | Wizard inclui dados macroeconômicos atuais (SELIC, IPCA, tendência de juros) no contexto enviado à IA | `_get_macro()` in tasks.py already reads `market:macro:selic/cdi/ipca` from Redis; included in prompt |
| WIZ-05 | Disclaimer CVM é exibido obrigatoriamente antes dos resultados: "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)" | CVM_DISCLAIMER constant in schemas.py; returned in all API responses; WizardContent.tsx renders it before results — but needs enforcement in step-based UI |
</phase_requirements>

---

## Summary

Phase 11 is substantially pre-implemented. A code audit reveals that the entire backend (router, schemas, tasks, models, migration 0016) and the frontend feature module (api.ts, hooks/useWizard.ts, types.ts, WizardContent.tsx, app/wizard/page.tsx) are already written and wired into main.py and celery_app.py. The Alembic migration for `wizard_jobs` exists at `0016_add_wizard_jobs.py`.

The critical gap is **WIZ-01**: the current `WizardContent.tsx` implements a single-form UI (all three inputs — valor, prazo, perfil — visible simultaneously) rather than a multi-step wizard with a progress indicator and back-navigation. All other requirements (WIZ-02 through WIZ-05) are implemented at the backend level and partially at the frontend level.

The primary work for this phase is: (1) refactor `WizardContent.tsx` from single-form to multi-step, (2) run `alembic upgrade head` to apply migration 0016 to the VPS database, and (3) write test coverage for the wizard task's validation logic.

**Primary recommendation:** Refactor WizardContent.tsx to a 3-step wizard (Step 1: valor, Step 2: prazo, Step 3: perfil + submit) with a visual step progress indicator. The backend requires no changes — it already fully satisfies WIZ-02, WIZ-03, WIZ-04, WIZ-05.

---

## What Is Already Built (Audit Results)

### Backend — COMPLETE

| File | Status | Notes |
|------|--------|-------|
| `backend/app/modules/wizard/__init__.py` | Done | Exports router |
| `backend/app/modules/wizard/models.py` | Done | `WizardJob` SQLAlchemy model, RLS-enabled |
| `backend/app/modules/wizard/schemas.py` | Done | `WizardStartRequest`, `WizardJobResponse`, `WizardResult`, `CVM_DISCLAIMER` |
| `backend/app/modules/wizard/router.py` | Done | `POST /wizard/start` (202), `GET /wizard/{job_id}`, rate-limited |
| `backend/app/modules/wizard/tasks.py` | Done | `run_recommendation` Celery task: macro fetch, portfolio fetch, prompt build, LLM call, ticker validation, retry logic (3 attempts), delta computation |
| `backend/alembic/versions/0016_add_wizard_jobs.py` | Done | Creates `wizard_jobs` table with RLS, indexes, GRANT |
| `backend/app/main.py` | Done | `wizard_router` imported and included at `/wizard` |
| `backend/app/celery_app.py` | Done | `app.modules.wizard.tasks` registered in includes |

### Frontend — PARTIALLY DONE (WIZ-01 GAP)

| File | Status | Notes |
|------|--------|-------|
| `frontend/app/wizard/page.tsx` | Done | Server component, metadata, renders WizardContent |
| `frontend/src/features/wizard/types.ts` | Done | All TS types |
| `frontend/src/features/wizard/api.ts` | Done | `startWizard`, `getWizardJob` |
| `frontend/src/features/wizard/hooks/useWizard.ts` | Done | Polling hook, 2.5s interval, auto-stop on terminal state |
| `frontend/src/features/wizard/components/WizardContent.tsx` | **GAP** | Single-form — WIZ-01 requires multi-step with progress indicator |
| AppNav.tsx | Done | `/wizard` nav item with `Lightbulb` icon |

### Migration Status

| Migration | Status |
|-----------|--------|
| `0016_add_wizard_jobs` | Written, NOT yet applied to VPS database |

---

## Standard Stack

### Core (already in project — no new installs needed)

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| FastAPI | project version | API router, 202 pattern | In use |
| SQLAlchemy async | project version | WizardJob ORM model | In use |
| Celery | project version | Background task dispatch | In use |
| httpx | project version | Async LLM API calls | In use (provider.py) |
| Redis (sync) | project version | Macro data read in Celery task | In use |
| Next.js 15 | project version | App Router, wizard page | In use |
| TanStack Query | v5 | API polling (not used in wizard yet — uses manual setInterval) | In use elsewhere |
| Tailwind CSS | project version | All styling | In use |
| lucide-react | project version | Icons (Lightbulb in nav) | In use |

### Supporting (no new dependencies required)

The wizard uses no libraries not already in the project. The multi-step UI is pure React state — no external stepper library is needed. The existing pattern of `useState` + conditional rendering (as seen in `SimuladorContent.tsx` and `WizardContent.tsx`) is the standard for this codebase.

### Alternatives Considered

| Instead of | Could Use | Decision |
|------------|-----------|----------|
| Manual setInterval polling | TanStack Query `useQuery` with `refetchInterval` | Manual polling is already implemented and working. Switching to TQ would require wrapping with QueryClient — unnecessary complexity for this phase. |
| Multi-step with URL params (`?step=2`) | Component state `useState<number>` | State-based steps. URL params would require router logic and complicate back-navigation. State is simpler and matches existing codebase pattern. |
| Structured output (JSON mode) via OpenRouter | Regex post-processing + retry | Retry approach already implemented in tasks.py. Structured output via JSON schema is not uniformly supported across the free-tier provider pool (Groq, Cerebras, Gemini have inconsistent JSON mode implementations). Current approach is correct. |

---

## Architecture Patterns

### Backend Pattern: 202 + Async Job + Polling

This project already implements this pattern for AI analysis (Phase 4 AI engine). The wizard follows the same pattern:

```
POST /wizard/start  → 202 { job_id, status: "pending", disclaimer }
                         ↓
                    Celery task dispatched immediately
                    (wizard.run_recommendation)
                         ↓
GET /wizard/{job_id} → { status: "pending|running|completed|failed", result? }
(poll every 2.5s)
```

**Why not SSE?** SSE requires a persistent HTTP connection. The VPS deploy model (docker cp + compose restart) makes long-lived connections unreliable. Polling at 2.5s is sufficient for LLM latency (~5-15s for the free tier pool). The existing pattern in the codebase is polling — SSE would be a new infrastructure concern with no benefit.

### Frontend Pattern: Multi-Step Wizard (Component State)

The target refactor for `WizardContent.tsx`:

```typescript
// Pattern: step index + data accumulation
const [step, setStep] = useState(1); // 1 | 2 | 3
const [valorInput, setValorInput] = useState("10000");
const [prazo, setPrazo] = useState<PrazoLabel>("1a");
const [perfil, setPerfil] = useState<PerfilLabel>("moderado");

// Step progress bar
// Step 1: Valor disponível
// Step 2: Prazo (horizonte)
// Step 3: Perfil de risco + submit button
```

**Step progress indicator pattern** (pure Tailwind, no library):

```tsx
// Source: project patterns from SimuladorContent.tsx + WizardContent.tsx
function StepIndicator({ current, total }: { current: number; total: number }) {
  return (
    <div className="flex items-center gap-2 mb-6">
      {Array.from({ length: total }, (_, i) => i + 1).map((n) => (
        <div key={n} className="flex items-center">
          <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-colors ${
            n < current ? "bg-blue-500 text-white" :
            n === current ? "bg-blue-500 text-white ring-4 ring-blue-100" :
            "bg-gray-200 text-gray-500"
          }`}>{n}</div>
          {n < total && (
            <div className={`h-0.5 w-8 mx-1 ${n < current ? "bg-blue-500" : "bg-gray-200"}`} />
          )}
        </div>
      ))}
    </div>
  );
}
```

**Back-navigation rule**: Each step except step 1 has a "Voltar" button that decrements step. Inputs retain their values when navigating back (state is not reset on back).

**CVM disclaimer placement**: Must be the FIRST element in the rendered output — before step indicator, before form, before results. Currently implemented correctly in `WizardContent.tsx` (the amber box is the first child of the `space-y-6` div). This placement must be preserved in the refactored version.

### Backend Pattern: LLM Output Validation with Retry

Already implemented in `tasks.py`. Do not change this logic:

```python
# Pattern: parse → validate → retry up to 3 attempts
for attempt in range(3):
    raw = asyncio.run(call_llm(...))
    data = _parse_and_validate(raw)  # raises on ticker or bad sum
    break  # success

# _parse_and_validate:
# 1. Strip markdown fences
# 2. Extract first { ... last }
# 3. json.loads
# 4. Check required fields
# 5. Check sum == 100 (±3 tolerance)
# 6. _TICKER_RE.search(rationale) — raises if ticker found
```

**Ticker regex**: `r'\b[A-Z]{3,6}\d{1,2}\b'` — matches PETR4, VALE3, HGLG11, KNRI11. This is correct. It will not match generic words like "FII" or "CDI" (no trailing digits).

### Database Pattern: wizard_jobs with RLS

Migration 0016 follows the tenant-isolation pattern. The `wizard_jobs` table uses `app_user` GRANT (not superuser), but the job status update in tasks.py uses `get_superuser_sync_db_session()` to bypass RLS — because the Celery worker has no tenant context. This is the same pattern used by the import pipeline.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Step progress indicator | Custom CSS animation library | Pure Tailwind + React state | This codebase uses only Tailwind for UI — no external component library for this type of element |
| LLM JSON mode / schema enforcement | OpenAI structured outputs, Pydantic-AI | Current `_parse_and_validate` regex+retry pattern | Free-tier pool providers (Groq, Cerebras, Gemini) have inconsistent JSON schema enforcement; the retry approach works across all providers |
| SSE streaming for wizard result | `starlette.responses.StreamingResponse` | Current 202 + poll pattern | VPS infrastructure and provider latency make polling correct. SSE adds no UX benefit for 5-15s LLM calls |
| Custom polling hook | Manual `setInterval` | Keep existing `useWizard.ts` with setInterval | Hook is already written and correct |
| Ticker sanitization beyond current regex | NLP entity detection, broker API lookup | Current `_TICKER_RE` | The regex covers all B3 ticker patterns. Over-engineering this is a trap. |

---

## Common Pitfalls

### Pitfall 1: Resetting Step Data on Navigation
**What goes wrong:** If the step component unmounts and remounts (e.g., using conditional return instead of conditional render), state resets when user navigates back.
**Why it happens:** React unmounts components when they fall out of the render tree.
**How to avoid:** Keep all state (`valorInput`, `prazo`, `perfil`, `step`) in a single parent component. Conditionally render step content with `{step === 1 && <StepOne />}` — do not use separate sub-components with their own state.
**Warning signs:** Clicking "Voltar" causes input fields to revert to default values.

### Pitfall 2: CVM Disclaimer Rendered After Results
**What goes wrong:** Disclaimer appears below the allocation result or as a footnote.
**Why it happens:** Developer places disclaimer in the results section rather than as the page's first element.
**How to avoid:** The disclaimer `<div>` must be the first child of the wizard container — before `StepIndicator`, before the form, before results. The current `WizardContent.tsx` does this correctly; preserve this in the refactor.
**Warning signs:** Any AI result content (allocation percentages, rationale, delta) renders above the amber disclaimer box.

### Pitfall 3: Missing Alembic Migration on VPS
**What goes wrong:** Backend starts but all wizard endpoints return 500 because `wizard_jobs` table doesn't exist.
**Why it happens:** Migration 0016 is written but not yet applied to the VPS PostgreSQL.
**How to avoid:** Run `alembic upgrade head` on the VPS as the first task of this phase — before any other testing.
**Warning signs:** `POST /wizard/start` returns 500 or ProgrammingError about missing table.

### Pitfall 4: Celery Task Not Discovering wizard.run_recommendation
**What goes wrong:** `POST /wizard/start` returns 202 but job stays in `pending` forever.
**Why it happens:** Celery worker doesn't include `app.modules.wizard.tasks` in its autodiscover.
**How to avoid:** `celery_app.py` already has `app.modules.wizard.tasks` in the includes list (verified). But after VPS deploy, restart the worker: `docker compose restart worker`.
**Warning signs:** `GET /wizard/{job_id}` always returns `status: "pending"` even after 30 seconds.

### Pitfall 5: Polling Continues After Component Unmounts
**What goes wrong:** Memory leak + network requests after user navigates away from `/wizard`.
**Why it happens:** `setInterval` is not cleared on component unmount.
**How to avoid:** The existing `useWizard.ts` already returns `stopPolling` as the `useEffect` cleanup. This is correct. Do not change this pattern.
**Warning signs:** Network tab shows requests to `/wizard/{job_id}` continuing after navigating to another page.

### Pitfall 6: asyncio.run() Inside Already-Running Event Loop
**What goes wrong:** `RuntimeError: This event loop is already running` when Celery task calls `asyncio.run(call_llm(...))`.
**Why it happens:** Some Celery configurations use an event loop. `asyncio.run()` fails if called inside an existing loop.
**How to avoid:** The existing `tasks.py` uses `asyncio.run()` which is correct for standard Celery sync tasks. The `celery_app.py` must NOT set `CELERYD_POOL = "gevent"` or `"eventlet"` — these would cause this error.
**Warning signs:** Task immediately goes to `failed` with RuntimeError in logs.

---

## Code Examples

### Verified: Backend Prompt Pattern (from tasks.py)

```python
# Source: backend/app/modules/wizard/tasks.py _build_prompt()
# Pattern: f-string with mandatory JSON response format, explicit no-ticker rule
return f"""Você é um consultor financeiro brasileiro especializado em alocação de portfólio.

REGRAS OBRIGATÓRIAS:
1. Retorne APENAS um JSON válido, sem markdown, sem blocos de código
2. NUNCA mencione tickers específicos (ex: PETR4, VALE3, HGLG11) na rationale
3. Os percentuais devem somar exatamente 100

CONTEXTO MACROECONÔMICO ATUAL:
- SELIC: {macro.get('selic', 'N/D')}% a.a.
- CDI: {macro.get('cdi', 'N/D')}% a.a.
- IPCA (12 meses): {macro.get('ipca', 'N/D')}%

Retorne EXATAMENTE este JSON:
{{
  "acoes_pct": <0-100>,
  "fiis_pct": <0-100>,
  "renda_fixa_pct": <0-100>,
  "caixa_pct": <0-100>,
  "rationale": "<PT-BR, 2-4 parágrafos>"
}}"""
```

### Verified: Frontend Polling Pattern (from useWizard.ts)

```typescript
// Source: frontend/src/features/wizard/hooks/useWizard.ts
// Pattern: setInterval polling at 2500ms, auto-stop on terminal state
useEffect(() => {
  if (!jobId) return;
  pollRef.current = setInterval(async () => {
    const data = await getWizardJob(jobId);
    setJob(data);
    if (data.status === "completed" || data.status === "failed") {
      clearInterval(pollRef.current!);
      pollRef.current = null;
    }
  }, 2500);
  return () => { if (pollRef.current) clearInterval(pollRef.current); };
}, [jobId]);
```

### Verified: Ticker Validation Pattern (from tasks.py)

```python
# Source: backend/app/modules/wizard/tasks.py
_TICKER_RE = re.compile(r'\b[A-Z]{3,6}\d{1,2}\b')
# Matches: PETR4, VALE3, HGLG11, KNRI11, MXRF11
# Does NOT match: FII, CDI, SELIC, IPCA, BDR, ETF (no trailing digit)

def _parse_and_validate(raw: str) -> dict:
    # Strip markdown
    text = re.sub(r"```(?:json)?", "", raw.strip()).strip().rstrip("`").strip()
    # Extract JSON object
    start = text.find("{"); end = text.rfind("}") + 1
    data = json.loads(text[start:end])
    # Ticker check
    match = _TICKER_RE.search(str(data.get("rationale", "")))
    if match:
        raise ValueError(f"Ticker detected in rationale: {match.group()}")
    return data
```

### Target: Multi-Step Wizard Refactor Pattern

```tsx
// Source: project pattern (derived from WizardContent.tsx + SimuladorContent.tsx)
// Three steps: step 1 = valor, step 2 = prazo, step 3 = perfil + submit
export function WizardContent() {
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [valorInput, setValorInput] = useState("10000");
  const [prazo, setPrazo] = useState<PrazoLabel>("1a");
  const [perfil, setPerfil] = useState<PerfilLabel>("moderado");
  const { submit, job, status, isStarting, error, reset } = useWizard();

  // ALWAYS first: CVM disclaimer
  // Then: step indicator (when form is active)
  // Then: current step content OR processing state OR result
}
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest with asyncio_mode=auto |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd /app && python -m pytest tests/test_wizard.py -x -q` |
| Full suite command | `cd /app && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WIZ-01 | Multi-step UI renders steps 1-3 with progress indicator | Manual (UI) | Visual inspection | N/A |
| WIZ-02 | Ticker detected in rationale triggers retry / validation raises ValueError | unit | `pytest tests/test_wizard.py::test_ticker_detected_raises -x` | ❌ Wave 0 |
| WIZ-02 | Valid JSON without tickers passes validation | unit | `pytest tests/test_wizard.py::test_valid_json_passes -x` | ❌ Wave 0 |
| WIZ-03 | POST /wizard/start returns 202 + job_id | integration | `pytest tests/test_wizard.py::test_start_wizard_202 -x` | ❌ Wave 0 |
| WIZ-03 | GET /wizard/{job_id} returns job for correct tenant | integration | `pytest tests/test_wizard.py::test_get_wizard_job -x` | ❌ Wave 0 |
| WIZ-04 | Prompt includes SELIC/CDI/IPCA values | unit | `pytest tests/test_wizard.py::test_prompt_includes_macro -x` | ❌ Wave 0 |
| WIZ-05 | All API responses include CVM disclaimer string | unit | `pytest tests/test_wizard.py::test_disclaimer_in_response -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_wizard.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_wizard.py` — unit + integration tests for wizard task validation logic and API endpoints
- [ ] No new conftest needed — existing `tests/conftest.py` has `register_verify_and_login` and async fixtures

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| SSE streaming for LLM | Async job + polling | This project (Phase 4) | Simpler, VPS-compatible |
| JSON schema enforcement (OpenAI structured outputs) | Prompt-enforced JSON + retry | This project design | Provider-agnostic, works with Groq/Cerebras/Gemini free tier |
| Single-form AI wizard | Multi-step wizard (target for WIZ-01) | WIZ-01 requirement | Better UX, step-by-step guidance |

**Deprecated/outdated:**
- Streaming via SSE: Not applicable here — LLM call is 5-15s, single-response. SSE is appropriate for token-by-token streaming which this wizard does not use.

---

## Open Questions

1. **Migration 0016 applied to VPS?**
   - What we know: Migration file exists at `0016_add_wizard_jobs.py`, last migration seen on VPS was 0015 (Phase 7)
   - What's unclear: Whether 0016 (and 0017) have been applied in production
   - Recommendation: First task of Phase 11 must be `alembic upgrade head` on VPS. Run `alembic current` first to confirm current head.

2. **Three steps or two steps for WIZ-01?**
   - What we know: Three inputs required (valor, prazo, perfil). Requirements say "multi-step with progress indicator."
   - What's unclear: Whether 2 steps (valor+prazo on step 1, perfil on step 2) or 3 steps is better UX.
   - Recommendation: 3 steps (one input per step) is cleaner, makes progress indicator meaningful, and better matches the wizard pattern. Step 1: valor disponível, Step 2: horizonte de investimento, Step 3: perfil de risco + submit.

3. **Does 0017 migration need to apply before 0016 can run?**
   - What we know: `0017_drop_import_staging_unique_constraint` has `down_revision = "0016_add_wizard_jobs"`, meaning 0017 depends on 0016.
   - What's unclear: Whether 0017 was already applied on VPS (the STATE.md bug history mentions alembic stamping 0017 manually in 2026-03-23 for the imports bug fix).
   - Recommendation: Run `alembic current` on VPS to confirm. If head is already 0017, migrations are up-to-date. If head is 0015, run `alembic upgrade head` which applies 0016 then 0017.

---

## Sources

### Primary (HIGH confidence)
- `backend/app/modules/wizard/` — direct code audit (models.py, router.py, schemas.py, tasks.py)
- `backend/app/modules/ai/provider.py` — AI provider fallback chain (confirmed working per MEMORY.md 2026-03-20)
- `backend/alembic/versions/0016_add_wizard_jobs.py` — migration audit
- `frontend/src/features/wizard/` — direct code audit (all files)
- `frontend/app/wizard/page.tsx` — page already exists and wired
- `backend/app/main.py` + `celery_app.py` — wizard router and task included

### Secondary (MEDIUM confidence)
- `backend/app/modules/simulador/service.py` — reference pattern for portfolio delta computation (same logic adapted in wizard tasks.py)
- `frontend/src/features/simulador/components/SimuladorContent.tsx` — reference UI pattern (step-like UX, same Tailwind patterns)
- Project MEMORY.md (2026-03-23) — confirms 0017 alembic stamping context

### Tertiary (LOW confidence)
- None — all claims are derived from direct code inspection of the current codebase.

---

## Metadata

**Confidence breakdown:**
- What's built: HIGH — direct code audit of all files
- Gap analysis (WIZ-01 multi-step): HIGH — WizardContent.tsx is clearly single-form
- Migration status on VPS: MEDIUM — 0016 file exists locally, VPS state not confirmed
- Architecture decisions (polling vs SSE, state vs URL): HIGH — consistent with project patterns

**Research date:** 2026-03-24
**Valid until:** 2026-04-24 (stable project, no external dependencies changing)
