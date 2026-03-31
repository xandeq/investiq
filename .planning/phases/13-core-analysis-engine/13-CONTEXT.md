# Phase 13: Core Analysis Engine - Context

**Gathered:** 2026-03-31
**Status:** Ready for planning

<domain>
## Phase Boundary

Deliver MVP analysis features (DCF, earnings, dividends, sector comparison) with async job pattern reused from wizard. Replace Phase 12 stubs (`_fetch_fundamentals_stub`, `_calculate_dcf_stub`) with real implementations. Add 3 new Celery tasks (earnings, dividend, sector) following the `run_dcf` pattern.

</domain>

<decisions>
## Implementation Decisions

### DCF Methodology
- **D-01:** 2-Stage FCFF model — 5-year explicit growth period + terminal value
- **D-02:** Formula: `Fair Value = Σ FCF_t/(1+WACC)^t + TV/(1+WACC)^5` where `TV = FCF_5 * (1+g_terminal) / (WACC - g_terminal)`
- **D-03:** WACC via CAPM: `Ke = SELIC + Beta * ERP(7%)`, Beta from BRAPI, SELIC from BCB API
- **D-04:** Fair value range via assumption sensitivity: vary growth ±2pp and discount rate ±2pp (3 DCF calculations: low/base/high)
- **D-05:** Default inputs: `growth_rate=5%`, `discount_rate=CAPM-derived`, `terminal_growth=3%`. User can override via existing `DCFRequest` fields.

### Data Sources
- **D-06:** BRAPI for stock fundamentals (price, EPS, P/E, DY, FCF, market_cap, sector, beta)
- **D-07:** BCB API for SELIC rate (endpoint: `bcdata.sgs.bcb.gov.br/dados/serie/bcdata.sgs.432/dados`). Cache 24h (SELIC changes ~6x/year)
- **D-08:** Cache all BRAPI fundamentals in Redis with 24h TTL per ticker
- **D-09:** Data attribution in every response: `"Data: BRAPI EOD [date]"`, `"Risk-free: BCB SELIC [date]"`

### DCF Output Depth
- **D-10:** Full breakdown: fair_value, range (low/high), upside_pct, assumptions table, year-by-year FCF projections, key_drivers list, LLM narrative, data_attribution
- **D-11:** Key drivers generated from sensitivity: identify which input (growth vs WACC) moves fair value most

### Earnings Output Depth
- **D-12:** 5-year EPS history with YoY growth rates + 5-year CAGR
- **D-13:** Quality metrics: accrual_ratio (good <0.20), FCF conversion rate (good >0.80), earnings_quality flag ("high"/"medium"/"low")
- **D-14:** Revenue history alongside EPS for context
- **D-15:** LLM narrative summarizing earnings trend and quality

### Dividend Output Depth
- **D-16:** Current yield, payout ratio, dividend coverage ratio
- **D-17:** 5-year consistency score (paid N of 5 years)
- **D-18:** Sustainability assessment: "safe" | "warning" | "risk" based on: payout >80%, coverage <1.2x, dividend cut in last 3 years
- **D-19:** Dividend history with per-year DPS and yield
- **D-20:** LLM narrative on dividend safety

### Sector Comparison Output Depth
- **D-21:** Metrics table: P/E, P/B, DY, EV/EBITDA for stock + 5-10 peers
- **D-22:** Stock ranked within peers for each metric (e.g., "pe_rank: 3/8, cheaper than 62%")
- **D-23:** Data completeness indicator per peer (complete: true/false)
- **D-24:** Aggregate completeness: "8/10 peers with complete data"
- **D-25:** LLM narrative comparing stock to peer group

### Peer Grouping
- **D-26:** Use B3 native sector/subsector classification (available in BRAPI `/quote` response)
- **D-27:** Minimum 3 peers required for comparison. If <3 in exact subsector, expand to parent sector
- **D-28:** Target 5-10 peers per comparison. Cap at 10 for response size

### Data Gap Handling
- **D-29:** Partial analysis + flags — never block entirely. Return whatever data is available with `data_completeness` object
- **D-30:** `data_completeness = { available: [...], missing: [...], completeness: "60%" }`
- **D-31:** DCF requires FCF — if missing, return error for DCF specifically (other analysis types may still succeed)
- **D-32:** Sector comparison includes peers with incomplete data but flags them with yellow indicator

