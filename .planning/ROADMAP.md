# InvestIQ v1.4 — Ferramentas de Análise — Roadmap

**Milestone:** v1.4 Ferramentas de Análise
**Phases:** 21–22 (continues from v1.3 Phase 20)
**Granularity:** Coarse (2 phases — natural delivery boundaries)
**Status:** Active
**Created:** 2026-04-12

---

## Phases

- [x] **Phase 21: Screener de Ações** — Tabela filtrável de ~900 ações com endpoint filterable, paginação e link para /stock/[ticker] (completed 2026-04-12)
- [x] **Phase 22: Catálogo Renda Fixa** — Frontend do catálogo RF com retorno líquido IR por prazo, filtros e indicadores visuais (backend exists from v1.1) (completed 2026-04-12)

---

## Phase Details

### Phase 21: Screener de Ações
**Goal:** Usuário pode explorar e filtrar o universo completo de ações brasileiras por fundamentos diretamente na plataforma
**Depends on:** Nothing (screener universe ~900 tickers already populated nightly by Celery beat from v1.1; screener_snapshots table exists)
**Requirements:** SCRA-01, SCRA-02, SCRA-03, SCRA-04
**Success Criteria** (what must be TRUE):
  1. Usuário acessa /acoes/screener e vê tabela com colunas Ticker, Nome, Setor, Preço Atual, Variação 12m%, DY 12m, P/L e Market Cap — cada coluna é clicável para ordenar
  2. Usuário aplica filtros (DY mínimo slider, P/L máximo input, Setor dropdown B3, Market Cap small/mid/large) e a tabela atualiza instantaneamente sem reload de página
  3. Usuário clica em qualquer ticker da tabela e é navegado para /stock/[ticker] — a página de análise completa já existente abre corretamente
  4. Tabela exibe paginação e usuário navega entre páginas de resultados
**Plans:** 3/3 plans complete

Plans:
- [x] 21-01-PLAN.md — Migration 0024 + brapi 52WeekChange + Celery upsert for variacao_12m_pct
- [x] 21-02-PLAN.md — GET /screener/universe endpoint (schemas, service, router, tests)
- [x] 21-03-PLAN.md — Frontend /acoes/screener page (feature dir, filters, sort, pagination)

---

### Phase 22: Catálogo Renda Fixa
**Goal:** Usuário compara produtos de renda fixa com retorno líquido real (após IR regressivo) por prazo, sem precisar sair da plataforma
**Depends on:** Nothing (fixed_income_catalog table + TaxEngine + Celery pipeline fully operational from v1.1; RF API endpoint may already exist)
**Requirements:** RF-01, RF-02, RF-03
**Success Criteria** (what must be TRUE):
  1. Usuário acessa /renda-fixa e vê catálogo agrupado por tipo (Tesouro Direto, CDB, LCI/LCA) com taxa, vencimento e valor mínimo de aplicação por produto
  2. Cada produto exibe retorno líquido calculado pelo TaxEngine para prazos 90d, 1a, 2a, 5a — produtos LCI/LCA têm badge ou destaque visual de isenção IR
  3. Usuário filtra catálogo por tipo (Tesouro/CDB/LCI/LCA) e prazo mínimo e ordena por retorno líquido — tabela atualiza sem reload
  4. Cada produto exibe indicador visual (ícone verde/vermelho ou texto) se o retorno líquido supera CDI ou IPCA no prazo selecionado
**Plans:** 2/2 plans complete

Plans:
- [x] 22-01-PLAN.md — Backend: GET /renda-fixa/macro-rates endpoint (schema + service + router + tests)
- [x] 22-02-PLAN.md — Frontend: filters, sort by retorno liquido, beat indicator in RendaFixaContent.tsx

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 21. Screener de Ações | 3/3 | Complete    | 2026-04-12 |
| 22. Catálogo Renda Fixa | 2/2 | Complete   | 2026-04-12 |

---

## Requirements Coverage

