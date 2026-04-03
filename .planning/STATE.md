---
gsd_state_version: 1.0
milestone: v1.2
milestone_name: Requirements to Phases Mapping
status: unknown
last_updated: "2026-04-03T10:29:51.787Z"
progress:
  total_phases: 5
  completed_phases: 3
  total_plans: 7
  completed_plans: 7
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-31 after v1.2 planning)

**Core value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — v1.2 adds AI-driven fundamental analysis (DCF, earnings, dividends, peers)

**Current focus:** Phase 14 — differentiators-sophistication

## Current Position

Phase: 14 (differentiators-sophistication) — EXECUTING
Plan: 2 of 2

## v1.1 Status Reference

✅ SHIPPED 2026-03-28

| Phase | Status | Completed |
|-------|--------|-----------|
| 1. Foundation | Complete | 2026-03-14 |
| 2. Portfolio Engine + Market Data | Complete | 2026-03-14 |
| 3. Dashboard + Core UX | Complete | 2026-03-15 |
| 4. AI Analysis Engine | Complete | 2026-03-15 |
| 5. Import + Broker Integration | Complete | 2026-03-15 |
| 6. Monetization | Complete | 2026-03-21 |
| 7. Foundation + Data Pipelines | Complete | 2026-03-26 |
| 11. Wizard Onde Investir | Complete | 2026-03-28 |

## Accumulated Context

- **Stack:** FastAPI + SQLAlchemy async + Next.js 15 + PostgreSQL + Redis + Celery
- **Deploy:** docker cp → docker compose restart (not docker build — apt-get fails on VPS network)
- **VPS:** 185.173.110.180, path: /app/financas/
- **BRAPI:** Token available (free, 15k req/month) — B3 quotes
- **Testing:** 257 tests passing currently; maintain test quality in v1.2
- **Production:** https://investiq.com.br (frontend) + https://api.investiq.com.br (backend)
- **Stripe LIVE:** price_1TC56FCA1CPHCF6PKQ5XmUWD (R$29,90/mês)

## v1.2 Architecture Decisions

### Legal & Compliance

- CVM audit required before Phase 12 launch — confirm registration threshold + disclaimer architecture
- On-feature disclaimer (not hidden in TOS) — position as educational analysis, not financial advice
- Data versioning mandatory on all analyses — `data_version_id` + `data_timestamp` visible to users

### Cost Control & Operations

- Rate limiting per plan tier: Free 0/month, Pro 50/month, Enterprise 500/month
- LLM provider pattern: OpenRouter (Haiku) + Groq fallback (never hardcode keys)
- Cost tracking per analysis type: DCF, Earnings, Dividend, Sector analysis tracked separately
- Async architecture mandatory: All analysis requests return job ID immediately, background Celery workers process

### Data & Caching

- All analyses tagged with data source + timestamp (BRAPI EOD, CVM/B3 filings, etc.)
- Cache invalidation on earnings release (BRAPI earnings feed) + manual "Refresh" button
- Peer comparison must show data completeness: "7 of 10 peers included; 2 missing earnings, 1 recent IPO"
- Multi-tenancy: All analyses scoped to `tenant_id` (like portfolio positions)

### Performance

- Analysis job target: <30s for simple DCF (Phase 12), <60s for complex sector analysis (Phase 15)
- Async job pattern reused from wizard: Return job ID, WebSocket notification on completion
- Cache hit rate target: >75% for repeat analyses (same ticker, same user within 24h)

## Research Flags (Phase Assignments)

| Flag | Phase | Action |
|------|-------|--------|
| CVM registration threshold | 12 | Legal counsel consultation during disclaimer architecture |
| OpenRouter fallback reliability | 12 | Staging integration test before production |
| Per-analysis-type cost tracking | 12 | Cost dashboard implemented in Phase 12 |
| BRAPI earnings feed reliability | 15 | Pilot invalidation with 10 tickers; verify triggers |
| B3 stock data completeness | 15 | Data audit of 200+ stocks before launch |
| User assumption validation ranges | 14 | Input validation: growth 0–20%, discount rate 0–30% |

## Decisions

