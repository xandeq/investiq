# Project Research Summary

**Project:** InvestIQ v1.1 — Onde Investir milestone
**Domain:** Investment portfolio SaaS — Brazilian market (B3 screeners, renda fixa catalog, allocation simulator, AI advisor)
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH

## Executive Summary

InvestIQ v1.1 extends a deployed, validated base (auth, portfolio management, market data, broker import) with six new capabilities: screener de acoes, screener de FIIs, catalogo de renda fixa, comparador RF vs RV, simulador de alocacao, and the AI wizard "Onde Investir". The key insight from research is that **the differentiator is not screener parity with StatusInvest** — that battle is already lost. The moat is portfolio integration: showing users what to buy given what they already own. No competitor (StatusInvest, Kinvo, Gorila) offers an AI wizard that reads the user's real portfolio and suggests allocation adjustments in context. That is the feature worth building.

The recommended approach requires zero new Python packages and zero new frontend libraries for core features. The two genuinely new architectural patterns are: (1) global (non-tenant) PostgreSQL tables for market-wide screener snapshots, requiring a new `get_global_db` FastAPI dependency distinct from the existing tenant-scoped `get_db`; and (2) a daily Celery beat task category that builds universe-wide snapshots, distinct from the existing per-user recalc pattern. Both are straightforward, additive extensions of proven patterns already in the deployed codebase.

The top risks are regulatory and data-source related, not technical. The CVM suitability framework (Res. 30/2021) prohibits the AI wizard from naming specific tickers — output must be asset class percentages only, with a pre-output disclaimer. Two external data sources require pre-phase validation: ANBIMA API registration timeline (free but requires developer onboarding), and the confirmed death of the old Tesouro Direto JSON endpoint (404 since August 2025). The LCI/LCA IR exemption reform pending in 2026 means tax logic must be stored as DB config, not hardcoded constants.

---

## Key Findings

### Recommended Stack

The v1.1 stack is entirely additive — no existing dependencies change. The deployed combination of FastAPI + SQLAlchemy 2.x async + PostgreSQL 16 + Redis + Celery + Next.js 15 + shadcn/ui + Tremor + TanStack Query + brapi.dev + python-bcb handles all v1.1 requirements without modification.

The only conditional new dependency is `authlib==1.3.x` (OAuth2 client credentials), required only if ANBIMA API uses OAuth2 auth — this must be confirmed at `developers.anbima.com.br` before the Tesouro Direto phase begins. Two shadcn/ui components (`Slider`, `Progress`) may need to be added via CLI if not already installed (`npx shadcn@latest add slider progress`) — zero-cost, using `@radix-ui/react-slider` already in the monorepo.

**New data sources for v1.1:**
- `dados.cvm.gov.br` (CVM Open Data): FII segment and vacancy metadata — official, zero-auth, stable CSV downloads
- ANBIMA API (`api.anbima.com.br/feed/precos-indices`): Tesouro Direto live rates — official, free developer registration required
- Tesouro Transparente CKAN CSVs: confirmed fallback for Tesouro Direto if ANBIMA onboarding delays
- `fixed_income_catalog` table (admin-seeded): reference rates for CDB/LCI/LCA — no public API exists for live bank rates

**What NOT to add:**
- Any scraping of StatusInvest, Funds Explorer, or Investidor10 — ToS violation, Cloudflare-blocked, fragile
- Additional charting libraries — Recharts + Tremor already cover all screener and simulator chart needs
- Real-time screener WebSockets — brapi.dev data is 15-min delayed; TanStack Query polling every 5 min is sufficient

### Expected Features

