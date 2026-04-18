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
