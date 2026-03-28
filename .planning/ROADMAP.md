# Roadmap: InvestIQ

## Milestones

- ✅ **v1.0 MVP** — Phases 1–6 (shipped 2026-03-21) — multi-tenant SaaS em produção
- ✅ **v1.1 Onde Investir** — Phases 7, 11 (shipped 2026-03-28) — wizard IA + screener + data pipelines
- 📋 **v1.2 (a definir)** — AI engine, FII screener, simulador, RF frontend

## Phases

<details>
<summary>✅ v1.0 MVP (Phases 1–6) — SHIPPED 2026-03-21</summary>

- [x] **Phase 1: Foundation** — Multi-tenant auth, RLS, transaction schema, FastAPI (completed 2026-03-14)
- [x] **Phase 2: Portfolio Engine + Market Data** — CMP, P&L, Redis cache, Celery, brapi.dev (completed 2026-03-14)
- [x] **Phase 3: Dashboard + Core UX** — Next.js frontend, carteira consolidada, P&L, benchmark (completed)
- [x] **Phase 4: AI Analysis Engine** — DCF/valuation/earnings async pipeline, CVM disclaimer (completed)
- [x] **Phase 5: Import + Broker Integration** — PDF nota de corretagem, CSV import (completed 2026-03-15)
- [x] **Phase 6: Monetization** — Stripe subscriptions, plan gates, billing emails (completed)

</details>

<details>
<summary>✅ v1.1 Onde Investir (Phases 7, 11) — SHIPPED 2026-03-28</summary>

- [x] **Phase 7: Foundation + Data Pipelines** — 4 global tables, TaxEngine IR, 3 Celery beat pipelines (completed 2026-03-26)
- [x] **Phase 11: Wizard Onde Investir** — AI wizard async, 3-step frontend, CVM disclaimer, portfolio delta (completed 2026-03-28)

*Note: Phases 8–10 (Screener filtros, Comparador RF, Simulador) were planned but deferred to v1.2. Screener Goldman Sachs shipped as hotfix.*

See full archive: `.planning/milestones/v1.1-ROADMAP.md`

</details>

---

## 📋 v1.2 — (name TBD, start with `/gsd:new-milestone`)

Candidate features (from Active requirements — priority order):
- AI Analysis Engine (DCF + valuation + earnings per asset) — AI-01–05
- FII Screener completo (P/VP, DY, segmento, vacância) — SCRF-01–04
- Ações Screener filtros avançados (DY min, P/L max, setor, market cap) — SCRA-01–03
- Renda Fixa catalog frontend (Tesouro, CDB, LCI/LCA + retorno líquido) — RF-01–03
- Comparador RF vs RV (retorno líquido histórico por prazo) — COMP-01–02
- Simulador de Alocação (valor → 3 cenários → delta carteira) — SIM-01–03
- Admin dashboard (assinantes, plano, pagamento) — MON-04

---

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Foundation | v1.0 | 4/4 | ✅ Complete | 2026-03-14 |
| 2. Portfolio Engine + Market Data | v1.0 | 4/4 | ✅ Complete | 2026-03-14 |
| 3. Dashboard + Core UX | v1.0 | 3/3 | ✅ Complete | 2026-03-15 |
| 4. AI Analysis Engine | v1.0 | 3/3 | ✅ Complete | 2026-03-15 |
| 5. Import + Broker Integration | v1.0 | 2/2 | ✅ Complete | 2026-03-15 |
| 6. Monetization | v1.0 | 3/3 | ✅ Complete | 2026-03-21 |
| 7. Foundation + Data Pipelines | v1.1 | 2/2 | ✅ Complete | 2026-03-26 |
| 11. Wizard Onde Investir | v1.1 | 2/2 | ✅ Complete | 2026-03-28 |
| 12. (next) | v1.2 | TBD | 📋 Planned | - |
