# Requirements: InvestIQ

**Defined:** 2026-03-13
**Core Value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada — sem planilha, sem abrir mil plataformas.

---

## Princípios de Design (guiam todas as decisões)

1. **SaaS-first desde o dia 1** — Cada decisão técnica deve suportar múltiplos clientes pagantes, não apenas uso pessoal
2. **Skills como motor, não assistente** — DCF, valuation, earnings, macro: features nativas do produto, não add-ons laterais
3. **Multi-tenant não é fase 2** — RLS, isolamento de dados e schema são fundação, não migração futura
4. **IA como diferencial visível** — A análise de IA deve aparecer no centro das views, não escondida em menu
5. **Foco em valor, não complexidade** — v1 = carteira + análise + experiência simples. Cortar tudo que não serve isso
6. **Arquitetura extensível** — Módulos futuros (planejamento, metas, simuladores, relatórios premium) devem encaixar sem reescrita
7. **Freemium by design** — Separação clara entre features gratuitas e premium desde o schema até a UI

---

## v1 Requirements

### Autenticação

- [x] **AUTH-01**: Usuário pode criar conta com email e senha
- [x] **AUTH-02**: Usuário recebe verificação de email após cadastro
- [x] **AUTH-03**: Usuário pode fazer login e manter sessão persistente no browser
- [x] **AUTH-04**: Usuário pode recuperar senha via link enviado por email
- [ ] **AUTH-05**: Sistema isola dados por tenant via PostgreSQL RLS desde o primeiro endpoint

### Carteira — Ativos

- [x] **PORT-01**: Usuário pode cadastrar transações de ações B3 (compra/venda com data, quantidade, preço)
- [x] **PORT-02**: Usuário pode cadastrar transações de FIIs (com suporte a dividendos mensais isentos)
- [x] **PORT-03**: Usuário pode cadastrar ativos de renda fixa manualmente (CDB, LCI, LCA, Tesouro Direto — com vencimento e taxa)
- [x] **PORT-04**: Usuário pode cadastrar BDRs e ETFs internacionais disponíveis na B3
- [x] **PORT-05**: Sistema calcula preço médio ajustado por ativo (incluindo eventos corporativos)
- [x] **PORT-06**: Sistema registra e aplica eventos corporativos (desdobramentos, grupamentos) para não distorcer P&L

### Carteira — Visualização

- [x] **VIEW-01**: Usuário vê carteira consolidada com todos os ativos, valor atual e alocação percentual por categoria
- [x] **VIEW-02**: Usuário vê P&L por ativo (ganho/perda realizado e não realizado)
- [x] **VIEW-03**: Usuário vê rentabilidade da carteira comparada com CDI e IBOVESPA
- [x] **VIEW-04**: Usuário vê histórico de dividendos/proventos recebidos por ativo e por período

### Dados de Mercado

- [x] **DATA-01**: Sistema atualiza cotações automaticamente (B3, delay 15min via brapi.dev) com cache Redis
- [x] **DATA-02**: Usuário vê indicadores macroeconômicos em tempo real (SELIC, CDI, IPCA, câmbio via python-bcb)
- [x] **DATA-03**: Usuário vê dados fundamentalistas por ativo (P/L, P/VP, DY, EV/EBITDA)
- [x] **DATA-04**: Usuário vê gráfico de preço histórico do ativo (TradingView Lightweight Charts)

### Análise por IA

- [ ] **AI-01**: Usuário solicita análise fundamentalista por IA de qualquer ativo (DCF + valuation + earnings em linguagem natural) — resultado assíncrono com job_id
- [ ] **AI-02**: Usuário recebe interpretação macro por IA (o que SELIC, inflação e câmbio significam para a carteira dele)
- [ ] **AI-03**: Usuário recebe avaliação da carteira por IA (diversificação, concentração de risco, sugestões de rebalanceamento)
- [ ] **AI-04**: Toda saída de IA exibe disclaimer obrigatório: "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"
- [ ] **AI-05**: Features de IA são gated por plano (premium) — usuário gratuito vê prévia + CTA de upgrade

### Import de Transações

- [x] **IMP-01**: Usuário pode fazer upload de nota de corretagem em PDF (XP e Clear) — parser assíncrono com revisão antes de confirmar
- [x] **IMP-02**: Usuário pode importar transações via CSV com template padrão fornecido pelo sistema
- [x] **IMP-03**: Sistema armazena arquivo original do import (PDF/CSV) para auditoria e reprocessamento

### Monetização

- [ ] **MON-01**: Sistema tem dois planos: Gratuito (carteira básica, sem IA) e Premium (análise IA completa)
- [ ] **MON-02**: Usuário premium pode assinar via Stripe (cartão de crédito, BRL)
- [ ] **MON-03**: Usuário gratuito vê features premium bloqueadas com preview + CTA de upgrade contextual
- [ ] **MON-04**: Admin pode visualizar assinantes, status de pagamento e plano por usuário

