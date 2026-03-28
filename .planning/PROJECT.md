# InvestIQ

## What This Is

Plataforma SaaS de gestão e análise de investimentos que usa skills de IA financeira como motor central. Começa como app pessoal do Alexandre, evolui para produto multi-tenant comercializável com assinatura. O diferencial é que as skills instaladas (DCF, valuation, análise fundamentalista, dados macro) entram como features nativas — não como add-ons.

## Core Value

O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem precisar de planilha, sem abrir mil plataformas.

## Requirements

### Validated

- ✓ Usuário pode cadastrar e visualizar todos os seus ativos (ações, FIIs, renda fixa, BDR, ETF) — v1.0
- ✓ Usuário vê a carteira consolidada com P&L, alocação e rentabilidade — v1.0
- ✓ Usuário acessa dados de mercado em tempo real (cotações, macro, fundamentals) — v1.0
- ✓ Usuário importa transações via PDF nota de corretagem e CSV — v1.0
- ✓ Usuário pode criar conta e fazer login (JWT RS256, verificação email, reset senha) — v1.0
- ✓ Plataforma suporta múltiplos usuários com dados isolados por tenant — v1.0 (app-level; RLS pendente)
- ✓ Usuário pode assinar via Stripe e recebe emails transacionais de billing — v1.0/v1.1
- ✓ Wizard "Onde Investir" com IA gera alocação recomendada em 3 etapas + CVM disclaimer — v1.1
- ✓ Screener Goldman Sachs para ações com universe automático (Celery beat, ~900 tickers) — v1.1
- ✓ TaxEngine IR regressivo com rates em DB + 3 pipelines Celery beat (screener/FII/RF) — v1.1
- ✓ Landing page com features, pricing e CTA — v1.1

### Active

- [ ] Análise fundamentalista por IA (DCF + valuation + earnings) com job assíncrono — AI-01–05
- [ ] FII screener completo (P/VP, DY, segmento, vacância) com toggle "não tenho" — SCRF-01–04
- [ ] Screener ações: filtros avançados (DY min, P/L max, setor, market cap) — SCRA-01–03
- [ ] Catálogo Renda Fixa frontend (Tesouro, CDB, LCI/LCA) com retorno líquido por prazo — RF-01–03
- [ ] Comparador RF vs RV (retorno líquido histórico por prazo) — COMP-01–02
- [ ] Simulador de alocação (valor → 3 cenários → delta carteira atual) — SIM-01–03
- [ ] Admin dashboard (assinantes, status pagamento, plano por usuário) — MON-04
- [ ] PostgreSQL RLS enforcement no DB level (não só application level) — AUTH-05

### Out of Scope

- Copy trading / seguir outros usuários — fora do foco inicial
- Mobile app nativa — web-first, PWA se necessário
- Robô de ordens / integração com corretoras para operar — regulatório complexo
- Social / comunidade — fora do escopo
- EDGAR / análise de BDRs via SEC — muito complexo para v1.x
- PIX nativo — Stripe BRL é suficiente para MVP

## Context

- Usuário (Alexandre): investidor conservador/renda, carteiras na Clear e XP, gasta R$20k/mês, 43 anos
- Google Sheet atual da carteira: https://docs.google.com/spreadsheets/d/1TfwR-aJpl55LBU0OoxJf1ui-pK1QP3PluppimHrN4qw
- Skills disponíveis como motor do produto: `dcf-model`, `valuation-toolkit`, `earnings-analysis`, `finance-research`, `alpha-vantage`, `edgar-analysis`, `fred-economic`, `charlie-cfo`, `financial-data-collector`
- Infraestrutura já pronta: VPS 185.173.110.180 + Cloudflare DNS + Traefik + Docker Compose
- Deploy: frontend porta 3100 (investiq.com.br), API porta 8100 (api.investiq.com.br)

## Constraints

- **Stack**: Python FastAPI (backend) + Next.js (frontend) + PostgreSQL + Redis — já decidido
- **Auth**: JWT — já decidido
- **Pagamentos**: Stripe v1, PIX futuro
- **Infra**: Docker Compose no VPS — sem Kubernetes, sem overhead
- **Multi-tenancy**: Projetar desde o dia 1 — não adaptar depois
- **Skills**: Integrar como features nativas, não expor as skills diretamente ao usuário final

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Multi-tenant desde o início | Evitar reescrita total quando virar SaaS | ✓ Good — app-level isolation works; RLS deferred |
| Skills financeiras como core | Diferencial competitivo — nenhum concorrente tem isso nativo | ✓ Good — wizard usa LLM provider pattern |
| Deploy direto Docker Compose | Simplicidade, infra já existente, evitar lock-in | ✓ Good — mas docker cp workaround necessário (apt-get falha no VPS) |
| `get_global_db` separado de `get_db` | Tabelas globais (screener, RF, FII) não são por-tenant | ✓ Good — evitou RLS complexidade em dados públicos |
| TaxEngine IR rates em DB | Reforma LCI/LCA 2026 pode mudar isenções | ✓ Good — ready for rate changes without deploy |
| Tesouro via ANBIMA API | JSON endpoint antigo 404 desde ago/2025 | ✓ Good — fallback para CKAN CSV implementado |
| CDB/LCI/LCA via tabela curated | Sem API pública live para taxas de mercado | ✓ Good — UI deixa claro "taxas de referência" |
| Screener universe via Celery beat | Nunca por requisição — evita rate limit | ✓ Good — ~900 tickers, 200ms sleep |

## Current State (v1.1 shipped 2026-03-28)

- **Production:** https://investiq.com.br + https://api.investiq.com.br
- **VPS:** 185.173.110.180 — 7.8GB RAM, Docker Compose, Traefik
- **Stack:** FastAPI + SQLAlchemy async + Next.js 15 + Celery + PostgreSQL + Redis + Stripe
- **Codebase:** ~24K LOC Python backend + ~12K LOC TypeScript frontend
- **Tests:** 257 passed, 2 pre-existing failures
- **DB Migrations:** 0019 (head)
- **Stripe:** LIVE — price_1TC56FCA1CPHCF6PKQ5XmUWD (R$29,90/mês)

## Next Milestone Goals (v1.2 — to be defined)

Priority items from Active requirements:
1. AI analysis engine (DCF/valuation/earnings) — AI-01–05 — biggest differentiator
2. FII screener + Ações filtros avançados — SCRF + SCRA-01–03
3. Renda fixa catalog frontend — RF-01–03
4. Simulador de alocação — SIM-01–03
5. Admin dashboard — MON-04

Start with `/gsd:new-milestone` after `/clear`.

---
*Last updated: 2026-03-28 after v1.1 milestone*
