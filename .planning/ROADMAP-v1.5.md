# InvestIQ v1.5 — AI Portfolio Advisor — Roadmap

**Milestone:** v1.5 AI Portfolio Advisor
**Phases:** 23–26 (continues from v1.4 Phase 22)
**Granularity:** Coarse (4 phases — module-driven delivery)
**Status:** Active
**Created:** 2026-04-18

---

## Phases

- [ ] **Phase 23: Portfolio Health Check** — Diagnostic (ADVI-01)
- [ ] **Phase 24: AI Advisor Recommendations** — Narrative + suggestions (ADVI-02)
- [x] **Phase 25: Smart Screener** — Complementary assets filtered (ADVI-03) — 2026-04-18
- [ ] **Phase 26: Entry Signals** — Buy suggestions with fundamentals context (ADVI-04)

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

**Plans:** To be created during planning

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

**Plans:** To be created during planning

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

**Plans:** To be created during planning

---

### Phase 26: Entry Signals

**Goal:** User sees buy signals (RSI + fundamentals) for portfolio holdings on-demand, and universe recommendations from daily batch

**Depends on:** Phase 23 (context), Phase 24 (fundamentals), Phase 25 (screener)

**Requirements:** ADVI-04

**Success Criteria:**
  1. Entry Signals for owned assets load on-demand (near-realtime, <1s)
  2. Universe recommendations load from daily Celery batch job (<100ms cache hit)
  3. Each signal shows: suggested_amount_brl, target_upside_pct, timeframe_days, stop_loss_pct
  4. Signals include RSI + MA + fundamentals context (reuse from swing_trade/opportunity_detector modules)

**Plans:** To be created during planning

---

## Progress Table

| Phase | Plans | Status | Completed |
|-------|-------|--------|-----------|
| 23. Portfolio Health Check | 1/1 | Complete | 2026-04-18 |
| 24. AI Advisor Recommendations | 1/1 | Complete | 2026-04-18 |
| 25. Smart Screener | 1/1 | Complete | 2026-04-18 |
| 26. Entry Signals | 0/? | Planned | — |

---

## Requirements Coverage

| Requirement | Phase | Description | Status |
|-------------|-------|-------------|--------|
| ADVI-01 | Phase 23 | Portfolio health score, biggest risk, passive income, underperformers | ✓ Complete |
| ADVI-02 | Phase 24 | AI diagnosis + recommendations referencing user's portfolio | ✓ Complete |
| ADVI-03 | Phase 25 | Smart screener filtered to complementary assets | ✓ Complete |
| ADVI-04 | Phase 26 | Entry signals (hybrid: owned=on-demand, universe=daily) | Pending |

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
*Milestone: InvestIQ v1.5 — AI Portfolio Advisor*
*Status: Ready for planning*