### Claude's Discretion
- Growth rate default estimation logic (historical CAGR vs analyst consensus proxy)
- BRAPI API response parsing and field mapping details
- Exact accrual ratio formula (net income vs cash from operations)
- FCF conversion calculation method
- Celery task naming convention for new tasks (follow `analysis.run_dcf` pattern)
- Error retry logic within each analysis task
- LLM prompt engineering for each analysis narrative

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 12 Foundation (dependency)
- `backend/app/modules/analysis/models.py` — AnalysisJob model (status lifecycle, data_version_id, analysis_type field)
- `backend/app/modules/analysis/schemas.py` — DataMetadata, AnalysisResponse, DCFRequest schemas
- `backend/app/modules/analysis/tasks.py` — `run_dcf` Celery task pattern (stubs to replace: `_fetch_fundamentals_stub`, `_calculate_dcf_stub`)
- `backend/app/modules/analysis/providers.py` — LLM fallback chain (`call_analysis_llm`)
- `backend/app/modules/analysis/versioning.py` — `build_data_version_id()`, `get_data_sources()`
- `backend/app/modules/analysis/constants.py` — `QUOTA_LIMITS`, `CVM_DISCLAIMER_*`, `ANALYSIS_TYPES`
- `backend/app/modules/analysis/quota.py` — `check_analysis_quota()` (reuse in new tasks)
- `backend/app/modules/analysis/cost.py` — `log_analysis_cost()`, `estimate_llm_cost()`
- `backend/app/modules/analysis/router.py` — Existing `/analysis/dcf` and `/analysis/{job_id}` endpoints

### Requirements
- `.planning/REQUIREMENTS.md` — AI-01 (DCF), AI-02 (Earnings), AI-03 (Dividends), AI-04 (Sector)

### Existing patterns
- `backend/app/modules/wizard/tasks.py` — Wizard Celery task pattern (original async pattern Phase 13 extends)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run_dcf` task in `tasks.py`: Full pipeline template (quota check → running → compute → LLM narrative → versioning → cost log). New tasks (earnings, dividend, sector) follow this exact pattern.
- `call_analysis_llm()` in `providers.py`: LLM fallback chain ready — each analysis type just provides a different prompt.
- `AnalysisJob` model: Already supports `analysis_type` field for dcf/earnings/dividend/sector.
- `DCFRequest` schema: Has validated bounds for growth_rate (0-20%), discount_rate (0-30%), terminal_growth (0-5%).

### Established Patterns
- Celery task pattern: `@shared_task(name="analysis.run_X")` → quota check → status update → compute → LLM → versioning → cost log
- Data versioning: Every result includes `data_version_id`, `data_timestamp`, `data_sources`
- Cost tracking: Every task logs cost on both success and failure paths
- Error handling: Catch-all with `_update_job(job_id, "failed", error=str(exc))` + cost log

### Integration Points
- Router: Add new endpoints `/analysis/earnings`, `/analysis/dividend`, `/analysis/sector` following `/analysis/dcf` pattern
- Celery: Register new tasks in celery app (auto-discovered from `analysis.tasks`)
- BRAPI: Need `_fetch_fundamentals()` (real implementation replacing stub) — called by all 4 analysis types
- BCB API: New external dependency for SELIC rate — needs HTTP client + caching

</code_context>

<specifics>
## Specific Ideas

- DCF should feel like a simplified Bloomberg DCF screen — key numbers front and center, assumptions visible
- Earnings quality metrics (accrual ratio, FCF conversion) are the differentiator — most Brazilian tools just show EPS
- Sustainability flags on dividends should be immediately visible ("safe" green, "warning" yellow, "risk" red)
- Peer ranking should answer "is this stock cheap or expensive vs peers?" in one glance
- All LLM narratives in PT-BR (Portuguese), 2-3 sentences max, actionable insights

</specifics>

<deferred>
## Deferred Ideas

- CVM quarterly filings (DFP/ITR) for deeper fundamentals — Phase 15 data quality
- Monte Carlo simulation for fair value range — future enhancement
- Scatter plot coordinates for frontend charts (PE vs growth) — Phase 16 may add
- Full financials (revenue, margins, ROIC) — v2 scope
- Custom curated peer groups for top 50 stocks — manual maintenance, not MVP
- Analyst consensus data integration — no free source available

</deferred>

---

*Phase: 13-core-analysis-engine*
*Context gathered: 2026-03-31*