### Extensibilidade (requisitos não-funcionais)

- [x] **EXT-01**: Arquitetura de módulos permite adicionar novos domínios (planejamento, metas, simuladores) sem alterar core
- [x] **EXT-02**: Sistema de planos é configurável — novos tiers e gates podem ser adicionados sem deploy especial
- [x] **EXT-03**: Skills financeiras são encapsuladas em adapters independentes — substituível ou expansível sem impacto no core

---

## v2 Requirements

### IR / Declaração de Imposto de Renda
- **IR-01**: Cálculo de IR sobre lucros em ações (alíquota 15% acima de R$20k/mês, day trade 20%)
- **IR-02**: Controle de prejuízos acumulados para compensação futura
- **IR-03**: Geração de relatório mensal para preenchimento do DARF
- **IR-04**: Relatório anual para declaração de IR (bens e direitos, rendimentos)

### PIX Recorrente
- **PAY-01**: Assinatura via PIX recorrente (Asaas ou Pagar.me) — alternativa ao Stripe para mercado BR

### Planejamento Financeiro
- **PLAN-01**: Usuário define metas financeiras (aposentadoria, imóvel, reserva)
- **PLAN-02**: Simulador de projeção de patrimônio com aportes regulares
- **PLAN-03**: IA avalia se carteira atual está alinhada com as metas

### Notificações
- **NOTF-01**: Alertas de preço para ativos monitorados
- **NOTF-02**: Notificação de dividendos creditados
- **NOTF-03**: Resumo semanal de performance da carteira por email

---

## Out of Scope

| Feature | Razão |
|---------|-------|
| Execução de ordens / integração para operar | Regulatório CVM — classificaria como corretora |
| App mobile nativo (iOS/Android) | Web-first v1, PWA se necessário |
| Copy trading / social | Fora do foco, CVM fiduciário |
| Real-time de bolsa (sem delay) | Licenciamento B3 = R$5k-50k/mês |
| Open Finance / CEI automático | API instável, escopo demais para v1 |
| OAuth social (Google/GitHub login) | Email/senha suficiente para v1 |
| Chat financeiro livre (estilo ChatGPT) | Features de análise estruturada > chat livre |

---

---

## v1.1 Requirements — Onde Investir

### Screener de Ações (SCRA)

- [ ] **SCRA-01**: Usuário pode filtrar ações por DY mínimo, P/L máximo, P/VP máximo, EV/EBITDA máximo, setor, liquidez diária mínima e market cap
- [ ] **SCRA-02**: Usuário vê tabela de resultados paginada com ticker, nome, preço, variação, DY, P/L, P/VP e sparkline de preço dos últimos 12 meses
- [ ] **SCRA-03**: Usuário pode ativar toggle "ativos que não tenho" para ver apenas tickers ausentes da sua carteira atual
- [x] **SCRA-04**: Sistema atualiza snapshot do universo de ações diariamente via Celery (nunca por requisição de usuário)

### Screener de FIIs (SCRF)

- [ ] **SCRF-01**: Usuário pode filtrar FIIs por P/VP máximo, DY mínimo, segmento (Tijolo/Papel/Híbrido/FoF/Agro), liquidez diária e número de cotistas
- [ ] **SCRF-02**: Usuário pode filtrar FIIs por vacância financeira máxima (dados CVM, atualizado semanalmente)
- [ ] **SCRF-03**: Usuário pode ativar toggle "FIIs que não tenho" para ver apenas tickers ausentes da sua carteira
- [ ] **SCRF-04**: Coluna de segmento é sempre exibida nos resultados e benchmark de P/VP é contextualizado por segmento

### Catálogo de Renda Fixa (RF)

- [ ] **RF-01**: Usuário vê catálogo de Tesouro Direto com taxas atuais, preço unitário e vencimento (SELIC, IPCA+, IPCA+ Juros Semestrais, Prefixado)
- [ ] **RF-02**: Usuário vê faixas de referência de mercado para CDB/LCI/LCA (taxas indicativas baseadas em CDI/IPCA — não oferta ao vivo)
- [ ] **RF-03**: Usuário vê retorno líquido IR calculado por prazo (6m, 1a, 2a, 5a) com IR regressivo (22.5%→15%) e isenções (LCI/LCA PF = 0%) aplicados

### Comparador RF vs RV (COMP)

- [ ] **COMP-01**: Usuário pode comparar retorno líquido IR de CDB/LCI/Tesouro vs IBOVESPA histórico por prazo de 6m, 1a, 2a e 5a
- [ ] **COMP-02**: Usuário vê integração com sua carteira no comparador: "sua carteira rendeu X% a.a. — equivalente a CDB de Y%"

### Simulador de Alocação (SIM)

- [ ] **SIM-01**: Usuário informa valor disponível, prazo e perfil (conservador/moderado/arrojado) e recebe mix percentual por classe de ativo (ações/FIIs/renda fixa/caixa)
- [ ] **SIM-02**: Simulador exibe 3 cenários (pessimista/base/otimista) com projeção de retorno e IR ajustado por classe e prazo
- [ ] **SIM-03**: Simulador considera carteira atual e exibe delta entre alocação atual e alocação ideal sugerida

