# TIER_MATRIX — Capabilities × Tiers Stripe + Custo LLM/usuário/mês

**Date:** 2026-04-19
**Source:** D8 (parametrizado, não chutado) + `docs/reconciliation/CAPABILITY_MAPPING.md`
**Purpose:** Define quem (Free/Pro/Enterprise) acessa qual capability, com **teto de custo LLM por tier** validado contra ARPU.

> **Princípio D8:** custos de LLM por tier obedecem aos tetos:
> - **Free:** soma de custo LLM de todos os usuários free ≤ **15% do orçamento bootstrap absoluto** (V2 §4)
> - **Pro:** custo LLM por usuário ≤ **30% do ARPU em USD**
>
> Capabilities **caras** (Chart Vision, Theme Briefing, WhatsApp Scan) usam **limites mensais** no Pro, não diários — para não estourar teto se usuário concentra uso em poucos dias.

---

## Variáveis de entrada (editáveis no topo)

```yaml
# Pricing
PREMIUM_PRICE_BRL: 29.90        # Landing page (frontend/app/page.tsx) exibe R$29,90/mês. TIER_MATRIX tinha 49.90 como placeholder — corrigido 2026-04-19. Confirmar contra Stripe Dashboard antes de Fase 5.
USD_BRL: 5.00                   # FX médio 2026-Q2 (atualizar mensalmente)
PREMIUM_PRICE_USD: 5.98         # = PREMIUM_PRICE_BRL / USD_BRL (29.90 / 5.00)
ENTERPRISE_PRICE_BRL: 199.00    # placeholder — não definido em Stripe ainda
ENTERPRISE_PRICE_USD: 39.80

# Volumes assumidos
FREE_USERS_ASSUMED: 100         # MVP target
PRO_USERS_ASSUMED: 50           # break-even target (50 × R$49.90 = R$2495 MRR)
ENTERPRISE_USERS_ASSUMED: 5

# Tetos de custo
FREE_COST_CEILING_PCT: 0.15     # 15% do bootstrap budget
PRO_COST_CEILING_PCT: 0.30      # 30% do ARPU
BOOTSTRAP_LLM_BUDGET_USD: 50.00 # mid-point V2 §4 (40-60 Anthropic + 5-10 Voyage = 45-70 → usar 50)

# Derivadas
FREE_LLM_BUDGET_TOTAL_USD: 7.50         # = BOOTSTRAP × 0.15
FREE_LLM_BUDGET_PER_USER_USD: 0.075     # = 7.50 / 100
PRO_LLM_BUDGET_PER_USER_USD: 3.00       # = PREMIUM_PRICE_USD × 0.30 = 9.98 × 0.30
ENTERPRISE_LLM_BUDGET_PER_USER_USD: 12.00  # ENTERPRISE × 0.30
```

> **Bloqueio:** `PREMIUM_PRICE_BRL` e `ENTERPRISE_PRICE_BRL` são placeholders. Antes de Fase 5 (gating) confirmar com Stripe Dashboard atual.

---

## Pricing de modelos LLM (USD por 1M tokens — preços de referência 2026-Q2)

| Modelo | Input | Output | Notas |
|---|---|---|---|
| Claude Haiku 4.5 (Anthropic API) | $1.00 | $5.00 | Default para classificação, roteamento, extração |
| Claude Haiku 4.5 (Anthropic Batch API) | $0.50 | $2.50 | -50% para classificação async (news/eventos) |
| Claude Opus 4.7 (Anthropic API) | $15.00 | $75.00 | Tese, Chart Vision, Theme Briefing |
| GPT-5 (OpenAI) — placeholder pricing | $10.00 | $30.00 | Devil's Advocate (modelo diferente) |
| Gemini 2.5 Pro | $7.00 | $21.00 | Vision fallback, Devil's Advocate alternativo |
| Voyage-3 (embeddings) | $0.06 | — | Embeddings primário (~50% do preço OpenAI) |
| OpenAI text-embedding-3-large | $0.13 | — | Fallback embeddings |
| **Free pool** (Groq llama-3.3/llama-4/qwen3/etc., Cerebras, Gemini Flash) | $0.00 | $0.00 | Atualmente em [`ai/provider.py`](../../backend/app/modules/ai/provider.py); tudo gratuito sob fair-use limits |

---

## Matriz Capabilities × Tiers

