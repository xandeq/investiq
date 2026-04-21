---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: - Client-side filtering with useMemo
status: unknown
last_updated: "2026-04-19T03:05:40.637Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md

**Core value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem precisar de planilha, sem abrir mil plataformas.

**Current focus:** v1.7 SHIPPED — next milestone TBD

## Current Position

Phase: 28 (Simulador de Alocação) — COMPLETE

## Progress Bar

```
v1.7 Simulador de Alocação
[████████████████████] 100% (1/1 phases)

Phase 28: Simulador de Alocação     [ COMPLETE 2026-04-19 ]
```

## v1.7 Status Reference

✅ SHIPPED 2026-04-19

| Phase | Status | Completed |
|-------|--------|-----------|
| 28. Simulador de Alocação | Complete | 2026-04-19 |

## v1.6 Status Reference

✅ SHIPPED 2026-04-19

| Phase | Status | Completed |
|-------|--------|-----------|
| 27. Comparador RF vs RV | Complete | 2026-04-18 |

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

### Existing Infrastructure Relevant to v1.7

- `GET /screener/macro-rates` — CDI/SELIC/IPCA from Redis — Phase 22/27, no changes needed
- `useComparadorCalc` hook — client-side projection with IR regressivo — Phase 27, reuse directly
- `GET /advisor/health` — returns portfolio allocation by asset class (RF/ações/FIIs) — Phase 23, no changes needed
- `TaxEngine` at `backend/app/modules/market_universe/tax_engine.py` — Phase 22, no changes needed
- Recharts LineChart — already in codebase from Phase 27

### Patterns to Reuse in v1.7

- **`useComparadorCalc`** (Phase 27): adapt for 3-class scenario projection instead of 4 benchmark rows
- **`usePortfolioHealth`** hook (Phase 23): read `GET /advisor/health` for current allocation by class
- **Macro rates fetch pattern** (Phase 27): inline or hook to `GET /screener/macro-rates`
- **Recharts** (Phase 27): optional stacked bar chart per scenario
- **Nav link pattern**: add "Simulador" alongside /comparador in sidebar

### Scenario Allocation Percentages (hardcoded)

| Perfil | RF | Ações | FIIs |
|--------|----|-------|------|
| Conservador | 80% | 10% | 10% |
| Moderado | 50% | 35% | 15% |
| Arrojado | 20% | 65% | 15% |

### Testing

- **Test count:** 257+ passing (maintained through v1.6)
- **Playwright E2E:** 72+ tests passing — maintain when adding new pages
- **DB Migrations:** 0029 (head — no new migrations expected for v1.7; all client-side)

## v1.7 Architecture Decisions

### Phase 28 Approach

- **No new backend endpoint.** All required data already served:
  - Macro rates: `GET /screener/macro-rates` (Redis cache, operational)
  - Portfolio allocation: `GET /advisor/health` → `allocation_by_class` field (Phase 23, operational)
- **Client-side scenario math:** `useSimuladorCalc` hook takes `valor`, `prazo`, `macroRates` → returns 3 scenario objects with projected returns per class (same pattern as `useComparadorCalc`)
- **Delta is arithmetic:** `target = scenario_pct * valor_total`, `current = health.allocation_by_class * portfolio_total`, `delta = target - current` — no SQL needed
- **Auth gate for SIM-03:** `has_portfolio` from health response; if false, show CTA instead of delta section — SIM-01/SIM-02 remain fully functional without portfolio
- **Page:** `frontend/app/simulador/page.tsx` — verify stub before creating

### Why 1 Phase

SIM-01 (form → scenarios), SIM-02 (projected returns), SIM-03 (delta) are tightly coupled. Scenarios without returns are meaningless; delta without a selected scenario has no reference. The tool is only useful when all three ship together. No backend work justifies a separate phase.

## Decisions

