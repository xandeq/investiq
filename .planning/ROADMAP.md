# InvestIQ v1.2 — AI Analysis Engine Roadmap

**Milestone:** v1.2 AI Analysis Engine
**Phases:** 12–16 (continues from v1.1 Phase 11)
**Granularity:** Coarse (5 phases — critical path only)
**Status:** Draft (awaiting user approval)
**Created:** 2026-03-31

---

## Phases

- [x] **Phase 12: Foundation (Legal + Cost Control + Async Architecture)** — Establish legal compliance, data versioning, quota system, async job infrastructure
 (completed 2026-03-31)
- [x] **Phase 13: Core Analysis Engine** — DCF, earnings, dividends, sector comparison (MVP scope)
 (completed 2026-04-03)
- [ ] **Phase 14: Differentiators & Sophistication** — LLM narratives, sensitivity analysis, user customization
- [ ] **Phase 15: Data Quality & Advanced Features** — Cache invalidation, peer data audit, performance hardening
- [ ] **Phase 16: Frontend Integration & Launch** — Detail page, progress UI, WebSocket, testing, production launch

---

## Phase Details

### Phase 12: Foundation (Legal + Cost Control + Async Architecture)

**Goal:** Establish legal compliance, data versioning strategy, async analysis infrastructure, and cost control framework before shipping any analysis features.

**Depends on:** v1.1 complete (Phases 1–11)

**Requirements Mapped:** AI-08, AI-09, AI-11, AI-12

**Success Criteria:**

1. Legal audit completed: CVM registration threshold documented, disclaimer architecture approved by counsel, on-feature disclaimer component built and tested in staging
2. Cost control framework deployed: Per-user quota tracking in database, rate limiting middleware enforced (rejects requests when quota exceeded), cost tracking per analysis type in logs
3. Data versioning system established: All analyses tagged with `data_version_id` and `data_timestamp`, test shows timestamp visible in API responses
4. Async analysis queue working end-to-end: User submits analysis request, receives job ID immediately, background Celery worker processes, test confirms <30s processing for simple DCF on 5 sample tickers
5. Fallback LLM provider chain tested: OpenRouter → Groq fallback works in staging, load test with 50 concurrent requests completes without errors

**Plans:** 3/3 plans complete

Plans:
- [x] 12-01-PLAN.md — Analysis module foundation (models, schemas, migration, test scaffold)
- [x] 12-02-PLAN.md — Quota enforcement, rate limiting, cost tracking, CVM disclaimer
- [x] 12-03-PLAN.md — Async Celery task, LLM provider fallback, cache invalidation

---

### Phase 13: Core Analysis Engine

**Goal:** Deliver MVP analysis features (DCF, earnings, dividends, sector comparison) with async job pattern reused from wizard.

**Depends on:** Phase 12 (foundation, quotas, async infrastructure)

**Requirements Mapped:** AI-01, AI-02, AI-03, AI-04

**Success Criteria:**

1. DCF analysis calculates correctly: Test suite confirms valuation matches manual Bloomberg/FactSet spot checks (±5%) for 10 sample tickers; output includes fair value range and key assumptions
2. Earnings module integrates fundamentals: Historical EPS (5 years) + earnings quality metrics (accrual ratio, FCF conversion) fetch from database, test confirms BRAPI/B3 data matches expected values
3. Dividend analysis complete: Yield, payout ratio, coverage ratio calculated; sustainability flag triggers if payout >80%, test flags high-risk dividend cutters
4. Sector comparison returns data: API queries BRAPI peer fundamentals, aggregates metrics (P/E, P/B, dividend yield) for 5–10 peers, test confirms response <10s for avg-case ticker
5. All analyses include data source attribution: API responses show "Data: BRAPI EOD [date]", "Fundamentals: CVM/B3 [source]" for transparency

**Plans:** 2/2 plans complete

