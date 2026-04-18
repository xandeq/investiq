---
gsd_state_version: 1.0
milestone: v1.6
milestone_name: Comparador RF vs RV
status: roadmap_complete
last_updated: "2026-04-18T00:00:00.000Z"
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md

**Core value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem precisar de planilha, sem abrir mil plataformas.

**Current focus:** v1.6 — Comparador RF vs RV (roadmap complete, ready for planning)

## Current Position

Phase: Phase 27 — Comparador RF vs RV (not started)
Plan: —
Status: Roadmap complete — ready for `/gsd:plan-phase 27`
Last activity: 2026-04-18 — v1.6 roadmap created (1 phase, 2 requirements mapped)

## Progress Bar

```
v1.6 Comparador RF vs RV
[░░░░░░░░░░░░░░░░░░░░] 0% (0/1 phases)

Phase 27: Comparador RF vs RV     [ NOT STARTED ]
```

## v1.5 Status Reference

✅ SHIPPED 2026-04-18

| Phase | Status | Completed |
|-------|--------|-----------|
| 23. Portfolio Health Check | Complete | 2026-04-18 |
| 24. AI Advisor Recommendations | Planned | — |
| 25. Smart Screener | Complete | 2026-04-18 |
| 26. Entry Signals | Complete | 2026-04-18 |

## v1.4 Status Reference

✅ SHIPPED 2026-04-12

| Phase | Status | Completed |
|-------|--------|-----------|
| 21. Screener de Ações | Complete | 2026-04-12 |
| 22. Catálogo Renda Fixa | Complete | 2026-04-12 |

## v1.3 Status Reference

✅ SHIPPED 2026-04-11

| Phase | Status | Completed |
|-------|--------|-----------|
| 17. FII Screener Table | Complete | 2026-04-04 |
| 18. FII Detail Page + IA | Complete | 2026-04-04 |
| 19. Opportunity Detector Page | Complete | 2026-04-05 |
| 20. Swing Trade Page | Complete | 2026-04-11 |

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
- **Frontend appDir:** `frontend/app/` (NOT `frontend/src/app/`) — confirmed Phase 17

### Data Sources

- **BRAPI:** Token available (free, 15k req/month) — B3 quotes + dividendsData + summaryProfile
- **python-bcb:** Macro data including CDI/IPCA rates
- **screener_snapshots:** ~900 tickers populated nightly by Celery beat (from v1.1)
- **fixed_income_catalog:** Tesouro Direto + CDB + LCI/LCA populated nightly by Celery beat (from v1.1)
- **TaxEngine:** IR regressivo (22.5%→15%) + LCI/LCA isenção — fully operational (v1.1)
- **Macro rates Redis cache:** CDI/SELIC/IPCA served by `GET /screener/macro-rates` — already built (Phase 22)

### Existing Infrastructure Relevant to v1.6

- `TaxEngine` at `backend/app/modules/market_universe/tax_engine.py` — Phase 27 core engine (no changes needed)
- `GET /screener/macro-rates` — CDI/SELIC/IPCA from Redis — Phase 27 data source (no changes needed)
- `fixed_income_catalog` table — Tesouro/CDB/LCI/LCA rates — Phase 27 rate lookup (no changes needed)
- `GET /renda-fixa` endpoint (Phase 22) — read structure before building /comparador
- `get_global_db` — pattern for non-tenant endpoints — use for /comparador (no auth needed)

### Patterns to Reuse in v1.6

- **TaxEngine call pattern** (Phase 22): established integration for net return calculation
- **Recharts LineChart**: already in codebase — find existing usage for import pattern
- **`get_global_db`**: global (non-tenant) table session — use for /comparador
- **Nav link pattern**: add "Comparador" alongside /renda-fixa

### Testing

- **Test count:** 257+ passing (maintained through v1.5)
- **Playwright E2E:** 72 tests passing — maintain when adding new pages
- **DB Migrations:** 0029 (head at v1.6 start — billing idempotency migration)

## v1.6 Architecture Decisions

### Phase 27 Approach

- New `GET /comparador` endpoint: params `valor`, `prazo_meses`, `tipo_rf` → calls TaxEngine for each alternative (produto RF, CDI, SELIC, IPCA+) → returns `{ summary: [...], projection: [...] }`
- Backend handles projection math (compound monthly): `P * (1 + r_monthly)^t` for each month — keeps TaxEngine as single source of truth
- Rentabilidade real column: `(1 + retorno_nominal) / (1 + ipca_acumulado) - 1` — IPCA from macro rates
- Frontend: `/comparador` page, no auth gate (standalone public tool), form updates table + chart on any input change
- Chart: Recharts LineChart, one series per alternative, x-axis = months, y-axis = patrimônio acumulado R$

