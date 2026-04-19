# Capability Mapping — V1/V2 alvo × Implementação atual × Nome unificado

**Date:** 2026-04-19
**Owner:** Fase 0 audit (`docs/audit/PHASE_0_AUDIT.md`)
**Purpose:** Mapeia as 12 capabilities-alvo do `INVESTIQ_UPGRADE_PLAN.md` V1 §2 + `opportunity_detector` para o que já existe no repositório, propõe nomenclatura única para eliminar redundância (V2 §22 princípio 11), e define status real (não o status assumido pelo V2 §5).

> **Uso:** este documento é a **fonte canônica** de "o que vai chamar como" no Agent Mesh. Renomeação física dos módulos no código é Fase 1 (não Fase 0).

---

## Tabela única — 12 capabilities + opportunity_detector

| # | Capability alvo (V1 §2) | Roadmap atual (v1.4 / v1.5 / v1.6 / v1.7) | Módulo / arquivo atual | **Nome unificado proposto** | Status |
|---|---|---|---|---|---|
| 1 | **§2.1 — Decision Copilot** (chat conversacional + estruturado) | parcialmente coberto por v1.5 ADVI-02 (advisor analyze) e por `opportunity_detector` Phase 1 | [`advisor/router.py`](../../backend/app/modules/advisor/router.py) (POST `/advisor/analyze`) + [`opportunity_detector/analyzer.py`](../../backend/app/modules/opportunity_detector/analyzer.py) (4 agents async) | **`decision_copilot_flow`** (LangGraph) com Decision Engine determinístico antes do LLM | **Parcial** — falta orquestração unificada, streaming SSE, Decision Engine isolável |
| 2 | **§2.2 — Análise de carteira** (Portfolio Health) | v1.5 Phase 23 ADVI-01 (Portfolio Health Check) + v1.5 Phase 24 ADVI-02 (AI narrative) | [`advisor/service.py:compute_portfolio_health`](../../backend/app/modules/advisor/service.py) + [`ai/skills/portfolio_advisor.py`](../../backend/app/modules/ai/skills/portfolio_advisor.py) | **`Portfolio Agent`** (renomear `advisor` → `portfolio_agent`) | **Existente (shipped 2026-04-18)** — D3 |
| 3 | **§2.3 — Análise de ativo** (DCF + valuation + earnings + fundamentals) | v1.4 SCRA + v1.1 Phase 12 AI Analysis Engine | [`analysis/dcf.py`](../../backend/app/modules/analysis/dcf.py), [`analysis/earnings.py`](../../backend/app/modules/analysis/earnings.py), [`analysis/data.py`](../../backend/app/modules/analysis/data.py), [`ai/skills/dcf.py`](../../backend/app/modules/ai/skills/dcf.py), [`ai/skills/valuation.py`](../../backend/app/modules/ai/skills/valuation.py), [`ai/skills/earnings.py`](../../backend/app/modules/ai/skills/earnings.py) | **`Asset Research Agent`** — wrapper sobre as 5 skills + screener_v2 | **Existente (shipped)** — empacotamento como tools = Fase 3 |
| 4 | **§2.4 — Análise de gráfico** (Chart Vision) | — | — | **`Chart Vision Agent`** (Anthropic vision + cross-check com API de preços) | **Não existe** — Fase 5 |
| 5 | **§2.5 — Notícias do dia** | — (sem ingestion de news) | — | **`News Agent`** (consulta tabela `events`, ranqueia por relevância vs carteira) | **Não existe** — Fase 2 (ingestion) + Fase 3 (digest) |
| 6 | **§2.6 — Briefing de tema macro** | — | — | **`Theme Briefing Agent`** (Tavily + Opus + cross-ref carteira) | **Não existe** — Fase 5 |
| 7 | **§2.7 — Análise grupo WhatsApp** (paste de print/conversa) | — | — | **`WhatsApp Scan Agent`** (extract tickers + pump&dump detection) | **Não existe** — Fase 5 (premium Enterprise) |
| 8 | **§2.8 — Renda fixa** (catálogo + comparador + simulador) | v1.4 RF-01/02/03 (catálogo) + v1.6 Comparador RF×RV + v1.7 Simulador de Alocação | [`screener_v2/service.py:query_fixed_income_catalog`](../../backend/app/modules/screener_v2/service.py), [`screener_v2/service.py:query_tesouro_rates`](../../backend/app/modules/screener_v2/service.py), [`comparador/service.py`](../../backend/app/modules/comparador/service.py), [`simulador/service.py`](../../backend/app/modules/simulador/service.py) | **`Fixed Income Agent`** — agrupa catálogo + comparador + simulador como tools | **Existente (shipped 2026-04-19)** — mas **bloqueado em prod** por macro nulls (P0 do audit `2026-04-AUDIT.md`) |
| 9 | **§2.9 — Fundos** (FIA / FIM / multimercados) | — | — | **`Fund Agent`** | **Não existe** — Fase posterior (não MVP V2) |
| 10 | **§2.10 — Alertas** (preço + signals + watchlist) | v1.0 Phase 6 watchlist + Phase 7 price alerts + emails Resend | [`watchlist/router.py`](../../backend/app/modules/watchlist/router.py), [`watchlist/tasks.py:check_price_alerts`](../../backend/app/modules/watchlist/tasks.py), [`watchlist/models.py`](../../backend/app/modules/watchlist/models.py) (`watchlist_items.price_alert_target`) | **`Alerts Service`** (não-agent — serviço base que outros agents emitem) | **Existente (shipped)** — estender `price_alert` → `signal_alert` (Fase 4) |
| 11 | **§2.11 — Modo debate** (Devil's Advocate cross-model) | — | — | **`Devils Advocate Flow`** (LangGraph; modelo diferente do gerador) | **Não existe** — Fase 4 |
| 12 | **§2.12 — Backtest rápido** | — | — | **`Backtester`** (módulo Python puro; janelas históricas) | **Não existe** — Fase 6 (gate para dinheiro real) |
| ➕ | `opportunity_detector` Phase 1 (V1 backlog ativo) | v1.3 Phase 19 (página) + Phase 1 do detector (4-agent async) | [`opportunity_detector/scanner.py`](../../backend/app/modules/opportunity_detector/scanner.py) (3 Celery tasks: acoes / crypto / fixed_income) + [`opportunity_detector/agents/`](../../backend/app/modules/opportunity_detector/agents) (`cause.py`, `fundamentals.py`, `risk.py`, `recommendation.py`) + [`opportunity_detector/alert_engine.py`](../../backend/app/modules/opportunity_detector/alert_engine.py) | **`Opportunity Detector Flow`** — primeiro fluxo a ser portado para LangGraph; serve como **template** para todos os outros 5 flows | **Existente (shipped)** — D6 confirma. Porte para LangGraph = Fase 3 (template) |

---

## Renomeações propostas (Fase 1 — não Fase 0)

> Aplicar via `git mv` + ajuste de imports + rota mantém-se com path antigo (`/advisor/*`) com redirect transparente até Fase 5 quando rota nova `/copilot/*` estabiliza.

| Antes (atual) | Depois (Fase 1) | Justificativa |
|---|---|---|
| `app/modules/advisor/` | `app/modules/portfolio_agent/` | Match com nomenclatura Agent Mesh (V2 §3) |
| `ai/skills/portfolio_advisor.py` | `app/modules/portfolio_agent/skills/narrative.py` | Sub-skill do Portfolio Agent |
| `app/modules/analysis/` (Phase 12) | `app/modules/asset_research_agent/` | Match com nomenclatura Agent Mesh |
| `ai/skills/dcf.py`, `valuation.py`, `earnings.py`, `macro.py` | `app/modules/asset_research_agent/skills/{dcf,valuation,earnings,macro}.py` | Tools do agent, não skills livres |
| `app/modules/comparador/`, `simulador/`, `screener_v2/renda_fixa/*` | `app/modules/fixed_income_agent/` (consolida tools) | 3 módulos hoje viram tools de 1 agent |
| `app/modules/opportunity_detector/` | `app/modules/agents/opportunity_detector/` (sub-pacote `agents/`) | Padrão para os 11 agents do Agent Mesh |
| `app/modules/insights/` (`generate_daily_insights`) | `app/modules/news_agent/` (Fase 2+ quando ingestion existir) | Insights hoje são pré-cursor; viram outputs do News Agent |

---

## Disambiguação por capability — onde "mesma coisa, dois nomes"

### Caso 1: "Advisor" vs "Portfolio Agent"

- **No repo hoje:** módulo `advisor` cobre **dois usos diferentes**:
  - `compute_portfolio_health` (sync, sem AI) — diagnóstico da carteira
  - `POST /advisor/analyze` (async, AI) — narrativa explicando a carteira
- **No V2 §3:** "Portfolio Agent" é o agent que **lê a carteira do usuário** e **expõe estado** para o Decision Copilot.
- **Resolução:** o módulo `advisor` inteiro vira `portfolio_agent`. O Decision Copilot consome `portfolio_agent.get_state()` e separadamente pode chamar `portfolio_agent.skills.narrative()` se o usuário quiser explicação.

### Caso 2: "Renda Fixa" — 3 módulos hoje, 1 agent depois

- **No repo hoje:** `screener_v2/renda_fixa` (catálogo) + `comparador/` (RF×RV) + `simulador/` (alocação) — três módulos separados.
- **No V2 §3:** `Fixed Income Agent` único.
- **Resolução:** consolidar em `fixed_income_agent/` com 3 sub-módulos (`catalog/`, `comparator/`, `simulator/`). API HTTP mantém endpoints atuais para não quebrar frontend; service interno passa por classe `FixedIncomeAgent`.

### Caso 3: "Opportunity Detector" — entre app feature e template do Agent Mesh

- **No repo hoje:** módulo standalone com Celery scanners + 4 agents async + página frontend `/oportunidades/`.
- **No V2 §3:** chamado de "padrão 4-agent" e "template do Agent Mesh".
- **Resolução:** **manter como app feature** (continua scanando radar). Em paralelo, **portar o pipeline** para LangGraph como `flows/opportunity_detector_flow.py` na Fase 3 — o Celery scanner passa a chamar o flow LangGraph em vez do `analyzer.run_analysis()` atual. Migração incremental sem quebrar o frontend.

### Caso 4: "Insights diários" vs "News Agent"

- **No repo hoje:** [`insights/tasks.py:generate_daily_insights`](../../backend/app/modules/insights/tasks.py) gera notificações diárias por carteira. Não consome news (ainda não há ingestion).
- **No V2 §3:** `News Agent` consome `events`, ranqueia, gera digest.
- **Resolução:** quando ingestion de news existir (Fase 2), `generate_daily_insights` vira chamador do `news_agent.daily_digest(tenant_id)`. Nome do módulo migra para `news_agent/` na Fase 3.

### Caso 5: "Watchlist alerts" vs "Alerts Service"

- **No repo hoje:** `watchlist_items.price_alert_target` é o único trigger.
- **No V2 §3:** `Alerts Service` (não-agent) recebe events de qualquer agent (Decision Copilot, Opportunity Detector, etc.) e dispara via email/WhatsApp/in-app.
- **Resolução:** estender `watchlist_items` com coluna `signal_alert_config JSONB` (Fase 4) — qualquer agent pode emitir `AlertEmitted(tenant_id, ticker, kind, payload)`.

---

## Status consolidado

| Categoria | Quantidade | Capabilities |
|---|---|---|
| **Existente (shipped, em prod)** | 4 | §2.2 Portfolio Health, §2.3 Asset Analysis, §2.8 Fixed Income, §2.10 Alertas |
| **Existente — opp_detector** | 1 | (extra) Opportunity Detector Phase 1 |
| **Parcial** | 1 | §2.1 Decision Copilot (advisor + opp_detector existem; falta unificação) |
| **Não existe** | 7 | §2.4 Chart Vision, §2.5 News, §2.6 Theme Briefing, §2.7 WhatsApp, §2.9 Fundos, §2.11 Devil's Advocate, §2.12 Backtest |

**Bottom line:** ~38% do alvo V2 já está em produção. O upgrade é **conectar e estender**, não construir do zero.

---

## Onde isto é referenciado

- [`docs/audit/PHASE_0_AUDIT.md`](../audit/PHASE_0_AUDIT.md) §21.3 (Inventário de Capabilities) — formato resumido
- [`docs/adr/ADR-001-stack-freeze.md`](../adr/ADR-001-stack-freeze.md) — congela linguagem dos agents (Python)
- [`docs/adr/ADR-002-orchestration-spike.md`](../adr/ADR-002-orchestration-spike.md) — escolhe lib de orquestração (LangGraph vs Pydantic AI)
- [`docs/reconciliation/TIER_MATRIX.md`](TIER_MATRIX.md) — quem (Free/Pro/Enterprise) acessa cada capability + custo/usuário/mês