### Wizard "Onde Investir" (WIZ)

- [ ] **WIZ-01**: Usuário percorre wizard multi-step informando valor disponível, prazo e perfil de risco
- [x] **WIZ-02**: IA gera alocação recomendada em percentuais por classe apenas — nunca tickers específicos
- [x] **WIZ-03**: Wizard lê carteira atual do usuário e inclui contexto de alocação existente na sugestão da IA
- [x] **WIZ-04**: Wizard inclui dados macroeconômicos atuais (SELIC, IPCA, tendência de juros) no contexto enviado à IA
- [x] **WIZ-05**: Disclaimer CVM é exibido obrigatoriamente antes dos resultados: "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"

---

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 — Foundation | Pending |
| AUTH-02 | Phase 1 — Foundation | Pending |
| AUTH-03 | Phase 1 — Foundation | Pending |
| AUTH-04 | Phase 1 — Foundation | Pending |
| AUTH-05 | Phase 1 — Foundation | Pending |
| EXT-01 | Phase 1 — Foundation | Done — 01-01 (module folder isolation verified) |
| EXT-02 | Phase 1 — Foundation | Complete |
| EXT-03 | Phase 1 — Foundation | Complete |
| PORT-01 | Phase 2 — Portfolio Engine + Market Data | Complete |
| PORT-02 | Phase 2 — Portfolio Engine + Market Data | Complete |
| PORT-03 | Phase 2 — Portfolio Engine + Market Data | Complete |
| PORT-04 | Phase 2 — Portfolio Engine + Market Data | Complete |
| PORT-05 | Phase 2 — Portfolio Engine + Market Data | Complete |
| PORT-06 | Phase 2 — Portfolio Engine + Market Data | Complete |
| DATA-01 | Phase 2 — Portfolio Engine + Market Data | Complete |
| DATA-02 | Phase 2 — Portfolio Engine + Market Data | Complete |
| DATA-03 | Phase 2 — Portfolio Engine + Market Data | Complete |
| DATA-04 | Phase 2 — Portfolio Engine + Market Data | Complete |
| VIEW-01 | Phase 3 — Dashboard + Core UX | Complete |
| VIEW-02 | Phase 3 — Dashboard + Core UX | Complete |
| VIEW-03 | Phase 3 — Dashboard + Core UX | Complete |
| VIEW-04 | Phase 3 — Dashboard + Core UX | Complete |
| AI-01 | Phase 4 — AI Analysis Engine | Pending |
| AI-02 | Phase 4 — AI Analysis Engine | Pending |
| AI-03 | Phase 4 — AI Analysis Engine | Pending |
| AI-04 | Phase 4 — AI Analysis Engine | Pending |
| AI-05 | Phase 4 — AI Analysis Engine | Pending |
| IMP-01 | Phase 5 — Import + Broker Integration | Complete |
| IMP-02 | Phase 5 — Import + Broker Integration | Complete |
| IMP-03 | Phase 5 — Import + Broker Integration | Complete |
| MON-01 | Phase 6 — Monetization | Pending |
| MON-02 | Phase 6 — Monetization | Pending |
| MON-03 | Phase 6 — Monetization | Pending |
| MON-04 | Phase 6 — Monetization | Pending |
| SCRA-01 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| SCRA-02 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| SCRA-03 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| SCRA-04 | Phase 7 — Foundation + Data Pipelines | Complete |
| SCRF-01 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| SCRF-02 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| SCRF-03 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| SCRF-04 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| RF-01 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| RF-02 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| RF-03 | Phase 8 — Screener + Renda Fixa Catalog | Pending |
| COMP-01 | Phase 9 — Comparador RF vs RV | Pending |
| COMP-02 | Phase 9 — Comparador RF vs RV | Pending |
| SIM-01 | Phase 10 — Simulador de Alocacao | Pending |
| SIM-02 | Phase 10 — Simulador de Alocacao | Pending |
| SIM-03 | Phase 10 — Simulador de Alocacao | Pending |
| WIZ-01 | Phase 11 — Wizard Onde Investir | Pending |
| WIZ-02 | Phase 11 — Wizard Onde Investir | Complete |
| WIZ-03 | Phase 11 — Wizard Onde Investir | Complete |
| WIZ-04 | Phase 11 — Wizard Onde Investir | Complete |
| WIZ-05 | Phase 11 — Wizard Onde Investir | Complete |

**Coverage:**
- v1.0 requirements: 34 total — mapped to phases 1-6
- v1.1 requirements: 21 total — mapped to phases 7-11
- Unmapped v1.1: 0 (all mapped)

---
*Requirements defined: 2026-03-13*
*Last updated: 2026-03-21 — v1.1 traceability complete (phases 7-11 assigned)*