| Requirement | Phase | Description | Status |
|-------------|-------|-------------|--------|
| SCRA-01 | Phase 21 | Tabela de ações ordenável (Ticker, Nome, Setor, Preço, Var 12m%, DY, P/L, Market Cap) | Pending |
| SCRA-02 | Phase 21 | Filtros DY mínimo / P/L máximo / Setor B3 / Market Cap | Pending |
| SCRA-03 | Phase 21 | Click ticker → /stock/[ticker] | Pending |
| SCRA-04 | Phase 21 | Paginação da tabela | Pending |
| RF-01 | Phase 22 | Catálogo agrupado por tipo com taxa, vencimento, valor mínimo | Pending |
| RF-02 | Phase 22 | Retorno líquido IR por prazo (90d/1a/2a/5a) + destaque isenção LCI/LCA | Pending |
| RF-03 | Phase 22 | Filtros por tipo/prazo, ordenação por retorno líquido, indicador CDI/IPCA | Pending |

**Coverage:** 7/7 ✓

---

## Architecture Notes

### Phase 21 — Screener de Ações

**Backend exists:**
- `screener_snapshots` table populated nightly by Celery beat (~900 tickers, from v1.1)
- Goldman Sachs screener endpoint at `/screener/` — returns top 10 scored stocks only
- **What's missing:** New endpoint returning full universe with filterable columns (DY, P/L, Setor, Market Cap, Variação 12m)

**Approach:**
- New `GET /screener/universe` endpoint returns all tickers with the required columns
- Frontend filters client-side with useMemo (same approach as Phase 17 FII Screener — ~900 tickers fits in browser memory)
- Paginação client-side or server-side (prefer client-side for consistency with Phase 17)

**Pattern to reuse:** Phase 17 FII Screener — same table + filter UX, same useMemo client-side approach, same Tailwind table styling

### Phase 22 — Catálogo Renda Fixa

**Backend exists (verify before creating new):**
- `fixed_income_catalog` table populated nightly by Celery beat (from v1.1)
- TaxEngine fully operational — IR regressivo (22.5%→15%) + LCI/LCA isenção
- RF API endpoint may already exist at `/renda-fixa` or `/fixed-income` — check before building new one

**Approach:**
- Frontend-only phase if backend endpoint exists
- If endpoint missing: thin FastAPI route wrapping TaxEngine calculations against fixed_income_catalog
- Retorno líquido calculation: TaxEngine.calculate(principal, rate, days) → net return per prazo bracket
- CDI/IPCA beat indicator: compare product net return vs current CDI rate (stored in DB or fetched from python-bcb)

---

## Key Design Decisions

### Why 2 Phases

Coarse granularity with 7 requirements maps to 2 natural delivery boundaries:

- **Phase 21** (SCRA-01/02/03/04): All four requirements deliver one coherent capability — a filterable ações screener table. They cannot ship partially (table is only useful with filters + navigation + paging). Backend universe already exists; work is a new API endpoint + frontend page.
- **Phase 22** (RF-01/02/03): All three requirements deliver one coherent capability — a usable RF catalog. Backend is fully operational; work is primarily frontend with TaxEngine integration. This is a distinct, independent capability with no dependency on Phase 21.

Each phase has 1–2 plans max (consistent with coarse granularity).

### Reuse from v1.3

- Client-side filtering with useMemo (Phase 17 FII Screener) — same pattern for Phase 21
- Table + filter UX component patterns — reuse as-is
- `get_global_db` pattern for global (non-tenant) data tables
- Nav link addition pattern for new pages

---

## v1.3 Reference (Archived)

v1.3 phases (17–20) completed 2026-04-11. Archive: `.planning/milestones/v1.3-ROADMAP.md` (if created).

| Phase | Status | Completed |
|-------|--------|-----------|
| 17 - FII Screener Table | ✅ DEPLOYED | 2026-04-04 |
| 18 - FII Detail Page + IA | ✅ DEPLOYED | 2026-04-04 |
| 19 - Opportunity Detector Page | ✅ DEPLOYED | 2026-04-05 |
| 20 - Swing Trade Page | ✅ DEPLOYED | 2026-04-11 |

