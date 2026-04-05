---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: Requirements to Phases Mapping
status: unknown
last_updated: "2026-04-05T08:45:09.833Z"
progress:
  total_phases: 3
  completed_phases: 2
  total_plans: 6
  completed_plans: 4
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04 after v1.3 milestone start)

**Core value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — v1.3 adds FII screener with composite score + filterable table + detail page with async IA analysis

**Current focus:** Phase 19 — opportunity-detector-page

## Current Position

Phase: 19 (opportunity-detector-page) — EXECUTING
Plan: 2 of 2

## Progress Bar

```
v1.3 FII Screener
[░░░░░░░░░░░░░░░░░░░░] 0% (0/2 phases)

Phase 17: FII Screener Table    [ NOT STARTED ]
Phase 18: FII Detail + IA       [ NOT STARTED ]
```

## v1.2 Status Reference

✅ SHIPPED 2026-04-04

| Phase | Status | Completed |
|-------|--------|-----------|
| 12. Foundation (Legal + Cost + Async) | Complete | 2026-03-31 |
| 13. Core Analysis Engine | Complete | 2026-04-03 |
| 14. Differentiators & Sophistication | Complete | 2026-04-03 |
| 15. Data Quality & Advanced Features | Complete | 2026-04-03 |
| 16. Frontend Integration & Launch | Complete | 2026-04-04 |

## Accumulated Context

### Infrastructure

- **Stack:** FastAPI + SQLAlchemy async + Next.js 15 + PostgreSQL + Redis + Celery
- **Deploy:** `docker cp` → `docker compose restart` (NOT docker build — apt-get fails on VPS network)
- **VPS:** 185.173.110.180, path: /app/financas/
- **Production:** https://investiq.com.br (frontend port 3100) + https://api.investiq.com.br (backend port 8100)
- **Stripe LIVE:** price_1TC56FCA1CPHCF6PKQ5XmUWD (R$29,90/mês)

### Data Sources

- **BRAPI:** Token available (free, 15k req/month) — B3 quotes + dividendsData + summaryProfile
- **FII endpoint:** `/v2/quote/{ticker}?modules=dividendsData,summaryProfile`
- **DY 12m:** Sum of dividendsData.cashDividends for last 12 months / current price
- **MODULES_NOT_AVAILABLE:** BRAPI can return this for some tickers — adapter must fall back to base quote fields (already implemented in v1.2 brapi.py)

### Existing FII Infrastructure (from v1.1)

- `global_fiis` table exists with FII metadata (ticker, segmento, nome)
- Celery beat FII metadata pipeline runs nightly — already fetches basic data
- `get_global_db` pattern established for global (non-tenant) tables

### v1.2 Patterns to Reuse in v1.3

- **Async job pattern:** POST analysis → returns job_id immediately → GET /analysis/{job_id} for result (Celery)
- **LLM provider chain:** Claude Haiku (OpenRouter) → Groq fallback — never hardcode keys
- **CVM disclaimer component:** Built in Phase 12 — reuse as-is for FII IA analysis
- **WebSocket polling:** Frontend polls job status, sections populate on completion
- **`get_global_db`:** FII screener data is global (not per-tenant) — same pattern as existing screener

### Testing

- **Current test count:** 257+ passing (v1.2 baseline)
- **Playwright E2E:** 72 tests passing — maintain when adding new pages

## v1.3 Architecture Decisions

### Score Formula

- `normalized_score = (DY_rank * 0.5) + (P_VP_rank * 0.3) + (liquidity_rank * 0.2)`
- Ranks are percentile (0–100) within FII universe
- DY: higher = better (higher rank = higher DY)
- P/VP: lower = better (invert rank — lower P/VP gets higher rank)
- Liquidity: higher = better (higher ADV = higher rank)
- Recalculated nightly via Celery beat after FII metadata pipeline

### Migration Strategy

