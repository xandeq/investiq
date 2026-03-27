# Roadmap: InvestIQ

## Overview

InvestIQ is built in dependency order: multi-tenant auth and the transaction schema are the load-bearing foundation — every subsequent feature references tenant_id, asset_class, and RLS policies. The portfolio engine and market data caching layer come next because P&L and live prices must be correct before anything is displayed. The frontend dashboard is built on top of a proven data layer. AI analysis is added once the data foundation is stable and compliant-by-design. Import reduces onboarding friction and shares the Celery infrastructure already in place. Monetization closes the loop after user value is validated.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Foundation** - Multi-tenant auth, PostgreSQL RLS, complete transaction schema, FastAPI boilerplate (completed 2026-03-14)
- [x] **Phase 2: Portfolio Engine + Market Data** - CMP calculation, P&L, Redis cache, Celery, cotacoes brapi.dev (completed 2026-03-14)
- [ ] **Phase 3: Dashboard + Core UX** - Next.js frontend, carteira consolidada, dividendos, indicadores macro
- [ ] **Phase 4: AI Analysis Engine** - DCF/valuation/earnings async pipeline, disclaimer system, freemium gates
- [x] **Phase 5: Import + Broker Integration** - PDF nota de corretagem parser, CSV import, async review pipeline (completed 2026-03-15)
- [ ] **Phase 6: Monetization** - Stripe subscriptions, freemium enforcement, admin dashboard, plan management

---

## Milestone v1.1 — Onde Investir

- [x] **Phase 7: Foundation + Data Pipelines** - Global DB tables, TaxEngine, Redis namespaces, 3 Celery beat pipelines feeding screener and renda fixa catalog
- [ ] **Phase 8: Screener + Renda Fixa Catalog** - Acao and FII screener endpoints with portfolio-aware toggle, renda fixa catalog with net IR returns
- [ ] **Phase 9: Comparador RF vs RV** - Net return comparison across asset classes by holding period, portfolio integration
- [ ] **Phase 10: Simulador de Alocacao** - AllocationEngine with 3 scenarios, portfolio-aware rebalancing delta
- [ ] **Phase 11: Wizard Onde Investir** - AI-powered async wizard aggregating all v1.1 data, CVM-compliant output, portfolio delta display

## Phase Details

### Phase 1: Foundation
**Goal**: Multi-tenant platform is operational — users can create accounts and authenticate, all data is isolated by tenant via PostgreSQL RLS, and the full transaction schema (including corporate actions and IR-required fields) is deployed and migration-baselined
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, AUTH-04, AUTH-05, EXT-01, EXT-02, EXT-03
**Success Criteria** (what must be TRUE):
  1. User can create an account with email and password and receive a verification email
  2. User can log in and stay logged in across browser sessions; can recover forgotten password via email link
  3. A user in tenant A cannot see any data belonging to tenant B — enforced at the PostgreSQL RLS level, not only application code
  4. The transaction schema accepts all required asset classes (acao, FII, renda_fixa, BDR, ETF), corporate action types (desdobramento, grupamento, bonificacao), and IR-required fields (asset_class, gross_profit, irrf_withheld) — verified by migration and unit tests
  5. New modules can be added to the codebase without modifying core auth or tenant middleware — modular architecture is observable from folder structure and import boundaries
**Plans**: 4 plans

Plans:
- [x] 01-01-PLAN.md — Docker Compose stack, FastAPI skeleton, PostgreSQL + Redis, Alembic baseline, test scaffolds
- [x] 01-02-PLAN.md — Auth service: PyJWT RS256, registration + email verification + login + password reset + Next.js auth UI
- [ ] 01-03-PLAN.md — Multi-tenant RLS: app_user role, PostgreSQL RLS policies, FastAPI tenant injection middleware
- [ ] 01-04-PLAN.md — Transaction data model: polymorphic schema, corporate actions table, IR fields, migration 0003 + RLS

