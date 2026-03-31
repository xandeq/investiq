# Requirements: InvestIQ v1.2 — AI Analysis Engine

**Defined:** 2026-03-31
**Core Value:** O usuário vê análise fundamentalista de nível institucional (DCF, earnings, dividendos, peers) em um click — sem abrir Bloomberg, sem virar planilha

## v1.2 Requirements

### Core Analysis

- [ ] **AI-01**: User can view DCF valuation (intrinsic value calculation, sensitivity to assumptions)
- [ ] **AI-02**: User can view earnings analysis (historical + forecast, growth rates, earnings quality metrics)
- [ ] **AI-03**: User can view dividend yield + sustainability check (payout ratio, coverage, risk flag if unsustainable)
- [ ] **AI-04**: User can view sector peer comparison (stock vs 5-10 peers on valuation, growth, yield with data completeness)

### Differentiators

- [ ] **AI-05**: Analysis includes LLM narrative (plain English interpretation of numbers, key insights, caveats)
- [ ] **AI-06**: User can see sensitivity analysis (bear/base/bull scenarios, impact on intrinsic value)
- [ ] **AI-07**: User can customize DCF assumptions (growth rate, discount rate, terminal growth) and recalculate

### Data Quality & Legal Compliance

- [ ] **AI-08**: All analyses timestamped with data version (show "Analysis as of [date] using [data source v1.2]")
- [ ] **AI-09**: CVM-compliant disclaimers visible on-feature (educational, not investment advice; not personal recommendation)
- [ ] **AI-10**: Peer comparison shows data completeness (e.g., "7 of 10 peers included; 2 missing earnings, 1 recent IPO")

### Operations & Cost Control

- [ ] **AI-11**: Rate limiting + per-plan quotas enforced (Free: 0, Pro: 50/month, Enterprise: 500/month)
- [ ] **AI-12**: Analysis jobs are async (Celery pattern, no sync LLM calls in request, status polling)
- [ ] **AI-13**: Analysis cached 24h by default, auto-invalidated on earnings release or manual "Refresh"

### User Experience

- [ ] **AI-14**: Per-stock detail page displays analysis results (single unified view, not scattered)
- [ ] **AI-15**: Analysis load time target 30-60s (async job, progress indicator, WebSocket notification on complete)

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Portfolio-Level Insights

- **AI-16**: Portfolio concentration analysis (top 5 holdings risk, correlation heatmap)
- **AI-17**: Rebalance suggestions (current allocation vs strategy target, reorder recommendations)
- **AI-18**: Downside risk metrics (max drawdown, value at risk by sector)

### Advanced Features

- **AI-19**: Analysis export (PDF report with charts, assumptions, rationale)
- **AI-20**: Analysis history (compare old vs new analysis, track estimate changes)
- **AI-21**: Multi-currency support (BRL + USD + EUR valuations)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Real-time fundamental updates | Earnings released irregularly; daily batch sufficient |
| Copy trading based on analysis | Regulatory complexity; outside initial scope |
| Automated trading alerts | System designed for analysis, not execution |
| Real estate/crypto analysis | Focus on B3 stocks only; other assets add complexity |
| Backtesting historical analysis accuracy | Too early; launch first, audit results after 3 months |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| AI-01 | TBD | Pending |
| AI-02 | TBD | Pending |
| AI-03 | TBD | Pending |
| AI-04 | TBD | Pending |
| AI-05 | TBD | Pending |
| AI-06 | TBD | Pending |
| AI-07 | TBD | Pending |
| AI-08 | TBD | Pending |
| AI-09 | TBD | Pending |
| AI-10 | TBD | Pending |
| AI-11 | TBD | Pending |
| AI-12 | TBD | Pending |
| AI-13 | TBD | Pending |
| AI-14 | TBD | Pending |
| AI-15 | TBD | Pending |

**Coverage:**
- v1.2 requirements: 15 total
- Mapped to phases: 0 (awaiting roadmap)
- Unmapped: 15 ⚠️

---
*Requirements defined: 2026-03-31*
*Last updated: 2026-03-31 after scope gathering*