- **2026-04-19:** 1 phase for v1.7 (3 requirements) — SIM-01/02/03 in Phase 28 (client-side tool, all infra exists, requirements are tightly coupled)
- **2026-04-18:** 1 phase for v1.6 (2 requirements) — both COMP-01 and COMP-02 in Phase 27 (tool is only useful when complete)
- **2026-04-12:** 2 phases for v1.4 (7 requirements) — SCRA-01–04 in Phase 21, RF-01–03 in Phase 22
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
- [Phase 27]: Redis key market:macro:selic already populated by refresh_macro Celery beat — only API layer needed updating to expose SELIC in macro-rates response
- [Phase 27]: No router changes required — FastAPI picks up new Pydantic field automatically; TypeScript structural typing allows additive selic field without breaking existing RendaFixaContent consumer
- [Phase 27]: IR applied to gross annual rate (approximation) — standard for market-facing comparison tools
- [Phase 27]: ipcaNominalForReal = annualizeRate(ipca, days) — compound IPCA over holding period for real return denominator
- [Phase 27]: Chart color palette: produto_rf blue, CDI slate, SELIC emerald, IPCA+ amber — matches table highlight colors
- [Phase 27]: deploy-then-e2e pattern: run deploy-frontend.sh before playwright suite since tests run against production
- [Phase 28]: Re-declared IR helpers in useSimuladorCalc rather than importing from useComparadorCalc — feature isolation per D-12 precedent
- [Phase 28]: Ações: 12% a.a. hardcoded (IBOV proxy), FIIs: 8% a.a. hardcoded (DY proxy) — no IR for PF in Phase 28 scope
- [Phase 28]: macro?.cdi is the only macro field in useMemo deps — IPCA/SELIC deliberately unused for v1.7 simulador
- [Phase 28]: Used getPnl().allocation[] as allocation source (not advisor/health.allocation_by_class — field does not exist in shipped PortfolioHealth schema)
- [Phase 28]: data-testid=scenario-{key} on card buttons for Plan 03 Playwright selectors

## Open Questions (resolve in Phase 28)

1. Does `frontend/app/simulador/page.tsx` exist as a stub from a prior phase? (verify before creating)
2. Does `GET /advisor/health` return `allocation_by_class` as a typed object `{ rf_pct, acoes_pct, fiis_pct }` or a flat record? (determines TypeScript delta calc shape)
3. What proxy return rate to use for ações class (IBOV ~12% a.a. or CDI×1.3)? Pick one and hardcode; document the choice in plan.
4. Does `useComparadorCalc` export cleanly or needs adaptation for multi-class (RF+ações+FIIs each needing separate TaxEngine call)?

## Performance Metrics

**v1.6 baseline:**

- Test count: 257+ passing
- Playwright E2E: 72+ passing
- Lines of code: ~24K Python backend + ~12K TypeScript frontend
- DB Migrations: 0029 (head)

**v1.7 targets:**

- Maintain 257+ unit tests passing (no new backend = no new unit tests strictly required; may add if hooks warrant)
- Maintain 72+ Playwright tests passing (+ new /simulador E2E)
- Scenario compute: <50ms (client-side arithmetic, no network call for scenario math)
- Delta section render: <300ms (depends on GET /advisor/health response time, already cached in Redis)

| Phase | Plan | Status | Duration | Notes |
|-------|------|--------|----------|-------|
| 28 | TBD | Not started | TBD | useSimuladorCalc hook + SimuladorContent + delta section + E2E |
| Phase 21 P01 | 62s | 2 tasks | 4 files |
| Phase 21 P02 | 8 | 2 tasks | 4 files |
| Phase 21 P03 | 197s | 2 tasks | 5 files |
| Phase 22 P01 | 4m | 2 tasks | 4 files |
| Phase 22 P02 | 4m | 2 tasks | 4 files |
| Phase 25 P01 | 408 | 3 tasks | 7 files |
| Phase 26 P01 | 639 | 3 tasks | 8 files |
| Phase 27 P01 | 141 | 2 tasks | 4 files |
| Phase 27 P02 | 254 | 4 tasks | 5 files |
| Phase 27 P03 | 35 | 3 tasks | 3 files |
| Phase 28 P01 | 240 | 2 tasks | 5 files |
| Phase 28 P02 | 15 | 2 tasks | 2 files |