---

*Roadmap created: 2026-04-12*
*Milestone: InvestIQ v1.4 — Ferramentas de Análise*

---

# InvestIQ v1.5 — AI Portfolio Advisor — Roadmap

**Milestone:** v1.5 AI Portfolio Advisor
**Phases:** 23–26 (continues from v1.4 Phase 22)
**Granularity:** Coarse (4 phases — module-driven delivery)
**Status:** Planning Complete
**Created:** 2026-04-18

---

## Phases

- [x] **Phase 23: Portfolio Health Check** — Diagnostic (ADVI-01) (completed 2026-04-18)
- [ ] **Phase 24: AI Advisor Recommendations** — Narrative + suggestions (ADVI-02)
- [x] **Phase 25: Smart Screener** — Complementary assets filtered (ADVI-03) (completed 2026-04-18)
- [x] **Phase 26: Entry Signals** — Buy suggestions with fundamentals context (ADVI-04) (completed 2026-04-18)

---

## Phase Details

### Phase 23: Portfolio Health Check

**Goal:** User sees instant portfolio diagnosis: health score, biggest risk, passive income, underperformers

**Depends on:** None (compute_portfolio_health() already exists in advisor/service.py)

**Requirements:** ADVI-01

**Success Criteria:**
  1. `/advisor` page loads portfolio health in <300ms (cached or on-demand refresh)
  2. Health Check displays: score (10-100), biggest_risk (1-sentence), passive_income_monthly, list of underperformers (up to 3)
  3. User can click "Atualizar" button to refresh health check; cache invalidates on transaction import/add
  4. Health Check card is responsive and displays on all screen sizes

**Plans:** 1/1 plan created

Plans:
- [x] 23-01-PLAN.md — Backend: GET /advisor/health (cached), POST /advisor/health/refresh + Router + Tests; Frontend: Health Check card component in AdvisorContent + usePortfolioHealth hook

---

### Phase 24: AI Advisor Recommendations

**Goal:** User receives personalized portfolio analysis referencing their actual holdings and macro context

**Depends on:** Phase 23 (health check provides context)

**Requirements:** ADVI-02

**Success Criteria:**
  1. `/advisor` page displays AI-generated diagnosis (diagnostico), positives (pontos_positivos), concerns (pontos_de_atencao), suggestions (sugestoes), next steps (proximos_passos)
  2. Analysis takes <2s to display (streaming or pre-calculated)
  3. Analysis references user's specific holdings, sectors, concentrations from health check
  4. Premium tier gate enforced (existing Stripe integration)

**Plans:** 1/1 plan created

Plans:
- [x] 24-01-PLAN.md — Backend: POST /advisor/analyze (start job, returns job_id), GET /advisor/analyze/{job_id} (poll result), async job processor, background task + Tests; Frontend: AI Diagnosis section with narrative display + useAdvisorAnalysis hooks

---

### Phase 25: Smart Screener

**Goal:** User sees screener filtered to show only complementary assets that address portfolio health risks

**Depends on:** Phase 23 (health check identifies gaps)

**Requirements:** ADVI-03

**Success Criteria:**
  1. Smart Screener filters show only sectors NOT in user's portfolio (identified by compute_portfolio_health sector_map)
  2. Results can be sorted by relevance to portfolio gaps, sector diversity score
  3. Each result links to `/stock/[ticker]` for full analysis
  4. Smart Screener data loads in <500ms (pre-calculated from screener_snapshots)

**Plans:** 1/1 plans complete

Plans:
- [x] 25-01-PLAN.md — Backend: GET /advisor/screener endpoint + get_complementary_assets service + Tests; Frontend: Smart Screener section with table, filtering, sort + useSmartScreener hook

---

### Phase 26: Entry Signals

**Goal:** User sees buy signals (RSI + fundamentals) for portfolio holdings on-demand, and universe recommendations from daily batch

**Depends on:** Phase 23 (context), Phase 25 (screener)

**Requirements:** ADVI-04

