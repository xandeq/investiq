---
gsd_state_version: 1.0
milestone: v1.3
milestone_name: - Client-side filtering with useMemo
status: unknown
last_updated: "2026-04-12T19:35:20.494Z"
progress:
  total_phases: 2
  completed_phases: 2
  total_plans: 5
  completed_plans: 5
---

# Project State

## Project Reference

See: .planning/PROJECT.md

**Core value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — v1.4 adiciona screener de ações filtrável e catálogo de renda fixa com retorno líquido real.

**Current focus:** Phase 22 — catalogo-renda-fixa

## Current Position

Phase: 22 (catalogo-renda-fixa) — EXECUTING
Plan: 2 of 2

## Progress Bar

```
v1.4 Ferramentas de Análise
[░░░░░░░░░░░░░░░░░░░░] 0% (0/2 phases)

Phase 21: Screener de Ações     [ NOT STARTED ]
Phase 22: Catálogo Renda Fixa   [ NOT STARTED ]
```

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

### Existing Infrastructure Relevant to v1.4

- `screener_snapshots` table: Celery beat pipeline, ~900 tickers universe — **Phase 21 backend foundation**
- `fixed_income_catalog` table: Celery beat pipeline, Tesouro/CDB/LCI/LCA data — **Phase 22 backend foundation**
- `TaxEngine`: calculates net return after IR by prazo bracket — **Phase 22 core engine**
- `get_global_db`: pattern for non-tenant global tables — reuse for both phases
- Goldman Sachs screener endpoint `/screener/` — returns top 10 only, Phase 21 needs `/screener/universe` instead

### Patterns to Reuse in v1.4

- **Phase 17 FII Screener:** client-side useMemo filtering, table + filter UX, Tailwind table styling — reuse for Phase 21
- **`get_global_db`:** global (non-tenant) table session — reuse for screener universe + RF catalog
- **Nav link pattern:** add /acoes/screener and /renda-fixa to sidebar/nav

### Testing

- **Test count:** 257+ passing (v1.2 baseline, maintained through v1.3)
- **Playwright E2E:** 72 tests passing — maintain when adding new pages
- **DB Migrations:** 0023 (head at v1.3 end)

## v1.4 Architecture Decisions

### Phase 21 Approach

- New `GET /screener/universe` endpoint returns full ~900 ticker universe with DY, P/L, Setor, Market Cap, Variação 12m
- Client-side filtering with useMemo — same as Phase 17 FII Screener, fits in browser memory
- Paginação client-side for consistency

### Phase 22 Approach

- Check if RF API endpoint already exists before creating new one
- Frontend-only if backend complete; thin route + TaxEngine wrapper if not
- CDI/IPCA beat indicator uses CDI rate from python-bcb or DB

## Decisions

- **2026-04-12 Roadmap:** 2 phases for 7 requirements — SCRA-01–04 in Phase 21 (screener), RF-01–03 in Phase 22 (catálogo RF)
- **2026-04-12 Roadmap:** Phase 21 reuses Phase 17 FII Screener client-side useMemo pattern
- **2026-04-12 Roadmap:** Phase 22 is frontend-only (backend fully operational since v1.1)
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

## Open Questions (resolve in Phase 21)

1. Does `screener_snapshots` table include all required columns (DY, P/L, Setor, Market Cap, Variação 12m) or do they need to be added/populated?
2. Does a `/renda-fixa` or `/fixed-income` API endpoint already exist, or does Phase 22 need to create it?
3. What is current DB migration head number after v1.3? (0023 assumed — confirm before Phase 21 migration)

## Performance Metrics

**v1.3 baseline:**

- Test count: 257+ passing
- Playwright E2E: 72 passing
- Lines of code: ~24K Python backend + ~12K TypeScript frontend
- DB Migrations: 0023 (head)

**v1.4 targets:**

- Maintain 257+ unit tests passing
- Maintain 72 Playwright tests passing (+ new screener + RF catalog E2E)
- Screener table load: <500ms (data pre-calculated nightly)
- RF catalog load: <300ms (static catalog from DB + TaxEngine calculations)

| Phase | Plan | Status | Duration | Notes |
|-------|------|--------|----------|-------|
| 21 | TBD | Not started | TBD | New /screener/universe endpoint + /acoes/screener frontend |
| 22 | TBD | Not started | TBD | /renda-fixa frontend (backend exists) |
| Phase 21 P01 | 62s | 2 tasks | 4 files |
| Phase 21 P02 | 8 | 2 tasks | 4 files |
| Phase 21 P03 | 197s | 2 tasks | 5 files |
| Phase 22 P01 | 4m | 2 tasks | 4 files |
| Phase 22 P02 | 4m | 2 tasks | 4 files |