### Phase 2: Portfolio Engine + Market Data
**Goal**: The portfolio engine calculates correct P&L using CMP methodology, cotacoes are served from Redis cache (never blocking on external APIs), and benchmark comparisons (CDI, IBOVESPA) are available via API
**Depends on**: Phase 1
**Requirements**: PORT-01, PORT-02, PORT-03, PORT-04, PORT-05, PORT-06, DATA-01, DATA-02, DATA-03, DATA-04
**Success Criteria** (what must be TRUE):
  1. User can register buy/sell transactions for acoes, FIIs, renda fixa, and BDRs/ETFs — sistema calculates and stores preço médio ponderado (CMP) per asset using B3 methodology
  2. Corporate actions (desdobramentos, grupamentos) are applied to position history without distorting P&L — verified against B3 official examples
  3. System updates cotacoes automatically (15-min delay via brapi.dev) using a Celery beat job that populates Redis — individual user requests never call external market data APIs directly
  4. User can see fundamental indicators per asset (P/L, P/VP, DY, EV/EBITDA) and a historical price chart
  5. User can see macro indicators in real time (SELIC, CDI, IPCA, câmbio) via python-bcb — data is fresh and labeled with source and timestamp
**Plans**: 4 plans

Plans:
- [ ] 02-01-PLAN.md — Celery + Redis infrastructure: Docker Compose worker+beat services, celery_app.py factory, psycopg2 sync engine, test stubs
- [ ] 02-02-PLAN.md — Market data service: brapi.dev adapter, python-bcb macro, Redis cache-aside, yfinance fallback, /market-data/* endpoints
- [ ] 02-03-PLAN.md — CMP engine (TDD): pure Decimal CMP functions, B3 official examples, corporate event adjustments
- [ ] 02-04-PLAN.md — Portfolio API: transaction CRUD, positions+P&L with Redis prices, benchmarks, dividends, activate routers

### Phase 3: Dashboard + Core UX
**Goal**: Users have a complete, working frontend — carteira consolidada, P&L por ativo, rentabilidade vs benchmark, histórico de dividendos, and macro indicators — accessible on mobile and desktop
**Depends on**: Phase 2
**Requirements**: VIEW-01, VIEW-02, VIEW-03, VIEW-04
**Success Criteria** (what must be TRUE):
  1. User sees the consolidated portfolio on login: all assets, current value, allocation percentage by category — data matches the Phase 2 API exactly
  2. User sees P&L per asset broken down as realized gain, unrealized gain, and total — clearly labeled "desde a compra / no mês / no ano"
  3. User sees portfolio rentabilidade compared against CDI and IBOVESPA — chart and numeric values visible on the same screen
  4. User sees dividend/provento history by asset and by period — filterable by year and asset class
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — Frontend infrastructure: TanStack Query v5, shadcn chart, lightweight-charts, QueryClientProvider, typed API functions, Wave 0 test stubs
- [ ] 03-02-PLAN.md — Dashboard module + page: GET /dashboard/summary backend, NetWorthCard, AllocationChart, PortfolioChart, MacroIndicators, RecentTransactions
- [ ] 03-03-PLAN.md — Portfolio analytics page: P&L table (desde a compra), benchmark chart, dividend history with year + asset_class filters

### Phase 4: AI Analysis Engine
**Goal**: Premium users can request AI-powered fundamental analysis (DCF + valuation + earnings) for any asset and receive AI interpretation of macro indicators for their portfolio — all outputs carry mandatory CVM-compliant disclaimers and are gated behind the premium plan
**Depends on**: Phase 3
**Requirements**: AI-01, AI-02, AI-03, AI-04, AI-05
**Success Criteria** (what must be TRUE):
  1. User can request fundamental analysis for any asset and receive a result in natural language (DCF, valuation, earnings interpretation) — request returns 202 + job_id immediately, result is available via polling within a reasonable time
  2. User receives AI interpretation of how current macro conditions (SELIC, IPCA, câmbio) affect their specific portfolio
  3. User receives AI portfolio evaluation covering diversification, concentration risk, and rebalancing suggestions
  4. Every AI output screen displays a visible disclaimer: "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)" — no AI output is visible without this disclaimer
  5. Free-tier user sees a preview of AI analysis with a CTA to upgrade — they cannot see the full analysis output
**Plans**: TBD

Plans:
- [ ] 04-01: AI skills adapters — dcf.py, valuation.py, earnings.py, macro.py encapsulated as independent Celery tasks; OpenAI/OpenRouter via AWS Secrets Manager
- [ ] 04-02: Async analysis pipeline — POST returns 202 + job_id, Celery worker runs analysis, result stored in DB, frontend polls until complete
- [ ] 04-03: AI results UI — analysis output panels, mandatory disclaimer component, rate limit per user/hour (slowapi + Redis), premium gate + upgrade CTA

### Phase 5: Import + Broker Integration
**Goal**: Users can import transactions from Clear and XP broker PDFs and from CSV — parsed transactions are reviewed before committing, raw files are stored permanently for re-parsing, and duplicate detection prevents double-counting
**Depends on**: Phase 2
**Requirements**: IMP-01, IMP-02, IMP-03
**Success Criteria** (what must be TRUE):
  1. User can upload a nota de corretagem PDF from XP or Clear — sistema parses it asynchronously and presents extracted transactions for review before any data is saved
  2. User can import transactions via CSV using the system's template — import is validated and shown for review before committing
  3. Original import files (PDF and CSV) are stored permanently and can be re-parsed if the parser is updated — without requiring the user to re-upload
**Plans**: 2 plans

Plans:
- [ ] 05-01-PLAN.md — Backend import pipeline: correpy parser cascade, CSV validator, Celery async tasks, ImportFile/ImportJob/ImportStaging models, FastAPI endpoints, Alembic migration 0005
- [ ] 05-02-PLAN.md — Import review UI: /imports page, file upload dropzone, TanStack polling, staging review table with duplicate flagging, confirm/cancel, import history with re-parse

### Phase 6: Monetization
**Goal**: Users can subscribe to the Premium plan via Stripe, free-tier users see enforced limits with contextual upgrade CTAs, and the admin has a dashboard to manage subscribers and plan status
**Depends on**: Phase 4
**Requirements**: MON-01, MON-02, MON-03, MON-04
**Success Criteria** (what must be TRUE):
  1. Two plans are active — Gratuito (carteira basic, sem IA) and Premium (full AI analysis) — plan limits are enforced at the API and UI levels, not only as visual hints
  2. User can subscribe to Premium via Stripe (BRL, cartão de crédito) and immediately gains access to AI features — Stripe webhook drives plan status, not manual updates
  3. Free-tier user sees blocked premium features with a preview and a contextual upgrade CTA — the CTA is visible in the AI analysis section, not only on a billing page
  4. Admin can view a list of all subscribers, their current plan, and payment status — no manual database query required
**Plans**: 2 plans

Plans:
- [ ] 06-01-PLAN.md — Stripe integration: BRL checkout, subscription webhooks, billing columns on User, customer portal, Alembic migration 0006, test infrastructure
- [ ] 06-02-PLAN.md — Freemium enforcement: plan_gate.py shared dependency, API-level gates, /planos pricing page, /planos/sucesso polling page, admin subscriber dashboard

---

## Milestone v1.1 Phase Details

### Phase 7: Foundation + Data Pipelines
**Goal**: All infrastructure required by v1.1 is in place — global DB tables exist, TaxEngine enforces correct IR regressivo rules, Redis namespaces are defined and isolated from existing market keys, and the three Celery beat pipelines are running and populating data that screener and catalog endpoints will read
**Depends on**: Phase 2 (Celery + Redis infrastructure)
**Requirements**: SCRA-04
**Success Criteria** (what must be TRUE):
  1. The `screener_snapshots`, `fii_metadata`, and `fixed_income_catalog` tables exist in production with Alembic migrations applied — the `get_global_db` FastAPI dependency returns a DB session without tenant injection
  2. The daily `refresh_screener_universe` Celery beat task runs successfully, populates `screener_snapshots` with B3 ticker fundamentals, and never fires per user request — verified by checking that screener endpoints return data without triggering any brapi.dev call at request time
  3. The weekly `refresh_fii_metadata` task downloads CVM CSV, upserts segment and vacancy data into `fii_metadata` — every FII row in the table has a non-null `segmento` field
  4. The `refresh_tesouro_rates` task runs every 6 hours, stores rates under the `tesouro:rates:*` Redis namespace — keys never collide with existing `market:*` namespace
  5. TaxEngine applies the full 4-tier IR regressivo table (22.5% / 20% / 17.5% / 15% by holding days) with LCI/LCA and FII exemption rates stored as DB config values, not hardcoded constants — a rate change requires only a DB update, not a code deployment
**Plans**: 2 plans

Plans:
- [x] 07-01-PLAN.md — Global DB tables (models, migration 0015, get_global_db, TaxEngine)
- [x] 07-02-PLAN.md — Three Celery beat pipelines (screener, FII metadata, Tesouro rates) + celery_app registration

### Phase 8: Screener + Renda Fixa Catalog
**Goal**: Users can filter and browse B3 stocks and FIIs using multi-criteria screeners that read pre-built snapshots (zero external API calls per request), and can view a renda fixa catalog showing Tesouro Direto rates and CDB/LCI/LCA reference ranges with IR-adjusted net returns already calculated
**Depends on**: Phase 7
**Requirements**: SCRA-01, SCRA-02, SCRA-03, SCRF-01, SCRF-02, SCRF-03, SCRF-04, RF-01, RF-02, RF-03
**Success Criteria** (what must be TRUE):
  1. User can filter acoes by DY, P/L, P/VP, EV/EBITDA, sector, liquidity, and market cap — results show a paginated table with ticker, price, variation, DY, P/L, P/VP, and a 12-month sparkline — every result row reflects the latest daily snapshot, not a live API call
  2. User can activate the "ativos que nao tenho" toggle and see only tickers absent from their current portfolio — the filter works for both the acao and FII screeners
  3. User can filter FIIs by P/VP, DY, segmento (Tijolo/Papel/Hibrido/FoF/Agro), vacancia financeira, liquidez, and numero de cotistas — the segmento column is always visible and P/VP results are labeled with the segment-appropriate benchmark context
  4. User sees the renda fixa catalog with Tesouro Direto current rates (SELIC, IPCA+, IPCA+ Juros Semestrais, Prefixado) showing rate, unit price, and maturity — catalog UI labels these as "taxas de referencia de mercado", never "oferta ao vivo"
  5. User sees net return after IR for each renda fixa instrument by holding period (6m, 1a, 2a, 5a) — IR regressivo tiers and LCI/LCA exemption are applied correctly and visibly displayed per row
**Plans**: TBD

### Phase 9: Comparador RF vs RV
**Goal**: Users can compare net-of-IR returns across fixed income and equity asset classes by holding period, and see their own portfolio's annualized return expressed as a fixed income equivalent — making the opportunity cost of their current allocation tangible
**Depends on**: Phase 8
**Requirements**: COMP-01, COMP-02
**Success Criteria** (what must be TRUE):
  1. User can compare net IR-adjusted returns for CDB, LCI/LCA, Tesouro SELIC, and IBOVESPA historical performance side by side for holding periods of 6m, 1a, 2a, and 5a — all figures reflect IR regressivo and LCI/LCA exemption correctly
  2. User sees their own portfolio's annualized return displayed in the comparador alongside fixed income benchmarks — phrased as "sua carteira rendeu X% a.a. — equivalente a CDB de Y% ao ano"
**Plans**: TBD

### Phase 10: Simulador de Alocacao
**Goal**: Users can input an available amount, time horizon, and risk profile and receive an AI-free, deterministic allocation mix across asset classes with three scenarios showing IR-adjusted projections, including a portfolio delta that shows the difference between their current allocation and the suggested ideal
**Depends on**: Phase 9
**Requirements**: SIM-01, SIM-02, SIM-03
**Success Criteria** (what must be TRUE):
  1. User inputs valor disponivel, prazo, and perfil (conservador/moderado/arrojado) and receives an allocation mix in percentages by asset class (acoes/FIIs/renda fixa/caixa) — result is deterministic and returns in under 500ms
  2. Simulator displays 3 scenarios (pessimista/base/otimista) with projected returns and IR-adjusted net values per scenario per asset class — IR is applied per holding period and asset class, not as a flat rate
  3. When the user activates portfolio-aware mode, the simulator reads their current portfolio allocation and shows the delta: how much of each asset class to add or reduce to reach the suggested ideal mix
**Plans**: TBD

### Phase 11: Wizard Onde Investir
**Goal**: Users can complete a guided multi-step wizard that produces an AI-generated allocation recommendation in asset class percentages — never specific tickers — informed by their actual portfolio, current macro data, and risk profile, with a mandatory CVM disclaimer rendered before any results are shown
**Depends on**: Phase 10
**Requirements**: WIZ-01, WIZ-02, WIZ-03, WIZ-04, WIZ-05
**Success Criteria** (what must be TRUE):
  1. User completes a multi-step wizard entering valor disponivel, prazo, and perfil de risco — the UI uses a step progress indicator and the user can navigate back to edit inputs before submitting
  2. Wizard result shows allocation in percentages by asset class only (acoes, FIIs, renda fixa, caixa) — no ticker symbols appear anywhere in the output; if the LLM returns a ticker pattern (uppercase 4-6 chars), the result is suppressed and retried automatically
  3. The CVM disclaimer — "Analise informativa — nao constitui recomendacao de investimento (CVM Res. 19/2021)" — is displayed visibly before the allocation result is rendered, not as a footnote or after-the-fact annotation
  4. Wizard output includes the user's current portfolio allocation context and shows the delta: "voce tem X% em acoes, sugestao e Y%" — the recommendation accounts for what the user already owns
  5. Wizard prompt to the LLM includes current SELIC, IPCA, and macro trend context — the rationale shown to the user references actual current macro conditions, not generic boilerplate
**Plans**: 2 plans

Plans:
- [x] 11-01-PLAN.md — VPS migration + wizard models in conftest + test_wizard.py (unit + integration tests)
- [ ] 11-02-PLAN.md — WizardContent.tsx multi-step refactor (3 steps, progress indicator, back-navigation, CVM disclaimer first)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6
Note: Phase 5 (Import) depends only on Phase 2 and can be developed in parallel with Phase 4 if needed.

**v1.1 Execution Order:**
7 -> 8 -> 9 -> 10 -> 11
Note: Phases 8, 9, and 10 can overlap after Phase 7 migrations land — screener endpoints, comparador, and simulator have no inter-dependencies between them.

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 5/4 | Complete   | 2026-03-14 |
| 2. Portfolio Engine + Market Data | 4/4 | Complete   | 2026-03-14 |
| 3. Dashboard + Core UX | 3/3 | Checkpoint (human-verify) |  |
| 4. AI Analysis Engine | 0/3 | Not started | - |
| 5. Import + Broker Integration | 2/2 | Complete   | 2026-03-15 |
| 6. Monetization | 0/2 | Not started | - |
| 7. Foundation + Data Pipelines (v1.1) | 2/2 | Complete | 2026-03-22 |
| 8. Screener + Renda Fixa Catalog (v1.1) | 0/TBD | Not started | - |
| 9. Comparador RF vs RV (v1.1) | 0/TBD | Not started | - |
| 10. Simulador de Alocacao (v1.1) | 0/TBD | Not started | - |
| 11. Wizard Onde Investir (v1.1) | 1/2 | In Progress|  |
