# Stack Research

**Domain:** SaaS de gestão de investimentos — InvestIQ v1.1 (Onde Investir milestone)
**Researched:** 2026-03-21
**Confidence:** MEDIUM-HIGH (brapi.dev modules confirmed via live code inspection; Tesouro Direto JSON endpoint confirmed deprecated Aug 2025; CDB/LCI API landscape MEDIUM)

---

## Context: What v1.1 Adds

This file extends the v1.0 STACK.md with only the **new stack additions** required for:
- Screener de ações (DY, P/L, P/VP, setor, liquidez — all B3)
- Screener de FIIs (P/VP, DY, liquidez, segmento, vacância)
- Catálogo de renda fixa (Tesouro Direto, CDB, LCI, LCA com taxas atuais)
- Comparação renda fixa vs renda variável (retorno líquido ajustado por IR/isenção)
- Simulador de alocação (R$X → diversificação, projeção)
- Wizard "Onde Investir" guiado por IA

**Do not re-read as baseline** — existing stack (FastAPI, PostgreSQL, Redis, Celery, Next.js 15, shadcn/ui, Tremor, TanStack Query, brapi.dev, python-bcb) is deployed and validated.

---

## Core Technologies (Already Deployed — DO NOT change)

| Technology | Version | Purpose |
|------------|---------|---------|
| FastAPI | 0.115.x | API runtime |
| SQLAlchemy 2.x async + asyncpg | 0.29.x | ORM + driver |
| PostgreSQL 16 + RLS | — | Multi-tenant data store |
| Redis 7 + Celery 5.4 | — | Cache + background jobs |
| Next.js 15 (App Router) | — | Frontend |
| shadcn/ui + Tremor | latest/3.x | Dashboard UI components |
| TanStack Query | 5.x | Frontend data fetching |
| brapi.dev | REST API | B3 quotes + fundamentals |
| python-bcb | 0.1.x | BCB macro data (SELIC, CDI, IPCA) |

---

## New Stack Additions for v1.1

### 1. Screener de Ações e FIIs — Data Source

**Decision: Extend existing brapi.dev integration. No new data source needed.**

The existing `BrapiClient.fetch_fundamentals()` (already in production) already calls
`/quote/{ticker}?modules=defaultKeyStatistics,financialData` which returns P/L, P/VP, DY,
EV/EBITDA. The gap is: this fetches one ticker at a time. For a screener, we need bulk.

brapi.dev `/api/quote/list` endpoint supports:
- `type=stock` or `type=fund` (FII filter)
- `sortBy=` field name, `sortOrder=asc|desc`
- `limit=` and `page=` for pagination
- Returns symbol, close, change, volume, and basic metrics

**Limitation confirmed:** The `/quote/list` bulk endpoint does NOT return full fundamentals (no P/L, P/VP, DY). It returns price/volume/basic data only. Full fundamentals require the per-ticker `/quote/{ticker}?modules=...` endpoint.

**Architecture decision for screener:** Build a daily Celery beat task that:
1. Fetches all B3 tickers via `/quote/list?type=stock&limit=500` (paginated)
2. For each ticker, fetches fundamentals via `/quote/{ticker}?modules=defaultKeyStatistics,financialData`
3. Stores snapshot in `screener_snapshot` PostgreSQL table (refreshed daily)
4. Screener API reads from this table — zero external API calls per user request

This is the only approach that works within brapi.dev free/startup tier rate limits. The
existing `BrapiClient` class requires only minor additions (a `fetch_all_tickers` method).

**Confidence:** HIGH — confirmed by reading actual deployed `brapi.py` adapter code.

### 2. FII-Specific Data (vacância, segmento, tipo de fundo)

**Decision: dados.cvm.gov.br (CVM Open Data) for FII metadata. brapi.dev for pricing.**

Vacância and segmento (lajes corporativas, shoppings, galpões logísticos, etc.) are NOT
available in brapi.dev. These are reported quarterly in CVM's FII informe mensal.

