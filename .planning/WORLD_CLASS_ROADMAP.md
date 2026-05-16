# InvestIQ — Roadmap para o Melhor Copiloto Financeiro do Planeta
## Análise completa: o que existe, o que melhora, o que falta

**Gerado em:** 2026-05-13  
**Fonte:** Audit multi-agente (backend + data pipeline + frontend)  
**Score atual:** 6.4/10 backend · 3.2/5 frontend · 6.4/10 dados

---

## DIAGNÓSTICO ATUAL — O que já é world-class

| Feature | Status | Diferencial |
|---------|--------|-------------|
| 10-gate signal engine | ✅ Excelente | Gates determinísticos — Goldman não faz isso por cliente de varejo |
| Kelly fracionário + guardrails | ✅ Robusto | Quarter-Kelly + 8% max position + 5 posições max |
| Renda fixa + IR ajustado | ✅ Melhor que XP/BTG/Rico | Comparação Tesouro + CDB + LCI + LCA com IR regressivo |
| Análise de ação individual (DCF + earnings + dividendos) | ✅ Nível institucional | AI-powered, multi-model fallback |
| Pipeline Celery + Redis | ✅ Sólido | 15 tasks, caching inteligente, zero downtime |
| Multi-tenant seguro | ✅ Produção | RLS app-level, JWT RS256, isolamento por tenant |
| Import PDF nota de corretagem | ✅ Diferencial real | Concorrência não tem |
| Opportunity Detector 4-agent chain | ✅ Inovador | Sequential agents espelham processo de research institucional |
| Briefing Engine 14 seções | ✅ Pronto (falta deploy) | Briefing matinal personalizad — inexistente no varejo BR |

---

## GAPS CRÍTICOS — Ordenados por impacto no usuário

### 🔴 P0 — Quebrado em produção (resolver AGORA)

| Problema | Impacto | Arquivo | Fix |
|---------|---------|---------|-----|
| Macro rates null (CDI/IPCA/SELIC = null) | Comparador + Simulador quebrados para todos os usuários | celery_app / Redis | Rodar `refresh_macro` task + deploy backend |
| CORS bloqueia `Idempotency-Key` | Hotfix de billing (migration 0029) não funciona em produção | `main.py:70` | Adicionar `"Idempotency-Key"` em `allow_headers` |
| Wave E (3 commits) pendente deploy | Briefing, sentimento, Copilot V2, outcomes — codados mas nunca executados | VPS | `bash deploy-backend.sh --migrate` |

---

### 🟠 P1 — Features superficiais que devem melhorar para world-class

#### 1. SINAIS DE INVESTIMENTO — Como ficam world-class

**Hoje:**
```
BUY signal = preço > 12% abaixo do máximo 30d AND DY > 5%
SELL signal = preço > 10% acima do preço de entrada
```

**O que falta:**
- Sem regime awareness (breakout em bull market ≠ breakout em sideways)
- DY > 5% threshold estático (ignora tendência de corte de dividendos)
- SELL ignora R/R (10% gain com stop 1% ≠ 10% gain com stop 5%)
- Pattern weights estáticos (calibração weekly, deve ser near-realtime)
- Sem contexto externo por sinal (sentimento + notícias relevantes)

**Como fica world-class:**
- Integrar regime classifier (bull/bear/sideways) com peso no gate
- DY: verificar tendência (crescendo ou caindo nos últimos 4 trimestres?)
- SELL: target_1/target_2 do schema já existem — usar!
- Copilot V2 (já codado nos commits pendentes) = contexto real por pick
- Calibração diária (não semanal) via Redis stats

**Esforço:** M · Arquivos: `swing_trade/service.py`, `signal_engine/calibration.py`

---

#### 2. DIVIDENDOS — Como ficam world-class

**Hoje:** Tabela bruta de histórico de dividendos por ação.

**O que falta:**
- Sem timeline visual (próximas datas de ex-div)
- Sem análise de sustentabilidade (payout ratio, FCF coverage)
- Sem previsão de yield (baseado em histórico + guidance)
- Sem ranking das melhores pagadoras de dividendos no portfólio
- Sem alerta "esta empresa pode cortar dividendos" (payout > 90%)

**Como fica world-class:**
```
Módulo novo: dividend_tracker/
- Calendário ex-div dos próximos 90 dias
- Sustainability score (FCF coverage + histórico consistência)
- Yield trend (último 4 trimestres)
- "Dividend cut risk" indicator
- Ranking das 10 melhores pagadoras na carteira
```

**Esforço:** M · Novo módulo backend + componente frontend

---

#### 3. PORTFOLIO HEALTH — Como fica world-class

**Hoje:** Score por concentração (setor, ativo, diversificação), passivo, underperformers.

**O que falta:**
- Zero volatilidade/beta assessment
- Sem VaR (Value at Risk)
- Sem stress test (e se SELIC +200bps? e se Ibov -20%?)
- Sem Sharpe ratio do portfólio como um todo
- Sem análise de correlação (portfolio parece diversificado mas todos caem junto)

