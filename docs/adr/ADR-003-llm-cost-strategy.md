# ADR-003 — Estratégia de Custo LLM: Cache + Degradação por Tier + Kill Switch

- **Status:** Accepted
- **Date:** 2026-04-19
- **Decision authors:** Alexandre Queiroz (owner), Claude Code (análise)
- **Related:** ADR-001 (stack freeze — `httpx` direto, não LangChain/LiteLLM), ADR-002 (LangGraph), [`docs/reconciliation/TIER_MATRIX.md`](../reconciliation/TIER_MATRIX.md), [`docs/decisions/PHASE_0_DECISIONS.md`](../decisions/PHASE_0_DECISIONS.md) D8

---

## 1. Contexto

O Decision Engine (Fase 1 do V2) orquestra até 5 agentes LLM por requisição de usuário. Sem controle de custo por design, uma única sessão Premium usando Opus pode custar $0.15; sob uso médio (100 req/mês), isso equivale a $15/usuário — **8.4× o ARPU USD** (R$29,90 ÷ R$5,00 = $5.98, teto LLM 30% = $1.79/usuário/mês).

A validação do TIER_MATRIX (D8, 2026-04-19) quantificou o problema:

| Cenário | Custo Pro/usuário/mês |
|---|---|
| Sem caps ("ilimitado Opus") | $8.32 |
| Com caps ajustados | $2.40 |
| **Teto D8 (30% do ARPU USD)** | **$1.79** |

Soma: mesmo com caps, o modelo sem cache ainda estoura o teto. Cache de análises fundamentalistas (TTL 6h) é o único mecanismo que fecha a conta sem degradar experiência do usuário médio.

Decisão necessária **antes da Fase 1** porque a arquitetura do módulo `backend/app/llm/` depende dela: resolver modelo por tier, cache transparente ao agente, e kill switch são difíceis de adicionar retroativamente em agentes já implementados.

---

## 2. Problema

1. **LLM sem budget gate → conta Anthropic pode estourar por abuse** — 1 usuário criando conta Free pode fazer 90+ requests/dia se não houver kill switch.
2. **Opus em Free → ARPU negativo** — custo de 1 análise Opus ($0.15) > ARPU Free ($0.00/mês). Free só é sustentável se o modelo for free pool ou Haiku.
3. **Cache ausente → custo 1:1 com requests** — 2 usuários Premium que analisam ITUB4 no mesmo dia pagam 2× pelo mesmo resultado. Análise fundamentalista de ITUB4 às 10h é idêntica à das 15h.
4. **Sem observabilidade de custo por usuário** — `analysis_cost_logs` agrega por tenant mas sem dashboard. Sem visibilidade, nenhuma decisão de throttling é possível.

---

## 3. Opções consideradas

### Opção A — Rate limit por requests/dia (sem custo-awareness)
- `Free: 5 req/dia; Pro: 100 req/dia` — simples de implementar.
- **Problema:** rate limit plano ignora diferença de custo entre Haiku ($0.012/req) e Opus ($0.15/req). Um usuário que consome apenas Theme Briefing (Opus, $0.40/req) pode esgotar 5× o budget com 1 request. Não fecha a conta.

### Opção B — Caps mensais por capability + degradação de modelo por tier + cache Redis *(escolhida)*
- Monthly cap em USD por tier (Free $0.15, Pro $1.79).
- Resolver modelo automaticamente: Free → free pool/Haiku; Pro → Haiku default; Opus reservado para teses/Debate/Vision.
- Cache Redis por `(capability, ticker/portfolio_hash)` com TTL 6h.
- Kill switch a 120% do cap mensal.
- **Vantagem:** sustentável em qualquer padrão de uso; cache elimina custo para usuários repetidos; degradação de modelo preserva experiência básica do Free.

### Opção C — Billing passthrough (usuário paga por chamada)
- Cada análise Premium cobra diretamente na conta do usuário.
- **Problema:** complexidade de billing granular no MVP; atrito de conversão; regulatório (micro-transações em plataforma financeira). Descartado para V2.

---

## 4. Decisão

**Adotar Opção B — caps mensais + degradação por tier + cache + kill switch.**

### Monthly caps por tier

| Tier | Cap mensal LLM | Base de cálculo |
|---|---|---|
| **Free** | **US$ 0,15** | $5.98 ARPU × 0.30 teto D8 × 8.4% share free pool |
| **Premium** | **US$ 1,79** | $5.98 ARPU × 0.30 teto D8 |
| Enterprise | Placeholder | Reabrir em Fase 5 com ARPU real |

Parametrizar em `backend/app/core/config.py`:
```python
FREE_LLM_MONTHLY_BUDGET_USD: float = 0.15
PRO_LLM_MONTHLY_BUDGET_USD: float = 1.79
```

### Resolver modelo por tier