| Source | Data | Endpoint | Auth |
|--------|------|----------|------|
| CVM Open Data | FII informes mensais (vacância, PL, cotistas) | `https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/` | None |
| CVM Open Data | FII cadastro (segmento, tipo, administrador) | `https://dados.cvm.gov.br/dados/FII/CAD/` | None |
| brapi.dev | FII price, DY, P/VP (priceToBook) | `/quote/{TICKER11}?modules=defaultKeyStatistics` | BRAPI_TOKEN |

**Implementation pattern:** A weekly Celery task downloads CVM's CSV files (`FII_INF_MENSAL_YYYY.csv`),
parses them with pandas, and upserts into a `fii_metadata` table. No new Python library is needed —
pandas is already in the Celery worker environment.

**Confidence:** HIGH — CVM Open Data is official, stable, documented at dados.cvm.gov.br.

### 3. Tesouro Direto — Taxas Atuais

**Decision: Use B3 official Tesouro Direto developer API, NOT the old JSON endpoint.**

The previously documented endpoint
`https://www.tesourodireto.com.br/json/br/com/b3/tesourodireto/service/api/treasurybondsinfo.json`
returned 404 since August 15, 2025 (confirmed by community search). This source is dead.

**Replacement options ranked:**

| Source | Type | Quality | Auth | Cost |
|--------|------|---------|------|------|
| **B3 Tesouro Direto API** | Official | HIGH | B2B registration | Free for registered developers |
| **Tesouro Transparente CKAN** | Official CSVs | MEDIUM | None | Free — but download-only, not live |
| **Fintz API** (`api.fintz.com.br`) | Third-party | HIGH | API key | Paid (pricing not published — contact) |
| **ANBIMA API** (`api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/difusao-taxas`) | Official | HIGH | Registration required | Free for registered entities |
| Scraping tesourodireto.com.br | Scraping | LOW | — | Free, but Cloudflare-protected, fragile |

**Recommended: Use ANBIMA API as primary source.**

ANBIMA (`https://api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/difusao-taxas`)
provides bid/ask rates, unit prices (PU), and indicative rates for all Tesouro Direto bonds.
It is officially documented at developers.anbima.com.br. Requires free registration as a
developer/participant.

Fallback: If ANBIMA registration is not feasible short-term, use the Tesouro Transparente
CKAN CSVs (`https://www.tesourotransparente.gov.br/ckan/dataset?tags=Tesouro+Direto`) as daily
batch downloads. Less convenient but zero auth/registration required.

**No new Python library needed** — `httpx` (already in requirements) handles both APIs.

Store fetched rates in `tesouro_rates` table, refreshed daily via Celery beat.

**Confidence:** MEDIUM for ANBIMA API (registration needed — timeline unknown). HIGH for CKAN fallback.

### 4. CDB / LCI / LCA — Taxas Atuais

**Decision: No real-time API exists for retail CDB/LCI/LCA rates. Use curated catalog model.**

There is no public API that provides current CDB/LCI/LCA rates across multiple banks the way
brapi.dev provides B3 quotes. The Open Finance Brasil APIs for renda fixa bancária (Phase 2
of Open Finance) expose *a user's own positions* — they do NOT expose current product offers
to third-party apps.

**What actually exists:**

| Source | Coverage | Approach | Verdict |
|--------|----------|----------|---------|
| Open Finance Brasil | User's own CDB/LCI positions | OAuth per user | Not useful for catalog |
| Bank/corretora APIs (XP, BTG, etc.) | Their own products only | No public dev API | Not accessible |
| Investidor10 / Renda Fixa BR | Aggregated rates (web) | Scraping only | Fragile |
| Manual curated catalog | Curated typical rates by type/indexer | Manual update | Viable for MVP |

**Recommended approach for MVP:** Build a curated catalog with:
1. A `fixed_income_catalog` table with columns: `type` (CDB|LCI|LCA), `indexer` (CDI|IPCA|prefixado),
   `rate_min`, `rate_max`, `rate_typical`, `term_months_min`, `term_months_max`, `updated_at`
