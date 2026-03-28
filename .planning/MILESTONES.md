# InvestIQ — Milestones

## ✅ v1.1 — Onde Investir (2026-03-28)

**Phases:** 7, 11 | **Plans:** 4 | **Timeline:** 2026-03-21 → 2026-03-28

**Delivered:** Data infrastructure (TaxEngine + 4 global tables + 3 Celery pipelines), Screener Goldman Sachs em produção, Wizard "Onde Investir" 3-step com IA + CVM disclaimer, landing page marketing, billing emails, correpy fee fix.

**Key accomplishments:**
1. 4 global PostgreSQL tables + TaxEngine IR regressivo (22.5%→15% + isenções LCI/LCA) + 20 unit tests
2. 3 Celery beat pipelines: screener universe (~900 tickers), FII metadata, renda fixa catalog
3. Screener Goldman Sachs deployado — 10 ações por run, rate-limit 3/hora
4. Wizard backend: Celery async, LLM provider pattern, CVM disclaimer, portfolio delta
5. Wizard frontend: WizardContent.tsx 3-step (Valor → Prazo → Perfil), progress indicator, Voltar navigation
6. Landing page: features grid, pricing table, FAQ, LandingNav sticky + mobile menu
7. Billing: emails transacionais welcome/payment-received/payment-failed/cancellation via Brevo
8. Correpy: distribuição proporcional da taxa de corretagem (não mais fee duplicada por transação)

**Known Gaps:**
- SCRA-01–03 (filtros avançados screener), SCRF-01–04 (FII screener), RF-01–03 (catálogo RF frontend)
- COMP-01–02 (comparador), SIM-01–03 (simulador), AI-01–05 (análise por IA), MON-04 (admin)
- AUTH-05 (RLS enforcement no DB level)

**Archive:** `.planning/milestones/v1.1-ROADMAP.md` | `.planning/milestones/v1.1-REQUIREMENTS.md`

---

## ✅ v1.0 — MVP (2026-03-21)

**Phases:** 1, 2, 3, 4, 5, 6 | **Timeline:** 2026-03-13 → 2026-03-21

**Delivered:** Multi-tenant FastAPI + Next.js SaaS em produção. Carteira completa (ações/FIIs/RF/BDR/ETF), P&L + CMP + eventos corporativos, cotações brapi.dev + macro python-bcb + fundamentals, import notas de corretagem (correpy + CSV), Stripe subscriptions, screener Goldman Sachs inicial.

**Production URLs:** https://investiq.com.br + https://api.investiq.com.br