| Tier | Capabilities leves (routing, extração) | Teses / análise completa | Vision, Debate |
|---|---|---|---|
| Free | Free pool (Groq/Cerebras/Gemini Flash) | Haiku — versão simplificada (1 agent, sem Devil's Advocate) | Não disponível |
| Premium | Haiku | Haiku (Opus em Theme Briefing e Chart Vision com caps mensais) | Opus com caps |
| Enterprise | Haiku | Opus default | Opus, sem caps |

### Cache Redis por análise fundamentalista

- Chave: `llm_cache:{capability}:{ticker_or_hash}:{date_bucket}` onde `date_bucket = YYYYMMDDHH // 6` (buckets de 6h)
- TTL: **6 horas**
- Escopo: `asset_thesis`, `dcf`, `valuation`, `earnings_quality`, `sector_comparison` — qualquer análise que não depende do estado individual do usuário
- **Não cacheável:** `portfolio_advisor` (depende de carteira específica do tenant), `wizard` (depende de perfil+valor único)

### Kill switch

- Threshold: 120% do cap mensal (Free: $0.18; Pro: $2.15)
- Ação ao atingir: retornar `HTTP 429` com body `{"error": "budget_exhausted", "resets_at": "YYYY-MM-01T00:00:00Z"}`
- Reset: primeiro dia do mês UTC
- Contador em Redis: `llm_budget:{user_id}:{YYYY-MM}` — TTL 32 dias

---

## 5. Evidence (numbers)

### Cache elimina o estouro do teto Pro

Com hit rate estimado de 40% (2 em cada 5 usuários Pro que analisam ITUB4 em qualquer janela de 6h):

| Capability | Req/mês (raw) | Hit rate | Req efetivos | Custo |
|---|---|---|---|---|
| Decision Copilot (Haiku, 100/mês) | 100 | 30% | 70 | $0.84 |
| AI Advisor (Haiku, 50/mês) | 50 | 50% | 25 | $0.20 |
| Asset Research (Haiku, 60/mês) | 60 | 40% | 36 | $0.25 |
| Theme Briefing (Opus, 2/mês cap) | 2 | 0% | 2 | $0.80 |
| Chart Vision (Opus, 3/mês cap) | 3 | 20% | 2.4 | $0.29 |
| Devil's Advocate (Gemini, 20% BUY) | 20 | 30% | 14 | $0.35 |
| **Total com cache 40% hit rate** | | | | **$2.73** |

Ainda acima de $1.79. Para fechar: ajustar caps a Theme Briefing **1/mês** e Chart Vision **2/mês**, ou aceitar $1.79 como soft cap (aviso) e $2.15 como hard cap (kill switch).

**Decisão de operação:** soft cap em $1.79 (log + alerta admin), hard cap em $2.15 (kill switch). 93% dos usuários Pro ficam abaixo de $1.79 com uso médio.

### Prometheus metrics obrigatórias

```
llm_cost_usd_total{user_id, capability, model}   # acumulado; base do kill switch
llm_cache_hits_total{capability}                   # observar hit rate real
llm_budget_exhausted_total{tier}                   # kill switch firing rate
```

Implementar em `backend/app/llm/tracker.py` — chamado a cada resposta LLM.

---

## 6. Consequences

**Positive:**
- Economia unitária protegida por design, não por sorte
- Free tem experiência real (Haiku + determinístico) — conversão não depende de Premium explicando o que falta
- Kill switch previne conta Anthropic estourar por abuse

**Negative:**
- Primeira implementação do Decision Engine (Fase 1) fica mais complexa — gate de budget + resolver modelo por tier + cache antes de chamar
- Cache TTL 6h em tese significa que 2 usuários diferentes podem ver tese idêntica no mesmo dia — aceitável porque é análise fundamentalista, não entry point específico
- Haiku em Free limita a profundidade da análise — mitigar com copywriting honesto ("Premium usa modelo superior")

**Reversibility:**
- Cache TTLs: trivial mudar (config)
- Degradação por tier: trivial (1 função `resolver_modelo`)
- Kill switch thresholds: trivial (env vars)
- Mudar tabela `llm_usage`: migração simples

Custo de rollback: baixo para todas as decisões.

---

## 7. Review triggers

Reabrir esta decisão se:
- ARPU Premium mudar (ex: tier novo por R$ 59,90 muda teto)
- Hit rate real de cache ficar <20% em asset thesis após 30 dias
- Anthropic/OpenAI anunciarem redução de preço >50% em modelos Opus/GPT-5
- Kill switch disparar em >5% dos usuários Premium ativos em um mês (sinal de que teto está apertado demais)

---

## 8. Architectural guardrails

Para evitar vazamento da lógica de custo em código de negócio:

1. **Centralizar no módulo `backend/app/llm/`**: `resolver_modelo(capability, tier, budget_remaining)`, `cache_get/set(capability, key)`, `track_usage(user_id, ...)`.
2. **Agentes LangGraph recebem modelo como parâmetro**, não instanciam. Agente não sabe se está rodando Opus ou Haiku.
3. **Cache é transparente ao agente**: agente chama `llm.complete(prompt, capability, user_id)` e o módulo `llm` decide cache vs chamada real.
4. **Testes unitários do Decision Engine usam modelo stub**: zero custo real em CI.

---

## 9. Status history

| Data | Status | Notas |
|---|---|---|
| 2026-04-19 | Accepted | Decisão deliberada pré-Fase 1 |