2. Admin endpoint to update rates weekly (Alexandre updates manually, or a Celery task scrapes
   a single reliable source like XP's public renda fixa page)
3. All return calculations use `python-bcb` for live CDI/SELIC/IPCA reference rates (already deployed)

This is the same approach used by StatusInvest's "simulador de renda fixa" — they do not have a
live API feed either; they maintain curated rate data.

**Future upgrade path:** If Open Finance Brasil individual data consent is implemented, users can
optionally connect their bank via OAuth to import their actual CDB/LCI/LCA positions at their
real rates. This is a Phase 3 capability (out of scope for v1.1).

**Confidence:** HIGH that no public CDB/LCI rate API exists. MEDIUM on Open Finance future path.

### 5. Comparação Renda Fixa vs Renda Variável — Net Return Calculator

**Decision: Pure backend calculation — no new library. Uses python-bcb for reference rates.**

The comparison engine requires:
- CDI rate: `python-bcb` SGS series 12 (daily CDI) — already deployed
- SELIC rate: `python-bcb` SGS series 432 — already deployed
- IPCA accumulated: `python-bcb` SGS series 433 — already deployed
- Tabela regressiva IR for CDB (22.5% → 15% based on term): pure Python logic
- LCI/LCA isenção IR: pure Python logic (currently: isento; pending 2026 reform note)
- Dividend income from FIIs: already in portfolio engine

**IR note (2026):** A government proposal to tax LCI/LCA at 5% IR na fonte is under discussion
as of March 2026. The calculation engine should implement this as a configurable parameter, not
hardcoded, so the rate can be updated without code changes.

**No new dependencies required.**

### 6. Simulador de Alocação — Frontend

**Decision: Use existing Recharts + shadcn/ui Slider. No new chart library needed.**

The allocation simulator requires:
- Multi-asset allocation sliders (e.g., 40% ações / 30% FIIs / 30% renda fixa)
- Pie/donut chart showing current allocation
- Projected return bar/area chart

All of these are covered by:

| Need | Solution | Already Installed |
|------|----------|-------------------|
| Slider (% allocation per class) | `@radix-ui/react-slider` via shadcn/ui `Slider` component | YES — shadcn/ui is deployed |
| Donut chart (allocation breakdown) | Tremor `DonutChart` | YES — Tremor 3.x is deployed |
| Area/bar chart (projected returns) | Recharts `AreaChart` / `BarChart` | YES — Recharts 2.x is deployed |
| Multi-value sliders (range) | shadcn/ui `Slider` supports array values | YES |

**No new frontend libraries required for the simulator charts/sliders.**

### 7. Wizard "Onde Investir" — Frontend

**Decision: Custom multi-step wizard built with shadcn/ui components + React state. No wizard library.**

Community consensus (verified via search, Feb 2026): the shadcn/ui ecosystem handles multi-step
forms as custom implementations using React Hook Form + Zod + Radix UI primitives. No external
wizard library adds enough value to justify the dependency.

**Pattern:** `useReducer` or Zustand slice for wizard state + shadcn `Progress` component for
step indicator + `Card` for each step panel. React Hook Form with `getValues()` persists answers
across steps. The wizard has 3-5 steps max (perfil → valor → horizonte → sugestão IA), which
is simple enough for a 100-line custom implementation.

**React Hook Form** (7.x) and **Zod** (3.x) are already installed. No additions needed.

**Confidence:** HIGH — confirmed by shadcn/ui docs and community discussions (2026).

### 8. Wizard IA Backend — Existing AI Infrastructure

**Decision: Reuse existing AI analysis pipeline (Celery + OpenAI/OpenRouter via AWS SM).**

The "Onde Investir" wizard ends with an AI-generated allocation suggestion. This is a new
prompt/template but uses the same infrastructure as the existing AI analysis engine
(Phase 4 of v1.0): POST returns 202 + job_id, Celery processes, frontend polls.

The prompt will receive:
- User risk profile (from existing `investor_profiles` table — deployed in Phase 4)
- Available amount (R$X from wizard input)
- Investment horizon (months)
- Current macro context (SELIC, CDI, IPCA — from python-bcb)
- Screener summary (top ações/FIIs by DY from `screener_snapshot` table)

**No new AI infrastructure required.** One new Celery task + one new prompt template.

---

## New Dependencies Summary

### Backend (Python) — NEW additions to requirements.txt

```
# No new packages required for v1.1 core features.
# All data fetching uses httpx (already installed) for ANBIMA API calls.
# CVM CSV parsing uses pandas (already available in Celery worker environment).
# python-bcb (already installed) covers all rate calculations.
```

**Conditional addition:**
```
# Only if ANBIMA API requires OAuth (check developer.anbima.com.br):
# httpx[oauth2] OR authlib==1.3.x (for OAuth2 client credentials)
# Do not add until ANBIMA registration is complete and auth flow confirmed.
```

### Frontend (Node.js) — NEW additions to package.json

```
# No new packages required for v1.1.
# Slider: shadcn/ui Slider (already available via shadcn CLI, uses @radix-ui/react-slider)
# Charts: Tremor DonutChart + Recharts (both already installed)
# Wizard: React Hook Form + Zod (both already installed)
```

**Verify this shadcn component is added if not already:**
```bash
npx shadcn@latest add slider
npx shadcn@latest add progress
```

---

## New Database Tables Required

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `screener_snapshot` | Daily fundamentals cache for all B3 tickers | `ticker`, `type` (stock/fii), `pl`, `pvp`, `dy`, `volume`, `sector`, `market_cap`, `snapshot_date` |
| `fii_metadata` | FII segment/vacancy from CVM monthly reports | `ticker`, `segmento`, `tipo` (tijolo/papel/híbrido/FOF), `vacancia_pct`, `pl_total`, `report_month` |
| `tesouro_rates` | Current Tesouro Direto bond rates | `bond_type` (IPCA+/Prefixado/SELIC), `maturity_date`, `buy_rate`, `sell_rate`, `unit_price`, `fetched_at` |
| `fixed_income_catalog` | Curated CDB/LCI/LCA typical rates | `product_type`, `indexer`, `rate_min`, `rate_max`, `rate_typical`, `term_months_min`, `term_months_max`, `updated_at` |

---

## Architecture Notes for v1.1

### Screener Data Flow

```
[Celery Beat — daily, off-hours]
  → BrapiClient.fetch_all_tickers(type='stock')   # paginated list
  → BrapiClient.fetch_fundamentals(ticker)         # 1 req per ticker
  → upsert screener_snapshot

[Celery Beat — weekly]
  → Download CVM FII informe mensal CSV
  → Parse with pandas
  → upsert fii_metadata

[FastAPI GET /screener/acoes?dy_min=5&pl_max=15&setor=energia]
  → SELECT FROM screener_snapshot WHERE dy >= 5 AND pl <= 15 AND sector = 'energia'
  → Returns in <50ms — zero external API calls
```

### Tesouro Direto Data Flow

```
[Celery Beat — daily, after 18h BRT when ANBIMA publishes]
  → httpx GET https://api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/difusao-taxas
  → Parse response → upsert tesouro_rates

[FastAPI GET /renda-fixa/tesouro]
  → SELECT FROM tesouro_rates WHERE fetched_at = (SELECT MAX(fetched_at) FROM tesouro_rates)
  → Returns current rates instantly
```

### Rate Limit Budget (brapi.dev Startup Plan)

Screener rebuild daily:
- ~500 tickers (ações) × 1 req each = 500 req/day for fundamentals
- ~400 FIIs × 1 req each = 400 req/day
- Total: ~900 req/day × 30 = 27,000 req/month

The Startup plan (R$59.99/mo, already in use) has 15-min delay and no published hard limit.
With the 200ms sleep between calls already implemented in `BrapiClient`, the screener rebuild
takes ~3 min for 900 tickers — well within acceptable off-hours window.

**If rate limits are hit:** Switch to weekly screener rebuild (Sunday night) and accept stale
fundamentals data for the screener. P/L and P/VP change slowly — weekly is acceptable.

---

## Alternatives Considered

| Recommended | Alternative | Why Not |
|-------------|-------------|---------|
| brapi.dev modules for screener fundamentals (stored snapshot) | Alpha Vantage for B3 fundamentals | Alpha Vantage coverage for Brazilian tickers is poor — missing FIIs, ETFs, most small caps |
| CVM Open Data for FII metadata | Funds Explorer scraping | Scraping is ToS violation and Cloudflare-protected; CVM is official and stable |
| ANBIMA API for Tesouro Direto | Old tesourodireto.com.br JSON | Old endpoint returned 404 since Aug 2025 — confirmed dead |
| ANBIMA API | Fintz API (api.fintz.com.br) | Fintz is paid (pricing undisclosed) and adds third-party dependency; ANBIMA is official |
| Curated catalog for CDB/LCI | Open Finance per-user data | Open Finance exposes user positions, not product catalog; wrong use case |
| shadcn/ui Slider for allocation | react-range or rc-slider | @radix-ui/react-slider (used by shadcn) is already installed — zero new dep |
| Custom multi-step wizard | react-step-wizard or formik-wizard | External wizard libs add bundle weight; React Hook Form already handles multi-step well |

---

## What NOT to Add

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| `status-invest` or `investidor10` scraping | No public API; ToS violation; Cloudflare blocks; breaks without notice | brapi.dev + CVM Open Data |
| Real-time CDB rate aggregator | Does not exist as accessible API in BR; even Open Finance covers user positions not offers | Curated catalog with weekly update |
| Apache ECharts | Heavy bundle (500kb+), not already installed, no advantage over Recharts for portfolio views | Recharts (already installed, 45kb) |
| Victory Charts | Another charting library; Recharts + Tremor already cover all screener chart needs | Recharts + Tremor (already installed) |
| `react-query-wizard` or similar | Niche lib with small ecosystem; multi-step form is <100 lines with React Hook Form | React Hook Form + shadcn/ui components |
| `fundamentus` Python library (scraping) | Scrapes fundamentus.com.br which blocks aggressively; no maintenance guarantees | brapi.dev `defaultKeyStatistics` module |
| Pandas in FastAPI request handlers | Pandas DataFrames in async request context causes memory pressure under concurrent users | SQL queries from `screener_snapshot` table; Pandas only in Celery batch tasks |
| WebSockets for screener live filtering | Screener fundamentals refresh daily — no need for sub-second updates | TanStack Query polling every 5 min against cached table |

---

## Version Compatibility Notes

All new features use the existing deployed stack. No version changes required.

| Concern | Status |
|---------|--------|
| shadcn/ui `Slider` component | Available since shadcn/ui initial release; add via `npx shadcn@latest add slider` if not yet added |
| shadcn/ui `Progress` component | Same — add via CLI if not yet installed |
| Tremor `DonutChart` in Tremor 3.x | Confirmed available in Tremor 3.x (already deployed) |
| ANBIMA API auth model | Requires checking developers.anbima.com.br — may be OAuth2 client credentials or simple API key. Use `authlib` 1.3.x if OAuth2 required |

---

## Sources

- Deployed `brapi.py` adapter code (read directly) — HIGH confidence on endpoint capabilities and plan details
- [brapi.dev docs](https://brapi.dev/docs) — confirmed `/quote/list` pagination, type filter, module support
- [CVM Open Data](https://dados.cvm.gov.br/dados/FII/) — official Brazilian FII data, confirmed stable
- [ANBIMA Developers portal](https://developers.anbima.com.br/en/documentacao/precos-indices/apis-de-precos/titulos-publicos/) — Tesouro Direto rates API documentation
- [Tesouro Transparente CKAN](https://www.tesourotransparente.gov.br/ckan/dataset?tags=Tesouro+Direto) — CSV batch fallback confirmed available
- [Fintz API docs](https://docs.fintz.com.br/endpoints/tesouro/) — third-party Tesouro API, pricing TBD
- [Open Finance Brasil developer docs](https://openfinancebrasil.atlassian.net/wiki/spaces/OF/pages/75038738) — confirmed covers user positions, not product catalog
- [shadcn/ui Slider docs](https://ui.shadcn.com/docs/components/radix/slider) — confirmed range/multi-value support via @radix-ui/react-slider
- WebSearch findings on tesourodireto.com.br JSON 404 since Aug 2025 — MEDIUM confidence (community reports, not official announcement)
- BCB SGS series codes (12=CDI, 432=SELIC, 433=IPCA) — HIGH confidence via official BCB open data

---

*Stack research for: InvestIQ v1.1 — Onde Investir milestone*
*Researched: 2026-03-21*
*Extends: v1.0 STACK.md (2026-03-13)*