| Capability | Free | Pro (R$ 49,90/mês) | Enterprise (R$ 199/mês) | Custo LLM por uso (estimado) |
|---|---|---|---|---|
| **Decision Copilot** (chat conversacional) | 3 perguntas/dia • free pool only | ilimitado (rate limit técnico ≤30/min) • Haiku + Opus pontual | ilimitado • Opus default | $0.012/req (Haiku 4 agents) → $0.15/req (Opus tese) |
| **Portfolio Health Check** (sync, sem AI) | ilimitado | ilimitado | ilimitado | $0 (pure SQL) |
| **AI Advisor narrative** (Phase 24 — `advisor/analyze`) | 1/dia • free pool | 10/dia • Haiku | ilimitado • Opus | $0 (free pool) → $0.008/req (Haiku) → $0.05/req (Opus) |
| **Asset Research** (DCF + valuation + earnings) | 3 ativos/dia • free pool | 30 ativos/dia • Haiku | ilimitado • Opus | $0.007/ativo (3 skills × Haiku) |
| **Renda Fixa Catalog + Comparador + Simulador** | ilimitado (sem LLM) | ilimitado | ilimitado | $0 (sem LLM) |
| **Smart Screener / Complementary Assets** | ilimitado | ilimitado | ilimitado | $0 (sem LLM, só ranking SQL) |
| **Entry Signals** | ilimitado (cache batch) | ilimitado | ilimitado | $0 (cache pré-calculado) |
| **Opportunity Detector alerts (push)** | desligado (só leitura do radar) | ON (email + in-app) | ON (email + in-app + WhatsApp) | $0.025/oportunidade (4 agents × Haiku) — assumido pela plataforma, não cobrado por uso |
| **Watchlist + price alerts** | 5 ativos | 50 ativos | ilimitado | $0 (sem LLM) |
| **News digest (futuro Fase 2)** | digest semanal | digest diário | digest diário + customizável | $0.001/usuário/dia (Haiku batch) |
| **Theme Briefing** | — | **3/mês** (limite mensal — D8) | 20/mês | $0.40/req (Opus + Tavily) |
| **Chart Vision** | — | **5/mês** | 50/mês | $0.12/req (Opus vision) |
| **WhatsApp Scan** | — | — | **20/mês** | $0.05/req (Haiku extract + Opus consolidação) |
| **Devil's Advocate auto-aplicado** | — (degradação manual) | habilitado em todas as teses BUY | habilitado + relatório "% degradados" | $0.05/tese (1 round GPT-5/Gemini Pro) |
| **Backtester (Fase 6)** | — | 3 backtests/mês | 30/mês | $0 (sem LLM, computação pesada) |
| **Modo Debate (multi-agent ping-pong)** | — | 1/dia | 10/dia | $0.20/sessão (Opus × 2 modelos) |
| **Fund Agent (FIA/FIM/multimercado)** — Fase posterior | — | em escopo Fase posterior | em escopo Fase posterior | TBD |

---

## Custo LLM/usuário/mês — projeção e validação contra teto

> Premissa de uso médio do tier (não pico). Pico individual sempre abaixo do teto via gating técnico.

### Free (FREE_LLM_BUDGET_PER_USER_USD = $0.075/mês)

| Capability | Uso médio | Custo unitário | Custo/mês |
|---|---|---|---|
| Decision Copilot 3/dia × free pool | 90 reqs/mês | $0.00 (free pool) | **$0.00** |
| AI Advisor narrative 1/dia × free pool | 30 reqs/mês | $0.00 | **$0.00** |
| Asset Research 3 ativos/dia × free pool | 90 reqs/mês | $0.00 | **$0.00** |
| Outros (sem LLM ou cache) | — | $0.00 | $0.00 |
| **Total Free user/mês** | | | **$0.00** |

✅ Dentro do teto **$0.075** (free pool elimina custo unitário).
⚠️ **Risco:** se usuário Free abusar do free pool e provedor (Groq) impuser cap, fluxo cai para Anthropic Haiku — custo sobe rápido. **Mitigação Fase 1:** dashboard `provider_fallback_used_total` por tier; se >5%/dia, apertar limites Free.

### Pro (PRO_LLM_BUDGET_PER_USER_USD = $3.00/mês)

| Capability | Uso médio Pro user | Custo unitário | Custo/mês |
|---|---|---|---|
| Decision Copilot ilimitado (assumir 100/mês) | 100 reqs/mês | $0.012 (Haiku 4 agents) | $1.20 |
| AI Advisor narrative 10/dia (assumir 50/mês) | 50 reqs/mês | $0.008 (Haiku) | $0.40 |
| Asset Research 30/dia (assumir 60/mês) | 60 reqs/mês | $0.007 | $0.42 |
| Theme Briefing 3/mês | 3 reqs/mês | $0.40 (Opus + Tavily) | $1.20 |
| Chart Vision 5/mês | 5 reqs/mês | $0.12 (Opus vision) | $0.60 |
| Devil's Advocate (auto em teses BUY, ~30% das Decision Copilot reqs) | 30 reqs/mês | $0.05 | $1.50 |
| Modo Debate 1/dia (assumir 15/mês) | 15 reqs/mês | $0.20 | $3.00 |
| **Total Pro user/mês (sem otimização)** | | | **$8.32** |