### Why 1 Phase

With TaxEngine, macro rates, and catalog fully built, the only work is:
1. Thin backend endpoint (projection loop + TaxEngine calls)
2. Frontend page (form + table + chart)

Table and chart are one unified tool — shipping them in separate phases would leave users with a half-finished comparador. 1 coherent phase is the cleanest boundary.

## Decisions

- **2026-04-12:** 2 phases for v1.4 (7 requirements) — SCRA-01–04 in Phase 21, RF-01–03 in Phase 22
- **2026-04-18:** 1 phase for v1.6 (2 requirements) — both COMP-01 and COMP-02 in Phase 27 (tool is only useful when complete)
- **Phase 17 established:** Page created at frontend/app/ (not frontend/src/app/) — appDir is frontend/app/
- **Phase 17 established:** Client-side filtering with useMemo avoids API roundtrips — dataset fits in browser memory
- **Phase 19:** Server-side filtering for opportunity detector (dataset unbounded) vs client-side for screeners (bounded ~400–900 items)
- **Phase 20:** Migration gates RLS SQL behind postgres dialect so sqlite-based tests can upgrade to head
- [Phase 21]: Used Numeric(10,6) for variacao_12m_pct to match existing precision pattern (dy column); no dialect gate needed in migration
- [Phase 21]: No server-side filtering on /universe -- frontend does all filtering with useMemo (per D-09)
- [Phase 21]: Reused existing screener_v2 router for /universe endpoint -- no new router or main.py changes needed
- [Phase 21]: Sector dropdown dynamically built from data.results via useMemo (not hardcoded) for /acoes/screener
- [Phase 21]: Market cap tier buttons toggle: clicking active tier deselects it in client-side filter
- [Phase 22]: MacroRatesResponse imported at top level in service.py -- no circular import risk confirmed
- [Phase 22]: No main.py changes needed -- /renda-fixa prefix already registered on screener_v2 router
- [Phase 22]: annualizeRate uses compound math matching Python _compound_return() formula exactly
- [Phase 22]: Beat indicator gated on macroRates load state -- no-flash guard prevents showing wrong colors during data fetch
- [Phase 25]: ComplementaryAssetRow.preco_atual maps to ScreenerSnapshot.regular_market_price; dy_12m_pct maps to ScreenerSnapshot.dy (field name correction from plan)
- [Phase 25]: useSmartScreener enabled only when health.has_portfolio=true — avoids API call for empty portfolios
- [Phase 26]: Used compute_signals() from swing_trade (not non-existent calculate_rsi_ma) — correctly reuses existing market-data-cached signal pipeline
- [Phase 26]: Universe Celery batch reads ScreenerSnapshot (NO LLM) — deterministic, cost-free nightly refresh filtering variacao_12m < -10% OR dy > 6%
- [Phase 26]: suggested_amount_brl hardcoded R$1000 default — no position-size context without cost-basis calculation; rsi=None since compute_signals uses 30d-high discount not RSI

## Open Questions (resolve in Phase 27)

1. Does `GET /renda-fixa` endpoint return `taxa` as annual decimal or percentage string? (determines TaxEngine call format for /comparador)
2. What is the current DB migration head number? (0029 assumed from untracked migration file — confirm before any new migration)
3. Does Recharts already exist in package.json or does it need to be added?

## Performance Metrics

**v1.5 baseline:**

- Test count: 257+ passing
- Playwright E2E: 72 passing
- Lines of code: ~24K Python backend + ~12K TypeScript frontend
- DB Migrations: 0029 (head)

**v1.6 targets:**

- Maintain 257+ unit tests passing
- Maintain 72 Playwright tests passing (+ new /comparador E2E)
- Comparador table compute: <200ms (backend projection loop, no external API calls — TaxEngine + Redis)
- Chart render: <100ms (client-side Recharts with ≤120 data points per series)

| Phase | Plan | Status | Duration | Notes |
|-------|------|--------|----------|-------|
| 27 | TBD | Not started | TBD | /comparador endpoint + frontend page with table + chart |
| Phase 21 P01 | 62s | 2 tasks | 4 files |
| Phase 21 P02 | 8 | 2 tasks | 4 files |
| Phase 21 P03 | 197s | 2 tasks | 5 files |
| Phase 22 P01 | 4m | 2 tasks | 4 files |
| Phase 22 P02 | 4m | 2 tasks | 4 files |
| Phase 25 P01 | 408 | 3 tasks | 7 files |
| Phase 26 P01 | 639 | 3 tasks | 8 files |