Plans:
- [x] 12-01-PLAN.md — Analysis module foundation (models, schemas, migration, test scaffold)
- [x] 12-02-PLAN.md — Quota enforcement, rate limiting, cost tracking, CVM disclaimer
- [ ] 12-03-PLAN.md — Async Celery task, LLM provider fallback, cache invalidation

---

### Phase 14: Differentiators & Sophistication

**Goal:** Add LLM-generated narratives, sensitivity analysis, and user customization to differentiate from generic financial tools.

**Depends on:** Phase 13 (core analysis working)

**Requirements Mapped:** AI-05, AI-06, AI-07

**Success Criteria:**

1. LLM narrative generated and validated: Claude Haiku produces 100–200 word plain-English summary of analysis (key insights, caveats, limitations), test confirms no hallucinated ticker names or false metrics in 50 generated narratives
2. Sensitivity analysis scenarios calculated: Bear (±10% on key inputs), Base, Bull scenarios generated for 10 sample tickers, test confirms bull scenario > base > bear on fair value
3. User assumption customization working: Frontend form accepts growth rate (0–20%), discount rate (0–30%), terminal growth (<inflation), Celery job recalculates DCF with custom inputs, test confirms valuation changes proportionally to input changes
4. Analysis quality monitoring in place: Per-LLM-call token count and cost tracked, test shows cost per analysis <$0.05 (Haiku tier), cost dashboard accessible to ops team
5. Fallback graceful degradation: If LLM quota exhausted, analysis returns cached result with "outdated" badge and "Contact support" message (feature doesn't break)

**Plans:** 2 plans

Plans:
- [ ] 14-01-PLAN.md — Sector peer comparison (AI-04: calculation, task, endpoint, tests)
- [ ] 14-02-PLAN.md — Quality validation + cost monitoring (AI-05, AI-06, AI-07 hardening + admin costs endpoint)

---

### Phase 15: Data Quality & Advanced Features

**Goal:** Ensure analysis data robustness via cache invalidation, peer data auditing, and performance optimization before customer launch.

**Depends on:** Phase 14 (all analysis features built)

**Requirements Mapped:** AI-10, AI-13

**Success Criteria:**

1. Cache invalidation system working: Event listener catches BRAPI earnings releases, triggers immediate invalidation of cached analyses for that ticker, test confirms stale cache cleared within 5min of earnings announcement
2. Peer data audit completed: Manual verification of 50 sample tickers shows peer group matches Bloomberg classification, data completeness flags (green/yellow/red) implemented in API, test shows completeness >80% for large-cap stocks
3. Performance under load validated: Load test with 500 concurrent analysis requests (distributed over 10s) completes with p95 latency <30s, no timeout failures, background workers scale horizontally
4. Analysis history + audit trail: Old analyses retrievable by user, changes between analyses (old valuation vs new) computed and surfaced in UI ("Fair value changed +15% due to EPS revision"), test confirms audit trail entries created on every analysis
5. Manual "Refresh analysis" button working: User clicks refresh, new job queued immediately, old result replaced on completion, test confirms refresh costs user 1 quota point, old analysis archived with timestamp

**Plans:** 3 plans

Plans:
- [ ] 12-01-PLAN.md — Analysis module foundation (models, schemas, migration, test scaffold)
- [ ] 12-02-PLAN.md — Quota enforcement, rate limiting, cost tracking, CVM disclaimer
- [ ] 12-03-PLAN.md — Async Celery task, LLM provider fallback, cache invalidation

---

### Phase 16: Frontend Integration & Launch

**Goal:** Integrate all analysis features into stock detail page UI, validate end-to-end user experience, test quality/performance, and ship to production.

**Depends on:** Phase 15 (data robustness verified)

**Requirements Mapped:** AI-14, AI-15

**Success Criteria:**

1. Stock detail page displays all analysis: DCF section (fair value ± range), earnings panel (historical + forecast), dividend widget (yield + risk flag), sector comparison (stock vs peers), LLM narrative (insights + caveats), test confirms all sections render without JS errors on 20 sample stocks
2. Async loading UX working: User clicks stock → detail page loads instantly, analysis sections show "Calculating..." spinner, WebSocket notifies frontend on job completion, sections populate in real-time without page refresh, test confirms UX smooth for p95 job latency <30s
3. Disclaimer visible and clear: CVM-compliant disclaimer appears above analysis section, educates user ("Educational analysis, not investment advice"), shows data freshness ("As of [date]"), test confirms users cannot scroll past disclaimer on mobile
4. Performance meets SLA: Production load test shows p50 analysis latency 15s, p95 <30s, p99 <60s, no timeout failures at 100 concurrent users, cache hit rate >75% (repeat analyses), database query times <500ms
5. Testing comprehensive: Full test suite passes (257 existing + new analysis tests), integration tests verify end-to-end flow (user request → Celery job → API response → frontend display), security tests confirm tenant isolation (user can't see other users' analyses)

**Plans:** 3 plans

Plans:
- [ ] 12-01-PLAN.md — Analysis module foundation (models, schemas, migration, test scaffold)
- [ ] 12-02-PLAN.md — Quota enforcement, rate limiting, cost tracking, CVM disclaimer
- [ ] 12-03-PLAN.md — Async Celery task, LLM provider fallback, cache invalidation

---

## Progress Tracking

| Phase | Status | Plans Complete | Completed |
|-------|--------|----------------|-----------|
| 12 - Foundation | Planning complete | Complete    | 2026-03-31 |
| 13 - Core Analysis Engine | 2/2 | Complete   | 2026-04-03 |
| 14 - Differentiators | Planning complete | 0/2 | - |
| 15 - Data Quality | Not started | 0/3 | - |
| 16 - Frontend Launch | Not started | 0/3 | - |

**Totals:** 5 phases | 0/15 plans complete | 0/15 requirements mapped

---

## Requirements Coverage

### v1.2 Requirements to Phases Mapping

| Requirement | Phase | Category | Status |
|-------------|-------|----------|--------|
| AI-01 DCF valuation | 13 | Core Analysis | Pending |
| AI-02 Earnings analysis | 13 | Core Analysis | Pending |
| AI-03 Dividend sustainability | 13 | Core Analysis | Pending |
| AI-04 Sector comparison | 13 | Core Analysis | Pending |
| AI-05 LLM narrative | 14 | Differentiators | Pending |
| AI-06 Sensitivity analysis | 14 | Differentiators | Pending |
| AI-07 Custom assumptions | 14 | Differentiators | Pending |
| AI-08 Data versioning + timestamps | 12 | Data Quality/Legal | Pending |
| AI-09 CVM disclaimers | 12 | Data Quality/Legal | Pending |
| AI-10 Peer data completeness | 15 | Data Quality/Legal | Pending |
| AI-11 Rate limiting + quotas | 12 | Operations | Pending |
| AI-12 Async Celery jobs | 12 | Operations | Pending |
| AI-13 Cache invalidation | 15 | Operations | Pending |
| AI-14 Detail page display | 16 | UX | Pending |
| AI-15 30–60s load time SLA | 16 | UX | Pending |

**Coverage Summary:**
- Total v1.2 requirements: 15
- Mapped to phases: 15
- Unmapped: 0
- **Coverage: 100% ✓**

---

## Key Design Decisions

### Phase 1 (Foundation) Rationale

Research identified three critical pitfalls that must be prevented upfront, not patched later:

1. **Legal liability** — Analysis positioned without CVM audit = liability exposure. Phase 12 includes legal review, disclaimer architecture, educational positioning.

2. **Cost explosion** — Uncontrolled LLM requests scale from $2.5K/month (10 users) to $150K+/month (5K users) without rate limiting. Phase 12 implements hard quotas, cost tracking, fallback providers before any analysis ships.

3. **Data staleness** — Screener shows live quote, analysis uses yesterday's fundamentals = user loses trust. Phase 12 establishes `data_version_id` + `data_timestamp` on every analysis, visible in UI.

Phase 12 also designs async architecture (reuse wizard's Celery pattern) and cache invalidation triggers (earnings, manual refresh). These are foundational and cannot be added later without breaking existing analyses.

### Reuse of v1.1 Patterns

- **Async job pattern:** Wizard (Phase 7–8) uses Celery jobs + job ID return + polling. Analysis reuses exact pattern (no reinvention).
- **Rate limiting pattern:** Screener (Phase 6) has basic rate limiting. Analysis extends to per-user quotas by plan tier.
- **LLM provider pattern:** Wizard uses OpenRouter + fallback. Analysis adds cost tracking per provider.
- **Multi-tenancy:** All analyses scoped to `tenant_id` like portfolio positions.

### Why These 5 Phases (Coarse Granularity)

Coarse granularity target is 3–5 phases. At 15 requirements, 5 phases = 3 req/phase on average:

- **Phase 12:** Foundation (4 operational/legal requirements) — cannot parallelize; blocks all downstream work
- **Phase 13:** Core features (4 analysis types) — can parallelize internally
- **Phase 14:** Differentiation (3 features) — depends on Phase 13 analysis working
- **Phase 15:** Quality (2 requirements) — polish phase, data audit
- **Phase 16:** Launch (2 UI/performance requirements) — integration + production readiness

Refusing to combine phases further: Phase 12 (legal + architecture) is distinct from Phase 13 (features); Phase 14 (LLM narratives) depends on Phase 13 working; Phase 15 (robustness) must finish before shipping.

---

## Research Flags Integration

| Flag | Addressed In Phase | Action |
|------|-------------------|--------|
| CVM registration threshold | 12 | Legal counsel consultation during disclaimer architecture |
| OpenRouter fallback reliability | 12 | Staging integration test before production |
| Per-analysis-type cost tracking | 12 | Cost dashboard tracks DCF vs sector vs dividend costs |
| BRAPI earnings feed reliability | 15 | Pilot invalidation with 10 tickers; verify triggers |
| B3 stock data completeness | 15 | Data audit of 200+ stocks; identify gaps before launch |
| User assumption validation ranges | 14 | Input validation: growth 0–20%, discount rate 0–30% |

---

## Success Criteria Summary

All phases implement observable user behaviors or verifiable technical outcomes:

| Phase | Observable Success | How Verified |
|-------|-------------------|-------------|
| 12 | Legal audit done, quotas enforced, job IDs returned in <1s | Checklist + integration test |
| 13 | DCF ±5% of Bloomberg, earnings data complete, dividend flags work, sector data returns <10s | Test suite + spot checks |
| 14 | LLM narratives 100–200 words with zero hallucinations, sensitivity bear<base<bull, assumptions adjust valuation proportionally | Generated narrative review + unit tests |
| 15 | Cache invalidated within 5min of earnings, peer gaps audited, p95 latency <30s, refresh button works | Event test + load test + manual verification |
| 16 | Detail page renders all sections, disclaimer visible before analysis, p50 latency 15s, 257+ tests pass, users can't see others' analyses | Regression test + security audit |

---

## Risk Mitigation Strategy

**Legal:** Phase 12 includes CVM audit checkboxing; Phase 16 includes compliance review before production toggle.

**Cost:** Phase 12 implements hard per-user quotas with fallback providers; Phase 14 monitors cost per analysis; Phase 15 validates cache efficiency (>75% hit rate = cost controlled).

**Performance:** Phase 12 designs async + queue; Phase 15 load tests at 500 concurrent; Phase 16 sets SLA and monitors in production.

**Data quality:** Phase 13 documents data sources; Phase 15 audits completeness; Phase 16 tests end-to-end with real stock data.

---

## Next Steps

1. User approval of phase structure and success criteria (this draft)
2. Create 5 detailed plans (via `/gsd:plan-phase 12`, etc.)
3. Execute phases in order (Phase 12 blocks all others)

---

*Roadmap created: 2026-03-31*
*Milestone: InvestIQ v1.2 — AI Analysis Engine*
*Status: Awaiting user approval*