- Add columns to `global_fiis`: `score`, `dy_rank`, `pvp_rank`, `liquidity_rank`, `dy_12m`, `pvp`, `daily_liquidity`, `score_updated_at`
- New migration (0020+)

### FII IA Analysis

- New Celery task: `run_fii_analysis` — reuses AnalysisJob model or new FiiAnalysisJob model
- Prompt scope: dividend quality, DY sustainability (payout > income = unsustainable), P/VP vs historical average, portfolio concentration risk
- Reuse LLM provider fallback chain from v1.2

### Frontend Pages

- `/fii/screener` — new page with table + filters (segment dropdown + DY slider)
- `/fii/[ticker]` — detail page with historical charts + portfolio section + IA analysis card

## Decisions

- **2026-04-04 Roadmap:** 2 phases for 4 requirements — natural split: screener table (Phase 17) vs detail page (Phase 18)
- **2026-04-04 Roadmap:** Reuse all v1.2 patterns: async jobs, LLM provider chain, CVM disclaimer, WebSocket polling
- **2026-04-04 Roadmap:** Score formula with percentile ranks (not absolute values) — normalizes across FII universe regardless of absolute DY/P/VP levels
- [Phase 17]: Percentile rank single-element returns 50 (median) to avoid unfair extreme ranking in sparse FII data
- [Phase 17]: Score stored as Decimal(str(float)) to preserve precision without floating-point drift
- [Phase 17]: Page created at frontend/app/fii/screener/ (not frontend/src/app/) — Next.js appDir is frontend/app/
- [Phase 17]: Client-side filtering with useMemo avoids API roundtrips — ~400 FIIs fits in browser memory
- [Phase 19-opportunity-detector-page]: save_opportunity_to_db uses get_superuser_sync_db_session (sync) — Celery workers are synchronous, async session raises RuntimeError
- [Phase 19-opportunity-detector-page]: DB persistence fires BEFORE Telegram/email in dispatch_opportunity() so data is saved even if notification channels fail
- [Phase 19-opportunity-detector-page]: GET /opportunity-detector/history uses get_global_db (not get_authed_db) — detected_opportunities has no tenant_id/RLS
- [Phase 19]: Server-side filtering (API params) for opportunities instead of client-side useMemo — dataset can grow without bound unlike FII screener (~400 FIIs)
- [Phase 19]: C:/Program Files/Git/fii added to PROTECTED_PATHS alongside /opportunity-detector — was previously missing from middleware auth coverage

## Open Questions (resolve in Phase 17)

1. Does BRAPI summaryProfile return `segmento` (sector) for FIIs or must it come from another source?
2. BRAPI free tier has 15k req/month — at ~400 FIIs * 2 modules = ~800 req/night for pipeline. Confirm this fits quota.
3. Is `global_fiis` already populated with all ~400 B3 FIIs or a subset? Confirm universe size before score calculation.

## Performance Metrics

**v1.2 baseline:**

- Test count: 257+ passing
- Playwright E2E: 72 passing
- Lines of code: ~24K Python backend + ~12K TypeScript frontend

**v1.3 targets:**

- Maintain 257+ unit tests passing
- Maintain 72 Playwright tests passing (+ new FII screener E2E)
- Screener table load: <500ms (data pre-calculated nightly)
- FII IA analysis job: <30s (same SLA as stock analysis)

| Phase | Plan | Status | Duration | Notes |
|-------|------|--------|----------|-------|
| 17 | TBD | Not started | TBD | Score calc + Celery task + API endpoint + frontend screener table |
| 18 | TBD | Not started | TBD | Detail page + historical charts + IA job + Playwright tests |
| Phase 17 P01 | 590 | 2 tasks | 10 files |
| Phase 17 P02 | 12m | 2 tasks | 6 files |
| Phase 19-opportunity-detector-page P01 | 27 | 8 tasks | 8 files |
| Phase 19 P02 | 30 | 7 tasks | 7 files |