**Must have (table stakes — every competitor has this):**
- Screener de acoes: filter by DY, P/L, P/VP, EV/EBITDA, sector, market cap, average daily volume
- Screener de FIIs: filter by P/VP, DY, segmento (Tijolo/Papel/Hibrido/FoF/Agro), vacancia financeira, numero de cotistas
- Tesouro Direto: SELIC, IPCA+, IPCA+ com Juros Semestrais, Prefixado — with current rates, maturity dates, unit prices
- CDB/LCI/LCA reference rate ranges with full IR regressivo calculation (4-tier: 22.5%/20%/17.5%/15% by holding days)
- LCI/LCA isencao IR (0% for PF currently, subject to 2026 reform)
- AI wizard input: valor disponivel + prazo + perfil; output: allocation percentages by asset class only

**Should have (differentiators — InvestIQ advantage over competitors):**
- "Ativos que nao tenho" toggle in both screeners — filters universe to tickers absent from user's portfolio
- FII P/VP with segment-aware benchmarks — Tijolo and Papel FIIs have different fair-value thresholds
- Comparador RF vs RV: "seu portfolio rendeu X% — equivalente a CDB de Y% ao ano" with current portfolio integration
- Simulador considers current portfolio for rebalancing suggestions, not just greenfield allocation
- Wizard reads current portfolio allocation and shows delta vs ideal ("voce tem 70% em acoes, sugestao e 50%")
- Macro context integration: current SELIC trend informs wizard output rationale
- Net return displayed after IR adjustment — no competitor presents this clearly to retail investors