**Success Criteria:**
  1. Entry Signals for owned assets load on-demand (near-realtime, <1s)
  2. Universe recommendations load from daily Celery batch job (<100ms cache hit)
  3. Each signal shows: suggested_amount_brl, target_upside_pct, timeframe_days, stop_loss_pct
  4. Signals include RSI + MA + fundamentals context (reuse from swing_trade/opportunity_detector modules)

**Plans:** 1/1 plans complete

Plans:
- [x] 26-01-PLAN.md — Backend: GET /advisor/signals/portfolio (on-demand), GET /advisor/signals/universe (daily batch) + service functions + Celery beat task + Tests; Frontend: Entry Signals section with portfolio + universe tables + useEntrySignals hooks

---

## Progress Table

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 23. Portfolio Health Check | 1/1 | Complete | 2026-04-18 |
| 24. AI Advisor Recommendations | 1/1 | Planned | — |
| 25. Smart Screener | 1/1 | Complete   | 2026-04-18 |
| 26. Entry Signals | 1/1 | Complete   | 2026-04-18 |

---

## Requirements Coverage

| Requirement | Phase | Description | Status |
|-------------|-------|-------------|--------|
| ADVI-01 | Phase 23 | Portfolio health score, biggest risk, passive income, underperformers | Complete |
| ADVI-02 | Phase 24 | AI diagnosis + recommendations referencing user's portfolio | Planned |
| ADVI-03 | Phase 25 | Smart screener filtered to complementary assets | Planned |
| ADVI-04 | Phase 26 | Entry signals (hybrid: owned=on-demand, universe=daily) | Planned |

**Coverage:** 4/4 ✓

---

## Architecture Notes

### Common Foundation (All Phases)

- **Portfolio data:** Transactions from tenant DB (RLS-scoped)
- **Global data:** screener_snapshots, fixed_income_catalog (Celery beat, nightly updates)
- **Skills reuse:** DCF, earnings analysis, fundamentals already integrated in `/stock/[ticker]`
- **UI pattern:** Diagnostic-first flow (health → diagnosis → recommendations → signals)

### Phase 23 — Portfolio Health Check

**Backend ready:** `compute_portfolio_health()` in advisor/service.py
- No external API calls
- Pure SQL + aggregation, <200ms
- Returns: score, biggest_risk, passive_income, underperformers, data_as_of

**Frontend work:** Create health check card component, integrate into `/advisor` page

**Caching strategy:** Manual refresh + auto-invalidate on transaction event

### Phase 24 — AI Advisor Recommendations

**Backend ready:** `run_portfolio_advisor()` in ai/skills/portfolio_advisor.py
- Takes positions, P&L, allocation, macro data
- Returns structured JSON (diagnostico, pontos_positivos, etc.)
- Uses Claude API (call_llm)

**Frontend work:** Display narrative in `/advisor` page, positioned after health check

**Tier gating:** Existing Stripe integration already handles premium checks

### Phase 25 — Smart Screener

**Backend ready:** Screener universe exists (screener_v2 router, /acoes/screener from v1.4)

**Personalization logic:** Filter by missing sectors identified in health check
- SQL query: sectors in portfolio → exclude from recommendations
- Score by diversity (prefer sectors with low portfolio weight)

**Frontend work:** New component or filter toggle on screener page

### Phase 26 — Entry Signals

**Backend ready:**
- RSI + MA calculation: swing_trade/service.py
- Fundamentals context: opportunity_detector/agents/recommendation.py
- Screener universe: ~900 tickers, nightly batch