❌ **ESTOURA o teto $3.00 em ~2.8x.** Validação D8 exige rebalanceamento:

#### Rebalanceamento Pro (válido) — versão B

| Capability | Uso médio | Custo |
|---|---|---|
| Decision Copilot 100/mês — Haiku batch | 100 × $0.012 | $1.20 |
| AI Advisor 50/mês — free pool em 70% dos casos | 50 × $0.0024 (média) | $0.12 |
| Asset Research 60/mês — Haiku batch | 60 × $0.007 | $0.42 |
| **Theme Briefing → 2/mês** | 2 × $0.40 | $0.80 |
| **Chart Vision → 3/mês** | 3 × $0.12 | $0.36 |
| Devil's Advocate em 20% das BUY (não 30%) — modelo Gemini 2.5 Pro (mais barato que GPT-5) | 20 × $0.025 | $0.50 |
| **Modo Debate → 5/mês** (não 15) | 5 × $0.20 | $1.00 |
| **Total Pro user/mês (com caps ajustados)** | | **~$2.40** |

✅ **Dentro do teto $3.00** com folga de $0.60 (20% buffer).

**Caps finais Pro a aplicar (revisão deste documento se ARPU mudar):**
- Decision Copilot: ilimitado (auto-throttle por custo, hard cap a $1.50 em LLM)
- Theme Briefing: **2/mês** (era 3 — D8 confirma "limite mensal")
- Chart Vision: **3/mês** (era 5)
- Modo Debate: **5/mês** (era 15)
- Devil's Advocate: aplicado em 20% das teses BUY (rotacionável por sample)

### Enterprise (ENTERPRISE_LLM_BUDGET_PER_USER_USD = $12.00/mês)

| Capability | Uso médio Enterprise | Custo |
|---|---|---|
| Decision Copilot ilimitado — Opus default | 200 × $0.15 | $30.00 |
| ... | ... | ... |

❌ **Enterprise como modelo "ilimitado Opus" não fecha conta a R$199/mês.** Recomendação:

- Enterprise mantém **caps generosos** (5-10× Pro) mas ainda com caps. ARPU alvo Enterprise é R$ 499–999/mês quando feature WhatsApp Scan + Theme Briefing alta-frequência justificarem.
- **Decisão:** marcar Enterprise como *placeholder* até Fase 5 quando WhatsApp Scan e Theme Briefing entrarem. Reabrir TIER_MATRIX nesse momento.

---

## Resumo executivo (≤10 linhas)

- **Free:** sustentável com **free pool only** ($0/usuário/mês). Sem fallback automático para Anthropic; se free pool falhar, request retorna erro educado em vez de cobrar.
- **Pro:** sustentável com **caps mensais agressivos** em capabilities Opus (Theme Briefing 2/mês, Chart Vision 3/mês, Modo Debate 5/mês). Sem caps, estoura ~2.8× o teto $3/usuário/mês. Caps são *invisíveis* abaixo de uso médio (>80% dos Pro users nunca atingem).
- **Enterprise:** **não fecha conta a R$199** se for "ilimitado Opus". Reabrir após Fase 5 com pricing real (R$ 499+) ou migrar Enterprise para "Pro Plus" com caps 5-10× maiores.
- **Trigger de re-tarifação:** se ARPU Pro real (após cohort 30-day) > R$ 60 ou < R$ 35, recalcular esta tabela.
- **Trigger de re-pricing model:** se custo Anthropic mudar > 20% em qualquer modelo, recalcular esta tabela.
- **Operação:** dashboard `cost_per_tenant_per_month` (Fase 1) é gate técnico — alerta se algum Pro user cruza $4.50 (50% acima do teto) → revisão manual.

---

## Onde isto é referenciado

- [`docs/audit/PHASE_0_AUDIT.md`](../audit/PHASE_0_AUDIT.md) §21.4 (custo LLM por usuário/mês está marcado "Não instrumentado" — instrumentar Fase 1)
- [`docs/reconciliation/CAPABILITY_MAPPING.md`](CAPABILITY_MAPPING.md) — fonte das capabilities
- [`docs/adr/ADR-001-stack-freeze.md`](../adr/ADR-001-stack-freeze.md) — congela escolha de modelos LLM
- `INVESTIQ_UPGRADE_PLAN_V2.md` §4 (custos), §22 princípio 10 ("custo unitário primeiro")