- **03-31 Roadmap:** Phase 12 Foundation must include legal audit + cost control + async architecture before any analysis features ship (research critical finding)
- **03-31 Roadmap:** Reuse wizard patterns: Celery async jobs, job ID return, WebSocket polling, LLM provider fallback
- **03-31 Roadmap:** Coarse granularity (5 phases) chosen to compress 15 requirements into critical-path deliverables
- **03-31 Roadmap:** All research pitfalls (legal, cost, data staleness, cache invalidation, performance) addressed in Phase 12 upfront, not bolted on later
- [Phase 13]: BRAPI token resolved via env > AWS SM (same as BrapiClient), sync HTTP calls in data.py
- [Phase 13]: DCF uses net_debt (total_debt - total_cash) subtracted from EV for equity fair value per share
- [Phase 13]: Earnings accrual ratio uses (total_debt + total_cash) as proxy for total assets (BRAPI limitation)
- [Phase 13]: Dividend sustainability uses strict priority ordering: risk first, warning second, safe last
- [Phase 14]: Admin costs endpoint placed before /{job_id} catch-all route in router.py to avoid 404 routing conflict
- [Phase 14]: days param validated with le=90 via FastAPI Query — days>90 returns 422 (not clamped)
- [Phase 14]: BRAPI has no sector-listing endpoint — hardcoded _SECTOR_TICKERS dict with 11 B3 sectors is the correct peer lookup approach
- [Phase 14]: fetch_fundamentals() does not return ticker field — inject as _ticker private key so calculate_sector_comparison() can identify each peer

## Open Questions (resolve in Phase 12)

1. CVM registration threshold: At what user count / analysis volume does InvestIQ cross from "information tool" to "financial adviser"?
2. OpenRouter fallback latency: What's acceptable degradation when Groq fallback fires?
3. Earnings feed timing: How reliably does BRAPI capture earnings announcements (same-day vs +1 day)?

## Performance Metrics

**v1.1 baseline (for reference):**

- Sessions: 11
- Plans executed: 11 (Phases 1–7, 11)
- Phases complete: 8 (Phases 1–7, 11 shipped; Phases 8–10 deferred)
- Test count: 257 passing
- Lines of code: ~24K Python backend + ~12K TypeScript frontend

**v1.2 targets:**

- Phase duration: 2–4 weeks per phase (Foundation critical, expect 3–4 weeks)
- Test count: 257 baseline + new analysis tests (target 300+)
- Code coverage: Maintain >80% for critical paths (quota enforcement, async jobs, legal disclaimers)

| Phase | Plan | Status | Duration | Tasks |
|-------|------|--------|----------|-------|
| 12 | 01-legal-audit | Planned | TBD | Consult CVM lawyer, build disclaimer UI, implement quota schema |
| 12 | 02-async-infrastructure | Planned | TBD | Design queue, implement fallback providers, write integration tests |
| 12 | 03-dcf-basic | Planned | TBD | Simple DCF model, data versioning, cost tracking |
| 13 | 01-earnings | Planned | TBD | Historical EPS, quality metrics, forecast aggregation |
| 13 | 02-dividends | Planned | TBD | Yield, payout ratio, coverage, sustainability flag |
| 13 | 03-peers | Planned | TBD | Sector peer fundamentals, metrics aggregation, <10s response |
| 14 | 01-llm-narrative | Planned | TBD | Claude Haiku integration, narrative generation, validation |
| 14 | 02-sensitivity | Planned | TBD | Bear/base/bull scenarios, input ranges, comparisons |
| 14 | 03-customization | Planned | TBD | Frontend form, assumption inputs, recalculation |
| 15 | 01-cache-invalidation | Planned | TBD | Event-driven invalidation, earnings feed integration |
| 15 | 02-data-quality | Planned | TBD | Peer audit, completeness flags, bias testing |
| 15 | 03-performance | Planned | TBD | Load test, scaling validation, p95 latency <30s |
| 16 | 01-detail-page | Planned | TBD | Stock detail layout, all analysis sections, disclaimer |
| 16 | 02-websocket | Planned | TBD | Async loading UX, progress spinner, real-time updates |
| 16 | 03-testing-launch | Planned | TBD | Regression test, security audit, production toggle |
| Phase 13 P01 | 344 | 2 tasks | 5 files |
| Phase 13 P02 | 339 | 2 tasks | 5 files |
| Phase 14 P02 | 15 | 2 tasks | 2 files |
| Phase 14 P01 | 22 | 2 tasks | 4 files |