**Defer to v2+:**
- Modern Portfolio Theory / Markowitz optimization (covariance matrix required, significantly higher complexity)
- Open Finance Brasil OAuth integration for importing actual CDB/LCI positions at real user-specific rates
- Live bank-specific CDB/LCI rate aggregation (requires commercial data partnership — no public API exists)
- Chat-style free-form investment Q&A
- Backtesting screener or allocation strategies
- Social screening (other users' top picks)

### Architecture Approach

v1.1 introduces two new architectural patterns on top of the existing multi-tenant FastAPI monolith. First, global (non-tenant) data tables (`screener_snapshots`, `fii_metadata`, `fixed_income_catalog`) require a new `get_global_db` FastAPI dependency that deliberately skips the `SET LOCAL app.current_tenant` injection performed by the existing `get_db` — using the wrong dependency for these tables would corrupt behavior. Second, three new Celery beat tasks handle universe-wide data refresh at different cadences (daily for screener, weekly for FII metadata, every 6 hours for Tesouro rates), distinct from the existing per-user recalc tasks. All screener and catalog endpoints are synchronous reads against pre-built snapshot tables — zero external API calls per user request.

**Major new components:**

1. `screener_snapshots` table + `refresh_screener_universe` Celery beat task — daily brapi.dev bulk fetch for all ~900 B3 tickers with 200ms sleep between calls
2. `fii_metadata` table + `refresh_fii_metadata` Celery beat task — weekly CVM CSV download and pandas upsert
3. `tesouro_rates` Redis namespace + `refresh_tesouro_rates` Celery beat task — ANBIMA API or CKAN CSV every 6 hours
4. `fixed_income_catalog` table — admin-seeded CDB/LCI/LCA reference rate ranges
5. `TaxEngine` class — IR regressivo rules with DB-backed configurable rates (not hardcoded constants)
6. `AllocationEngine` class — synchronous allocation math, portfolio-aware, target < 500ms
7. `advisor/` FastAPI router + Celery task — async 202+poll pattern, same as existing AI analysis pipeline, reuses `call_llm()` from `ai/provider.py`

**Redis namespace additions (strict separation from existing `market:*`):**
- `screener:universe:{TICKER}` (daily refresh cadence)
- `tesouro:rates:{BOND_CODE}` (6-hour TTL)
- `fii:metadata:{TICKER}` (weekly refresh cadence)

### Critical Pitfalls

1. **Tesouro Direto unofficial JSON is dead** — `tesourodireto.com.br/json/.../treasurybondsinfo.json` returns 404 since August 15, 2025. Use ANBIMA official API (register at developers.anbima.com.br) or Tesouro Transparente CKAN CSV as confirmed no-auth fallback. Choose data source in Phase 1 before writing any Tesouro feature.

2. **CDB/LCI/LCA live rates don't exist as a public API** — Open Finance Brasil exposes user positions, not product catalogs. Design `fixed_income_catalog` as curated reference rates anchored to CDI/IPCA ranges. Label in UI as "taxas de referencia de mercado", never "oferta ao vivo" or "taxas em tempo real".

3. **Screener universe rebuild cannot happen per-request** — ~900 tickers x 1 req each = rate limit breach and >10s latency if called synchronously per user. Every screener endpoint must query the pre-built `screener_snapshots` table. Any endpoint calling `brapi_client.fetch_fundamentals()` outside a Celery task is a defect.

4. **AI wizard naming specific tickers violates CVM Res. 30/2021** — wizard output must be asset class percentages only, never ticker symbols. Add ticker-pattern post-processing validation in the Celery task (reject response if it contains uppercase 4-6 char strings). CVM disclaimer must appear before results are rendered, not after or as a footnote.

5. **IR regressivo omission actively misleads users** — a flat 15% IR assumption overstates short-hold CDB returns and understates the LCI/LCA advantage. `TaxEngine` must implement the full 4-tier table (22.5% <=180d, 20% 181-360d, 17.5% 361-720d, 15% >720d). LCI/LCA IR rate must be a DB config value (currently 0%, 5% proposed for 2026 reform). FII distributions = 0% IR (Lei 11.033/2004).

6. **FII P/VP without segment context produces wrong screening results** — Tijolo (brick-and-mortar real estate) and Papel (CRI/CRA) FIIs have completely different fair-value P/VP thresholds. CVM `fii_metadata` segment must be present from day one in the screener. Never apply a universal P/VP threshold without a visible segment column.

7. **Redis namespace collision with existing `market:*` keys** — define `screener:*`, `tesouro:*`, `fii:*` namespaces explicitly before writing any cache code. Any v1.1 cache key using the `market:` prefix for screener or catalog data is a bug.

---

## Implications for Roadmap

All four research files converge on the same strict dependency order. Phases 2-4 can be parallelized after the Phase 1 foundation migration lands. Phase 5 (simulator) depends on Phase 4's net return math being validated. Phase 6 (wizard) depends on all preceding phases because it aggregates every data source. This maps to a 6-phase roadmap with clear unblocking relationships.

### Phase 1: Foundation — Migrations, Tax Engine, Data Source Decisions

**Rationale:** All v1.1 phases depend on the new database tables and the `get_global_db` dependency being in place. The `TaxEngine` built here is consumed by Phases 4, 5, and 6. The two external data source decisions (ANBIMA vs CKAN for Tesouro, confirming no CDB API exists) must be resolved here — choosing the wrong source mid-build is expensive to unwind.

**Delivers:** Alembic migrations for `screener_snapshots`, `fii_metadata`, `fixed_income_catalog`; `get_global_db` FastAPI dependency; Redis namespace constants documented in codebase; `TaxEngine` class with DB-backed IR rate config; ANBIMA API registration initiated (or CKAN fallback confirmed as primary); Fixed income catalog seeded with reference rate ranges; CDB/LCI/LCA UI copy reviewed and approved ("taxas de referencia").

**Avoids:** Pitfalls 1 (dead JSON endpoint chosen before any code written), 2 (CDB API expectation eliminated in data model design), 5 (TaxEngine with DB config, not constants, built here not bolted on later), 7 (Redis namespaces defined upfront)

**Research flags:** ANBIMA API auth model must be confirmed at developers.anbima.com.br before writing the Tesouro fetch task. If OAuth2 client credentials, add `authlib==1.3.x` to requirements.

### Phase 2: Data Pipelines (Celery Beat Tasks)

**Rationale:** The screener UI, renda fixa catalog, and FII screener are useless without data. Build and validate the three Celery beat tasks before any endpoint. The first production run of the 900-ticker brapi.dev rebuild must be monitored for rate limit behavior — this is the highest-risk unknown in the entire milestone.

**Delivers:** `refresh_screener_universe` Celery beat task (daily, ~900 brapi.dev calls with 200ms sleep, exponential backoff with jitter); `refresh_fii_metadata` task (weekly CVM CSV download and pandas upsert); `refresh_tesouro_rates` task (every 6 hours, ANBIMA/CKAN + Redis cache); Admin-level manual refresh trigger endpoint; Pipeline failure alerting; Monitoring for brapi.dev throttle events on first production run.

**Avoids:** Pitfall 3 (snapshot table validated before any screener endpoint is built), Pitfall 6 (FII segment required from the first CVM CSV ingest — not added later)

**Research flags:** brapi.dev rate limit behavior under universe rebuild is an empirical unknown — monitor first run and document throttle thresholds. Otherwise standard Celery beat task patterns; skip research-phase.

### Phase 3: Screener Endpoints + Renda Fixa Catalog

**Rationale:** With data pipelines validated, the API and frontend layers are straightforward SQL queries and catalog assembly. Both screeners and the renda fixa catalog can be built in parallel. The "ativos que nao tenho" differentiator is a LEFT JOIN against the user's existing transactions table — simple but must use the right DB dependency (global for screener data, tenant-scoped for the portfolio JOIN).

**Delivers:** `GET /screener/acoes` with filter params (DY, P/L, P/VP, EV/EBITDA, sector, market cap, volume, `exclude_owned` flag); `GET /screener/fiis` with FII-specific filters (segmento, vacancia, cotistas, DY, P/VP); `GET /renda-fixa/catalogo` assembling Tesouro rates from Redis + CDB/LCI/LCA reference ranges + net returns by holding period via TaxEngine; Frontend screener pages with filter sidebar, sortable paginated results table, and segment column always visible before P/VP filter.

**Avoids:** Pitfall 2 (UI copy says "taxas de referencia de mercado", not "taxas ao vivo"), Pitfall 6 (segmento column visible before any P/VP threshold filter)

**Research flags:** Screener filter UI and sortable tables are standard patterns — skip research-phase. The `exclude_owned` JOIN is a minor complexity using existing portfolio query patterns.

### Phase 4: Comparador Renda Fixa vs Renda Variavel

**Rationale:** Depends on Phase 3 (Tesouro rates in Redis, CDB/LCI reference rates in DB, CDI/SELIC/IPCA already in Redis from v1.0). Pure calculation feature — no new data sources or infrastructure. The portfolio integration ("seu portfolio rendeu X%") is the key differentiator vs a generic calculator.

**Delivers:** `GET /renda-fixa/comparador?prazo=12&valor=50000` returning net returns by asset class after IR via TaxEngine; Comparison table by holding period (6m, 1a, 2a, 5a) for CDB vs LCA vs Tesouro SELIC vs IBOVESPA historical via python-bcb; Portfolio integration showing user's annualized return vs equivalent fixed income benchmarks; Frontend comparison table with IR-adjusted net return columns and holding period selector.

**Avoids:** Pitfall 5 (TaxEngine from Phase 1 applied here — not reimplemented)

**Research flags:** Low complexity, standard calculation patterns. Skip research-phase.

### Phase 5: Simulador de Alocacao

**Rationale:** Depends on Phase 4's net return math being validated in production, Phase 2-3's screener aggregate DY statistics, and Phase 1's TaxEngine. The `AllocationEngine` is new business logic but all inputs are already in Redis or PostgreSQL. Synchronous endpoint, target < 500ms. This is the first feature with no competitor equivalent — the allocation parameters (expected returns by risk profile) are business decisions requiring requirements sign-off.

**Delivers:** `POST /simulador/alocacao` accepting valor, prazo_anos, perfil (conservador/moderado/arrojado), incluir_carteira flag; `AllocationEngine` returning allocation mix percentages + 3 scenarios (pessimista/base/otimista) + IR-adjusted projections per scenario per asset class; Portfolio-aware mode: reads current allocation and suggests incremental rebalancing toward ideal; Frontend simulator page with multi-class allocation sliders (shadcn Slider), donut chart (Tremor DonutChart), scenario comparison bar chart (Recharts).

**Avoids:** Pitfall 5 (IR applied per asset class and holding period in AllocationEngine output, not as a flat rate)

**Research flags:** Allocation model parameters — conservative/moderate/aggressive risk profiles need explicit expected return and volatility assumptions. These are domain decisions, not technical ones. Flag for requirements review with Alexandre before implementation: what are the assumed annual return ranges per asset class per profile?

### Phase 6: Wizard "Onde Investir" (AI Advisor)

**Rationale:** This is the milestone's unique moat and hard-depends on all preceding phases. The AI prompt aggregates portfolio context, screener top picks, Tesouro rates, macro data, and allocation context into ~8-12KB. Uses the existing async 202+poll pattern and `call_llm()` from `ai/provider.py` unchanged. No new AI infrastructure. The CVM compliance requirements for this feature are the highest in the entire milestone.

**Delivers:** `POST /advisor/wizard` accepting valor, prazo, perfil + auto-reading current portfolio; Celery task aggregating full prompt context from all v1.1 data sources; LLM response parsed to structured `{acoes_pct, fiis_pct, renda_fixa_pct, caixa_pct, rationale}`; Post-processing ticker-pattern validation (reject if response contains uppercase 4-6 char strings); Multi-step wizard frontend (3-5 steps) using shadcn Progress component + Card per step; CVM disclaimer rendered visibly before results, not as a footnote after; Portfolio delta display: "voce tem X% em acoes, sugestao e Y%".

**Avoids:** Pitfall 4 (ticker output validation in Celery task + explicit negative constraint hardcoded in prompt template; never recommend specific assets)

**Research flags:** CVM compliance wording for the pre-output disclaimer must be reviewed against current CVM Res. 19/2021 text by Alexandre before production launch. LLM prompt engineering for compliant output (asset class percentages only, no tickers, no imperative language) will likely require multiple iteration cycles — build in review time before declaring this phase complete.

### Phase Ordering Rationale

- Phase 1 is unconditionally first: new tables, `get_global_db`, TaxEngine, and data source decisions unblock all other phases
- Phases 2, 3, and 4 can overlap after Phase 1 migrations land: pipelines, screener endpoints, and comparador have no inter-dependencies
- Phase 5 (simulator) must follow Phase 4 because it reuses and depends on the net return calculation being validated in production
- Phase 6 (wizard) is the integration test of the entire milestone and must be last — it aggregates every preceding component
- The "ativos que nao tenho" differentiator ships in Phase 3 (not deferred to Phase 6) because it requires only a LEFT JOIN against the already-deployed portfolio data — cheap to include at screener build time

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new dependencies confirmed by reading live deployed `brapi.py` adapter code. All v1.1 additions are additive. brapi.dev `/quote/list` endpoint capabilities confirmed from live code inspection. |
| Features | MEDIUM-HIGH | Table stakes well-researched against competitor analysis (StatusInvest, Kinvo, Gorila). Differentiator features (portfolio-aware allocation, AI wizard) have no prior art to compare against — judgment calls based on research synthesis. |
| Architecture | HIGH | Integration patterns confirmed by reading actual deployed `app/`, `market_data/brapi.py`, `ai/provider.py`. `get_global_db` pattern is a straightforward, well-understood extension. Redis namespace plan is forward-compatible with existing schema. |
| Pitfalls | HIGH (technical) / MEDIUM (regulatory) | Technical pitfalls confirmed: dead Tesouro JSON endpoint (Aug 2025 community reports), brapi.dev per-request rate limits (inferred from deployed rate limiter code), Redis namespace risks (live schema read). CVM suitability specifics are MEDIUM — general framework understood, exact compliance wording needs legal review. |

**Overall confidence:** MEDIUM-HIGH

### Gaps to Address

- **ANBIMA API registration timeline:** Free registration at developers.anbima.com.br — timeline unknown (may be instant or take days). Initiate in Phase 1. If blocked, Tesouro Transparente CKAN CSV is a confirmed working fallback (zero auth, batch-only, daily cadence — acceptable for the screener update frequency).

- **brapi.dev rate limits under 900-ticker daily rebuild:** The Startup plan (R$59.99/mo) has no published hard rate limit. First production run of the universe rebuild must be monitored with logging and alerting. If throttled, switch to weekly rebuild cadence — fundamentals (P/L, P/VP) change slowly and weekly refresh is acceptable for a screener use case.

- **LCI/LCA IR exemption reform (Lei 15.270/25 proposal):** A government proposal to tax PF LCI/LCA holders at 5% IR na fonte is under active discussion as of March 2026. The `TaxEngine` must store this as a DB config value (not a constant) so it can be updated without a code deployment. Track the legislative status during Phase 1 design.

- **Allocation model parameters:** The simulator's expected return assumptions for conservative/moderate/aggressive profiles are business decisions, not research findings. Required before Phase 5 implementation: what annual return range does "conservador" assume for each asset class? What volatility bands are used for pessimista/otimista scenarios? Needs explicit sign-off from Alexandre.

- **CVM wizard disclaimer copy:** The exact disclaimer wording ("Analise informativa — nao constitui recomendacao de investimento (CVM Res. 19/2021)") should be reviewed against the current CVM resolution text before Phase 6 production launch. The general framework is clear but the exact formulation may matter.

---

## Sources

### Primary (HIGH confidence)
- Deployed `brapi.py` adapter code (read directly) — brapi.dev endpoint capabilities, plan details, rate limit handling, module support confirmed from live code
- [CVM Open Data](https://dados.cvm.gov.br/dados/FII/) — FII monthly informes (vacancia, cotistas), cadastro (segmento, tipo) — official Brazilian regulator, stable
- [ANBIMA Developers portal](https://developers.anbima.com.br/en/documentacao/precos-indices/apis-de-precos/titulos-publicos/) — Tesouro Direto difusao-taxas API documentation — official Brazilian bond market association
- BCB SGS series codes: CDI=12, SELIC=432, IPCA=433 — official BCB open data, stable
- CVM Resolucao 30/2021 — suitability requirements; CVM Res. 19/2021 — investment advice regulation
- Receita Federal IR rules: Lei 11.033/2004 (FII isencao), tabela regressiva RF (official Receita documentation)

### Secondary (MEDIUM confidence)
- [brapi.dev docs](https://brapi.dev/docs) — `/quote/list` pagination, type filter, module availability
- [Tesouro Transparente CKAN](https://www.tesourotransparente.gov.br/ckan/dataset?tags=Tesouro+Direto) — CSV batch download availability confirmed
- [shadcn/ui Slider docs](https://ui.shadcn.com/docs/components/radix/slider) — multi-value range support confirmed
- Community reports confirming tesourodireto.com.br JSON 404 since August 2025 — multiple independent sources
- [Open Finance Brasil developer docs](https://openfinancebrasil.atlassian.net/wiki/spaces/OF/pages/75038738) — confirmed covers user positions, not product catalogs

### Tertiary (LOW confidence)
- LCI/LCA IR reform (Lei 15.270/25 proposal) — legislative text under discussion, not yet enacted; status may change during v1.1 development
- Fintz API pricing (api.fintz.com.br) — third-party Tesouro API, pricing undisclosed; not recommended as primary source
- Open Finance Brasil Phase 3 timeline — user-consent CDB position import; speculative future capability, out of scope for v1.1

---

*Research completed: 2026-03-21*
*Scope: v1.1 additions only — base project (auth, portfolio, market data, broker import) is deployed and excluded*
*Supersedes: SUMMARY.md from 2026-03-13 (v1.0 research)*
*Ready for roadmap: yes*
