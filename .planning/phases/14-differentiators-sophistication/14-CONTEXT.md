# Phase 14: Differentiators & Sophistication - Context

**Gathered:** 2026-04-03
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 14 adds quality validation, monitoring, and frontend components for the analysis features built in Phase 13. Most backend functionality (LLM narratives, sensitivity, custom assumptions) already exists — this phase focuses on hardening, testing, and making them user-facing.

**Requirements:** AI-05, AI-06, AI-07

**Already implemented in Phase 13 (backend):**
- LLM narratives generated for all 3 analysis types (DCF, earnings, dividend) via `call_analysis_llm()`
- Sensitivity analysis (bear/base/bull) in `calculate_dcf_with_sensitivity()`
- Custom assumptions accepted via DCF endpoint (growth_rate, discount_rate, terminal_growth)
- Cost tracking per analysis via `log_analysis_cost()`
- Fallback chain: OpenRouter -> Groq -> cached result with "outdated" badge

**What Phase 14 must add:**
1. Narrative quality validation (test suite ensuring no hallucination)
2. Sector peer comparison analysis (AI-04 — the 4th analysis type not yet built)
3. Frontend components for sensitivity display and custom assumption input
4. Cost monitoring/ops dashboard or admin endpoint
5. Integration tests for full analysis flow

</domain>

<decisions>
## Implementation Decisions

### Sector Comparison (AI-04 — NEW)
- Backend: `sector.py` module, `run_sector` Celery task, `POST /analysis/sector` endpoint
- Fetch peers by `sector_key` from BRAPI, compare P/E, P/B, DY, ROE across 5-10 peers
- Reuse `fetch_fundamentals()` from data.py (already caches)
- SectorRequest schema already exists (ticker + max_peers)

### Narrative Quality
- Test suite with mocked LLM responses validating no hallucinated tickers/metrics
- Prompt engineering improvements if needed
- PT-BR language consistency checks

### Frontend Components
- Sensitivity table/chart showing bear/base/bull fair values
- Custom assumptions form (growth rate slider 0-20%, discount rate 0-30%, terminal growth 0-5%)
- "Recalculate" button that dispatches new DCF job with custom params
- Cost dashboard: admin-only endpoint showing analysis costs per type/day

### Claude's Discretion
- Frontend component library choices (existing Next.js + Tailwind)
- Chart library for sensitivity visualization
- Admin dashboard implementation details

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `.planning/ROADMAP.md` — Phase 14 scope and success criteria
- `.planning/REQUIREMENTS.md` — AI-04, AI-05, AI-06, AI-07 definitions
- `.planning/STATE.md` — Current project state
- `.planning/phases/13-core-analysis-engine/13-01-SUMMARY.md` — DCF implementation details
- `.planning/phases/13-core-analysis-engine/13-02-SUMMARY.md` — Earnings + dividend implementation
- `.planning/phases/13-core-analysis-engine/13-RESEARCH.md` — BRAPI field mapping
- `backend/app/modules/analysis/` — All Phase 12-13 backend code
- `backend/app/modules/analysis/tasks.py` — Existing task patterns to follow
- `backend/app/modules/analysis/router.py` — Existing endpoint patterns
- `backend/app/modules/analysis/data.py` — BRAPI data layer (fetch_fundamentals)
- `backend/app/modules/analysis/dcf.py` — DCF with sensitivity
- `backend/app/modules/analysis/schemas.py` — SectorRequest already defined

</canonical_refs>
