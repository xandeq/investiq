# InvestIQ

## What This Is

Plataforma SaaS de gestão e análise de investimentos que usa skills de IA financeira como motor central. Começa como app pessoal do Alexandre, evolui para produto multi-tenant comercializável com assinatura. O diferencial é que as skills instaladas (DCF, valuation, análise fundamentalista, dados macro) entram como features nativas — não como add-ons.

## Core Value

O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem precisar de planilha, sem abrir mil plataformas.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Usuário pode cadastrar e visualizar todos os seus ativos (ações, FIIs, renda fixa, cripto)
- [ ] Usuário vê a carteira consolidada com P&L, alocação e rentabilidade
- [ ] Usuário recebe análise fundamentalista dos ativos (earnings, DCF, valuation)
- [ ] Usuário acessa dados de mercado em tempo real (cotações, indicadores)
- [ ] Usuário importa transações (B3, Clear, XP)
- [ ] Usuário pode criar conta e fazer login (autenticação segura)
- [ ] Plataforma suporta múltiplos usuários com dados 100% isolados (multi-tenant)
- [ ] Usuário pode assinar um plano e pagar (Stripe + PIX futuro)
- [ ] Admin consegue gerenciar usuários e planos

### Out of Scope

- Copy trading / seguir outros usuários — fora do foco inicial
- Mobile app nativa — web-first, PWA se necessário
- Robô de ordens / integração com corretoras para operar — regulatório complexo
- Social / comunidade — fora do escopo v1

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
| Multi-tenant desde o início | Evitar reescrita total quando virar SaaS | — Pending |
| Skills financeiras como core | Diferencial competitivo — nenhum concorrente tem isso nativo | — Pending |
| Deploy direto Docker Compose | Simplicidade, infra já existente, evitar lock-in | — Pending |
| Supabase no mesmo VPS | PostgreSQL + auth + storage já rodando | — Pending |

---
*Last updated: 2026-03-13 after initialization*

## Current Milestone: v1.1 — Onde Investir

**Goal:** Transformar o InvestIQ em um advisor de alocação completo — o usuário informa quanto tem para investir e a plataforma orienta onde e como alocar entre ações, FIIs, renda fixa e fundos.

**Target features:**
- Screener de ações com filtro de dividend yield mínimo
- Screener de FIIs (P/VP, DY, liquidez, segmento)
- Histórico de preços com gráfico (ações e FIIs)
- Catálogo de renda fixa (Tesouro Direto, CDB, LCI, LCA) com taxas atuais
- Comparação renda fixa vs ações/FIIs (retorno líquido ajustado)
- Simulador de alocação (R$X dividido entre ativos, projeção de retorno/risco)
- Análise de portfólio com sugestão de realocação baseada no perfil
- Fluxo "Onde Investir" — wizard guiado por IA do valor → alocação ideal