**Como fica world-class:**
```
Módulo novo: risk_attribution/
- Portfolio VaR (95%, 10-day)
- Expected Shortfall
- Stress scenarios (SELIC shock, equity -20%, FII -10%)
- Correlação entre ativos (matrix visual)
- Sharpe ratio do portfólio vs CDI benchmark
- "Maior risco oculto" como novo card no Advisor
```

**Esforço:** H · Novo módulo + dados históricos de preços (já parcialmente em Redis)

---

#### 4. CRYPTO — Zero hoje

**Hoje:** Absolutamente nada. Asset class ignorada.

**O que o usuário precisa:**
- BTC, ETH, USDC/USDT, SOL: cotações em tempo real
- Adicionar crypto na carteira com alocação
- Alertas de preço (mesmo sistema de watchlist)
- Swing signals básicos (RSI, volume, on-chain simples)
- Dashboard consolidado incluindo crypto

**MVP (esforço S):**
```python
# 1. CoinGecko API (free, sem autenticação)
# GET https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum&vs_currencies=brl
# 2. Adicionar asset_class "crypto" ao enum do portfolio
# 3. Reutilizar watchlist + alertas para crypto
# Esforço: 2-3 dias para MVP completo
```

---

#### 5. OUTCOME TRACKING — Ativar o loop fechado

**Hoje:** Tabela signal_outcomes existe (migration 0030), router registrado, mas resultados superficiais: só winrate e avg-R.

**O que falta para world-class:**
- Profit Factor (gross profit / gross loss)
- Sharpe por padrão
- CALMAR ratio
- Análise de holding period (padrão funciona melhor em 3d ou 10d?)
- Identificar quando padrões falham (VIX alto? Pré-Fed? Earnings season?)
- Exit quality: user saiu no target ou bateu stop?

**Por que é transformador:** Sem outcome tracking, usuário não sabe se o sistema funciona. Com tracking rico, o sistema *aprende* — calibração automática (calibration.py já existe, só precisa de dados reais).

**Esforço:** M · Arquivos: `outcome_tracker/service.py` + análises + frontend dashboard

---

#### 6. NOTIFICAÇÕES — De passivo para proativo

**Hoje:** Usuário precisa entrar no app para ver qualquer sinal.

**O que falta:**
- Notification center centralizado (sinais de swing + watchlist + oportunidades)
- Daily digest email (top 3 ações recomendadas para hoje)
- Push notification via Telegram (já integrado no backend!)
- Alertas: "PETR4 atingiu seu alerta de preço R$38.00"

**MVP imediato:** O bot Telegram já está implementado! `telegram_bot/briefings.py` existe. Só falta:
1. Conectar `check_price_alerts` task → envio Telegram quando trigger
2. Briefing matinal às 8h30 (já no beat schedule) → deploy

**Esforço:** S · Conectar pipes que já existem

---

#### 7. IR HELPER — De tabela para wizard

**Hoje:** Tabela de ganhos e rendimentos. Bruto, sem guidance.

**O que falta:**
- Step-by-step wizard (5 passos)
- Export PDF formato DARF
- Cálculo de IR a pagar por mês com alert de prazo
- Tax-loss harvesting: "venda MGLU3 (em -40%) para abater ganhos de VALE3"

**Esforço:** M · Frontend + lógica de harvest

---

#### 8. FUNDOS DE INVESTIMENTO — Não existe

**Hoje:** FIIs têm screener completo. Fundos (FIAs, multimercado, PGBL/VGBL): zero.

**O que falta:**
- Importar cotas de fundo (extrato PDF ou manual)
- Mostrar no dashboard com % alocação
- Basic: rentabilidade vs CDI, taxa de adm, benchmark

**Esforço:** M · ~200 linhas backend + componente frontend

---

## ROADMAP EM WAVES (Priorizado por impacto × esforço)

### WAVE 0 — Hardening (esta semana)
*Fechar o que está quebrado antes de qualquer feature nova*

| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 0.1 | Fix CORS + deploy Wave E (migrations 0033/0034) | S | P0 blocker |
| 0.2 | Fechar 18 test failures | S | Confiança |
| 0.3 | HTTP security headers no Next.js | S | P1 security |
| 0.4 | Alertas de preço: confirmar funcionamento em produção | S | Confiança usuário |
| 0.5 | Conectar Telegram bot a price alerts | S | Quick win proatividade |
| 0.6 | Briefing matinal às 8h30 via Telegram (já codado) | S | Wow factor |

---

### WAVE 1 — Sinais de nível institucional (semanas 2-3)

| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 1.1 | Dividend Calendar + Sustainability Score | M | Investidores de renda |
| 1.2 | Swing Trade: integrar regime classifier + pattern weights | M | Qualidade sinais |
| 1.3 | Crypto MVP: BTC/ETH na carteira + watchlist + alertas | S | Novo segmento |
| 1.4 | Notification Center (Inbox centralizado no app) | M | Engajamento |
| 1.5 | Outcome Tracker analytics: Profit Factor, Sharpe, holding period | M | Loop fechado |