**Hybrid approach:**
- Owned assets: on-demand calculation (user's portfolio) → cache <5min
- Universe: daily Celery batch job → refresh nightly
- Two separate API routes: `/advisor/signals/portfolio` (on-demand), `/advisor/signals/universe` (cached)

**Frontend work:** Display signals section with freshness indicators ("Updated now" vs "Daily")

---

## Key Design Decisions

### Why 4 Phases

Sequential module delivery:
- **Phase 23:** Health foundation (required context for all downstream modules)
- **Phase 24:** Narrative recommendations (depends on health context)
- **Phase 25:** Smart screener filtering (depends on health sector analysis)
- **Phase 26:** Entry signals (depends on all upstream context for personalization)

Each phase delivers one coherent capability; together they create the `/advisor` page.

### Decisions Already Locked (from /gsd:discuss-phase)

1. **Smart Screener:** Complementary assets (Option A) — sectors missing from portfolio
2. **Page flow:** Diagnostic-first (Option A) — Health Check → AI Diagnosis → Recommendations → Signals
3. **Entry Signals:** Hybrid (Option C) — Owned=on-demand, universe=daily batch
4. **Health refresh:** Manual + trigger on transaction (Option C)

---

*Roadmap created: 2026-04-18*
*Roadmap planning completed: 2026-04-18*
*Milestone: InvestIQ v1.5 — AI Portfolio Advisor*
*Status: Ready for execution*

---

# InvestIQ v1.6 — Comparador RF vs RV — Roadmap

**Milestone:** v1.6 Comparador RF vs RV
**Phases:** 27 (continues from v1.5 Phase 26)
**Granularity:** Coarse (1 phase — TaxEngine + macro rates already built; tool only useful when table + chart ship together)
**Status:** Shipped 2026-04-19
**Created:** 2026-04-18

---

## Overview

Ferramenta standalone para o usuário comparar o retorno líquido de um produto de renda fixa (CDB/LCI/LCA/Tesouro Direto) contra benchmarks de mercado (CDI, SELIC, IPCA+) em qualquer prazo. O backend é thin — TaxEngine, tabela `fixed_income_catalog` e taxas macro no Redis já existem. O trabalho real é a UI: formulário de entrada, tabela comparativa com rentabilidade real e gráfico de evolução do patrimônio.

Por isso, 1 fase única: tabela e gráfico só são úteis juntos, e dividir backend/frontend em fases separadas criaria overhead sem valor.

---

## Phases

- [x] **Phase 27: Comparador RF vs RV** — Endpoint `/comparador` + página `/comparador` com tabela de retorno líquido vs benchmarks, coluna rentabilidade real e gráfico de evolução do patrimônio (completed 2026-04-18)

---

## Phase Details

### Phase 27: Comparador RF vs RV

**Goal:** Usuário informa valor, prazo e tipo de produto RF e vê tabela comparativa de retorno líquido nominal e real versus CDI, SELIC e IPCA+, com gráfico de evolução do patrimônio ao longo do prazo

**Depends on:**
- `TaxEngine` at `backend/app/modules/market_universe/tax_engine.py` (IR regressivo 22.5%→15%, LCI/LCA isenção) — no changes needed
- Macro rates (CDI/SELIC/IPCA) in Redis, served by existing `GET /screener/macro-rates` endpoint — no changes needed
- `fixed_income_catalog` table: Tesouro/CDB/LCI/LCA taxa + vencimento — populated nightly by Celery beat — no changes needed
- `GET /renda-fixa` endpoint (Phase 22) — read before implementing to confirm available fields

**Requirements:** COMP-01, COMP-02

**Success criteria:**
1. Usuário acessa `/comparador`, preenche valor (R$), prazo (meses) e seleciona tipo de produto RF (CDB/LCI/LCA/Tesouro Direto) e vê tabela comparativa com retorno líquido nominal para o produto RF selecionado, CDI, SELIC e IPCA+, com IR regressivo aplicado corretamente via TaxEngine
2. Tabela exibe coluna de rentabilidade real (retorno nominal descontado IPCA projetado) para cada alternativa — LCI/LCA mostram destaque visual de isenção IR
3. Gráfico de linha mostra a evolução do patrimônio acumulado mês a mês para cada alternativa ao longo do prazo informado
4. Formulário atualiza tabela e gráfico instantaneamente ao alterar qualquer campo (valor, prazo, tipo RF) sem reload de página

**Canonical refs:**
- `backend/app/modules/market_universe/tax_engine.py` — TaxEngine core (read before implementing backend)
- `backend/app/modules/market_universe/router.py` — existing `/renda-fixa` and `/screener/macro-rates` endpoints (confirm structure)
- `frontend/src/features/billing/components/UpgradeCTA.tsx` — Tailwind card pattern to reuse
- Phase 22 plans (`22-01-PLAN.md`, `22-02-PLAN.md`) — established TaxEngine integration pattern for frontend

**Notes:**
- Backend: new `GET /comparador` endpoint takes query params `valor`, `prazo_meses`, `tipo_rf` — calls TaxEngine for each benchmark row and returns projection array (one entry per month) + summary table row per alternative
- Frontend: standalone page at `frontend/app/comparador/page.tsx` — no portfolio context required, accessible to all users (free tier)
- Chart: use Recharts (already in codebase from other pages) — LineChart with one series per alternative
- Projection math: compound monthly growth — `P * (1 + r_monthly)^t` for each month — client-side or backend-side both viable; prefer backend to keep math in one place (TaxEngine)
- Rentabilidade real: `(1 + retorno_nominal) / (1 + ipca_acumulado) - 1` — IPCA from Redis macro rates
- Tipo RF input maps to a product from `fixed_income_catalog` (best available rate for that type) or user-supplied custom rate — simplest approach: use catalog median rate for selected type
- No auth required: tool is standalone, no tenant context needed — use `get_global_db` not `get_db`

**Plans:** 3/3 plans complete

Plans:
- [x] 27-01-PLAN.md — Backend: extend MacroRatesResponse with selic field (+ service reads market:macro:selic + tests + frontend type mirror)
- [x] 27-02-PLAN.md — Frontend: new comparador types + useComparadorCalc useMemo hook + ComparadorContent.tsx rewrite with form + 4-row table (LCI/LCA isento, Tesouro IPCA+ spread input) + cleanup stale v1.0 api.ts/useComparador.ts
- [x] 27-03-PLAN.md — Frontend: ComparadorChart.tsx (Recharts LineChart, 4 series) wired into ComparadorContent + Playwright e2e spec v1.6-comparador.spec.ts

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 27. Comparador RF vs RV | 3/3 | Complete    | 2026-04-18 |

---

## Requirements Coverage

| Requirement | Phase | Description |
|-------------|-------|-------------|
| COMP-01 | Phase 27 | Valor + prazo + tipo RF → tabela retorno líquido nominal vs CDI/SELIC/IPCA+ com IR via TaxEngine |
| COMP-02 | Phase 27 | Coluna rentabilidade real (nominal descontado IPCA) + gráfico evolução patrimônio acumulado |

**Coverage:** 2/2 ✓

---

## Execution Notes

### Patterns to reuse

- **TaxEngine call pattern** (Phase 22): `tax_engine.calculate_net_return(principal, annual_rate, days, product_type)` — returns net amount after IR bracket
- **Macro rates fetch** (Phase 22 `22-01-PLAN.md`): `GET /screener/macro-rates` → `{ cdi_rate, selic_rate, ipca_rate }` already cached in Redis
- **`get_global_db`**: use for `/comparador` endpoint — no tenant isolation needed (public catalog data)
- **Recharts LineChart**: already used in swing_trade or portfolio pages — find existing usage and copy import pattern
- **Client-side state with no useMemo** (small dataset): comparador computes N rows (4 alternatives) × M months (≤120) — trivial, no caching needed

### Key implementation sequence

1. Backend: `GET /comparador` endpoint — validate params, fetch macro rates from Redis, fetch catalog rate for `tipo_rf`, run TaxEngine + projection loop, return `{ summary: [...], projection: [...] }`
2. Backend tests: parametric test covering CDB (IR applies), LCI (isenção), Tesouro IPCA+ (mixed), 12-month and 60-month prazos
3. Frontend: `/comparador` page — form (valor, prazo slider, tipo_rf select), call API on change, render table + Recharts chart
4. Nav: add "Comparador" link to sidebar/nav alongside /renda-fixa

---

*Milestone: InvestIQ v1.6 — Comparador RF vs RV*
*Roadmap created: 2026-04-18*