---

### WAVE 2 — Portfolio de nível Goldman (mês 2)

| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 2.1 | Risk Attribution: VaR, stress tests, correlação | H | Diferencial competitivo |
| 2.2 | Rebalancing Assistant (current vs target + IR impact) | M | Funcionalidade faltante crítica |
| 2.3 | IR Helper Wizard + tax-loss harvesting | M | Fidelização anual |
| 2.4 | Async Redis em advisor/service.py | S | Performance |
| 2.5 | Sentry APM (FastAPI + Celery) | S | Observabilidade |

---

### WAVE 3 — Dados de qualidade institucional (meses 2-3)

| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 3.1 | CVM Insider Trading RSS (GRATUITO) | S | Alpha real |
| 3.2 | Fundamentals históricos: P/L, P/VP, ROE 5a (Fundamentus scraper) | M | Valuation completo |
| 3.3 | Macro: PIB + desemprego via BCB API (gratuito) | S | Análise cíclica |
| 3.4 | Sentimento NLP real (Llama3 via Groq, custo ~$0) vs keyword bag | M | Sentimento confiável |
| 3.5 | Fundos de investimento básico | M | Carteira completa |

---

### WAVE 4 — O que Goldman não oferece para varejo (mês 3-4)

| # | Item | Esforço | Impacto |
|---|------|---------|---------|
| 4.1 | Backtesting engine: replay histórico de sinais | H | Confiança no sistema |
| 4.2 | Devil's advocate: contra-argumento Haiku em cada pick | S | Qualidade decisions |
| 4.3 | ETF analyzer + overlap detection | M | Diversificação real |
| 4.4 | Sector rotation analysis (macro regime classifier) | H | Timing de setores |
| 4.5 | LangGraph agent sessions (Fase 5 premium) | H | Diferencial definitivo |

---

## DADOS CRÍTICOS — O que integrar e como

| Dado | Fonte | Custo | Esforço | Impacto |
|------|-------|-------|---------|---------|
| Insider trading (CVM forms) | CVM dados.gov.br | **GRÁTIS** | S | ++++ |
| PIB + desemprego | BCB API (série 4380, 13522) | **GRÁTIS** | S | +++ |
| Fundamentals históricos 5a | Fundamentus scraper | **GRÁTIS** | M | +++++ |
| Sentimento NLP | Groq Llama3 inference | **~$0** | M | +++ |
| Crypto on-chain básico | CoinGecko API | **GRÁTIS** | S | ++ |
| Options flow | MercadoOpções API | ~R$1-2k/mês | H | ++++ |
| FactSet fundamentals | FactSet | USD 3-5k/mês | M | +++++ |
| VIX + Fed data | FRED St. Louis | **GRÁTIS** | S | +++ |

**Quick win de dados:** CVM Insider Trading + BCB macro + FRED = GRÁTIS + semana de implementação = diferencial institucional real.

---

## COMPARAÇÃO FINAL — Onde InvestIQ chega com cada Wave

| Após | vs Goldman (varejo) | vs Bloomberg | vs XP/Rico | Score |
|------|---------------------|--------------|------------|-------|
| Wave 0 | 30% | 20% | 85% | 6.5/10 |
| Wave 1 | 45% | 30% | 95% | 7.5/10 |
| Wave 2 | 65% | 45% | 110% (melhor) | 8.5/10 |
| Wave 3 | 75% | 55% | 120% | 9.0/10 |
| Wave 4 | 90% | 70% | 130% | 9.5/10 |

**Nota:** Goldman/Bloomberg têm dados proprietários (order flow, deal flow, prime brokerage) que são impossíveis de replicar para varejo. Em análise disponível para retail, InvestIQ pode superar ambos ao chegar na Wave 4 — especialmente com IA personalizada por carteira individual.

---

## QUICK WINS (1-2 dias cada, alto impacto visual)

1. **Dark mode** — 1 dia, engagement
2. **Tooltips em todas as métricas financeiras** — 1 dia, educação
3. **Skeleton loaders universais** — 1 dia, percepção de velocidade
4. **Cmd+K search global** (ticker, página) — 1-2 dias, produtividade
5. **Timestamp relativo + absoluto on hover** — 0.5 dia
6. **Crypto MVP**: BTC/ETH na carteira — 2-3 dias, novo segmento
7. **Telegram price alert connection** — 0.5 dia (infra já existe)
8. **Deploy Wave E** (briefing às 8h30 + sentimento) — 1 hora (já codado)

---

*Roadmap gerado por audit multi-agente: backend features · data pipeline · frontend UX*  
*Próximo passo: /gsd:plan-phase para Wave 0 (hardening) seguido de Wave 1 (sinais world-class)*
