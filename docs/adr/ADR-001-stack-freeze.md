# ADR-001 — Stack Freeze para o Upgrade V2

- **Status:** Accepted
- **Date:** 2026-04-19
- **Decision authors:** Alexandre Queiroz (D1–D8 lock), Claude Code (Fase 0 audit)
- **Supersedes:** propostas implícitas de stack do `INVESTIQ_UPGRADE_PLAN.md` original (Node/TS/Next.js greenfield)
- **Related:** ADR-002 (orquestração: LangGraph vs Pydantic AI — *Proposed*)

## Contexto

O `INVESTIQ_UPGRADE_PLAN.md` (V1) descrevia uma arquitetura-alvo correta para o produto, mas seu plano de execução assumia greenfield em Node/TypeScript/Next.js — uma reescrita completa do backend Python existente.

O `INVESTIQ_UPGRADE_PLAN_V2.md` reconciliou parcialmente a visão com a stack real, mas ainda traz duas premissas erradas que a Fase 0 audit ([`docs/audit/PHASE_0_AUDIT.md`](../audit/PHASE_0_AUDIT.md)) confirmou:

1. **V2 §0/§3/§4 cita "FastAPI + Django mantidos".** Django **não existe no repositório.** Backend é FastAPI puro + SQLAlchemy 2.x async + Alembic ([`backend/requirements.txt:1-29`](../../backend/requirements.txt), [`backend/app/main.py:14-44`](../../backend/app/main.py)). Auth, billing, admin, rate-limit — tudo em FastAPI.
2. **V2 §5 lista `ANBIMA` como fonte de dados.** Não há cliente ANBIMA. Tesouro Direto é obtido por scraping HTML do site oficial (task `refresh_tesouro_rates`); BCB usa `python-bcb`.

Esta ADR formaliza a decisão **D1–D5** do usuário (mensagem em `chore(audit): phase 0 — audit & reconciliation` PR description) que congela a stack a ser usada no upgrade V2.

## Decisão

A partir desta data, **a stack do InvestIQ está congelada nas escolhas abaixo.** Mudar qualquer uma delas requer nova ADR explícita justificando trigger de negócio.

### Backend (canônico — D1)

| Camada | Escolha congelada | Justificativa |
|---|---|---|
| API pública e admin | **FastAPI 0.115.x** | Stack única — não há Django no repo. Async nativo, SSE simples, ecossistema Python para market data. Já em produção. |
| ORM | **SQLAlchemy 2.x async** + `asyncpg` para FastAPI; `psycopg2` sync para Celery (separação documentada em [`celery_app.py:13-16`](../../backend/app/celery_app.py)) | Já em produção; Alembic autogenerate funcional. |
| Migrations | **Alembic 1.13.x** | 29 migrations existentes, cadeia íntegra. |
| Workers | **Celery 5.4 + Celery Beat** | 17 tasks beat agendadas em produção. Não trocar por Temporal antes de >10k tasks/dia (V2 §19). |
| Queue/cache | **Redis** (broker Celery + cache + rate limit) | Mesma instância; uso ampliará em Fase 2 (cache de cotações + sessions). |
| Auth | **PyJWT RS256 + bcrypt + httpOnly cookies** | Já em produção em [`core/security.py`](../../backend/app/core/security.py). 2FA fica para Fase 6+ (ver red flag #4 em §21.8). |
| Rate limit | **slowapi** sobre Redis | Default IP-based; endpoints sensíveis sobrescrevem com user_id-based. |
| LLM clients | **`httpx` direto** com fallback chain (OpenAI → OpenRouter → Groq; free pool: Groq + Cerebras + Gemini) | Implementado em [`ai/provider.py`](../../backend/app/modules/ai/provider.py). Reutilizar; não introduzir LangChain, LiteLLM, etc. |

### Frontend (D5)

| Camada | Escolha congelada | Justificativa |
|---|---|---|
| Framework | **Next.js 15.2.3 App Router** | Já em produção ([`frontend/package.json:11-22`](../../frontend/package.json)). Não greenfield — extensão. |
| Runtime | **React 19** | Já em produção. |
| Estado servidor | **TanStack Query v5** | `staleTime` por endpoint já calibrado ([2026-04-AUDIT.md:236-242](../../.planning/audits/2026-04-AUDIT.md)). |
| Estilo | **Tailwind 3.4 + shadcn/ui** | Já em produção. |
| Charts | **Recharts** + **Lightweight Charts** | Já em produção. |
| Streaming chat | **SSE consumido client-side do FastAPI** | Não Vercel AI SDK / RSC (V2 §0 já corrigia). |
| Padrão visual | manter design system atual + tokens existentes | Não introduzir nova lib de UI (Material/Mantine/etc.). |

### Data layer (D2)

| Componente | Escolha congelada | Notas |
|---|---|---|
| DB principal | **PostgreSQL** (mesma instância) | RLS por `tenant_id` já configurado ([`core/db.py:44`](../../backend/app/core/db.py)). |
| Extensão time-series | **TimescaleDB** (instalar Fase 1) | Hypertables `events`, `prices`, `features`. |
| Extensão vector | **pgvector** (instalar Fase 1) | Embeddings in-DB; **sem Qdrant no MVP** (V2 §19 explicit "não fazer"). |
| Object storage | **Cloudflare R2** (Fase 5+ quando houver screenshots/parquet) | S3-compatible; free tier suficiente. |
| Fontes de market data | **brapi.dev** (B3), **`python-bcb`** (BCB), **Binance** público (crypto), **Tesouro Direto** (scraping HTML — substituir por fonte oficial quando latência importar) | **ANBIMA NÃO ENTRA** (D2 — premissa errada do V2). |

### Orquestração de agentes (D7 — referência a ADR-002)

A escolha entre **LangGraph Python** vs **Pydantic AI** está em ADR-002 com status *Proposed* + plano de spike de 2 dias antes de Fase 2. Esta ADR registra apenas que **a linguagem é Python** (não TypeScript/Mastra).

### Stack de LLMs (D8 — congela escolhas, custos parametrizados em TIER_MATRIX)

| Tarefa | Modelo primário | Notas |
|---|---|---|
| Roteamento de intents | Claude Haiku 4.5 | Rápido, barato |
| Classificação batch (news) | Claude Haiku 4.5 + Anthropic Batch API | Cost ceiling em [`docs/reconciliation/TIER_MATRIX.md`](../reconciliation/TIER_MATRIX.md) |
| Vision (chart) | Claude Opus 4.7 + Gemini 2.5 Pro fallback | Cross-check obrigatório com API de preços |
| Tese / Briefing macro | Claude Opus 4.7 (com web search via Tavily) | Pontual, com cap mensal no Pro |
| Devil's Advocate | Modelo **diferente** do gerador (GPT-5 ou Gemini 2.5 Pro) | Reduz viés de concordância |
| Embeddings | Voyage-3 primário, OpenAI `text-embedding-3-large` fallback | Voyage ~ metade do preço |
| Free tier | Pool free (Groq llama-3.3-70b/llama-4-scout/kimi-k2/qwen3-32b/openai-oss-20b/llama-3.1-8b; Cerebras llama3.1-8b; Gemini 2.5 Flash) | Já implementado em [`ai/provider.py`](../../backend/app/modules/ai/provider.py) |

### Observabilidade (Fase 2)

- **Sentry SDK** (FastAPI integration + Celery integration)
- **OpenTelemetry** + Grafana Cloud free tier
- `trace_id` injetado em request middleware e propagado para Celery via `apply_async(headers={...})`
- Custom `app_logs` table mantida como ledger interno (espelha Sentry)

## Consequências

### Positivas

- **Reuso máximo do código testado em produção.** Phases 11–28 (incluindo v1.4 SCRA, v1.5 Advisor completo, v1.6 Comparador, v1.7 Simulador) ficam intactos.
- **Velocidade de Fase 1 maximizada.** Sem reescrita; Decision Engine entra como módulo novo `decision_engine/` em Python puro chamável por endpoints existentes.
- **Time familiar com a stack.** Toda nova feature usa convenções já estabelecidas (módulos sob `app/modules/{name}/{router,service,schemas,tasks,models}.py`).
- **Custo unitário controlado.** Não pagar por SDK comercial (Vercel AI SDK premium, Mastra hosted, Temporal Cloud).

### Negativas

- **Ecossistema Python para vision/streaming não é tão maduro quanto Node.** Mitigação: SSE direto do FastAPI; vision usa Anthropic SDK Python (suportado).
- **`pgvector` tem limites em ~50M embeddings.** Mitigação: V2 §19 já estabelece migrar para Qdrant **só quando** pgvector ficar lento — gate quantitativo.
- **Tesouro Direto via scraping é frágil.** Aceito hoje; red flag P2 em [`PHASE_0_AUDIT.md` §21.8](../audit/PHASE_0_AUDIT.md) — substituir por fonte oficial quando latência importar.
- **TypeScript no frontend isolado do backend.** Sem schema-sharing automático (ex.: tRPC, OpenAPI client gen). Mitigação: gerar tipos via OpenAPI a partir do FastAPI quando contratos estabilizarem (Fase 5).

### Neutras

- **Renomeação de módulos** (V2 §22 princípio 11 — "nomenclatura unificada"): mapeamento em [`docs/reconciliation/CAPABILITY_MAPPING.md`](../reconciliation/CAPABILITY_MAPPING.md). Renomeação física é Fase 1 (não Fase 0).

## Alternativas consideradas

### A — Reescrever backend em Node/TypeScript + Next.js API Routes (proposta original do V1)

- **Custo:** ~3–4 meses só para parity com hoje, depois mais 6 meses para Fase 1–6.
- **Risco:** alto — duas codebases em paralelo; staff conhece Python; cancelaria Phases 23–26 (já em prod).
- **Benefício:** RSC streaming nativo, schema-sharing.
- **Decisão:** rejeitado. Princípio V2 §22.9 ("evoluir antes de reescrever") é absoluto aqui.

### B — Migrar para .NET 8

- **Custo:** alto — staff não conhece, ecossistema Python para market data BR (yfinance/python-bcb/correpy/pdfplumber) não tem paralelo direto em .NET.
- **Decisão:** rejeitado. Não alinhado com ecossistema de data e perfil do desenvolvedor.

### C — Manter Python mas trocar FastAPI por Django + DRF

- **Custo:** médio — admin pronto, mas perde async nativo e SSE simples.
- **Decisão:** rejeitado. Async é requisito para streaming chat (V2 §3 UI Layer); Django Async ainda é beta. Sem benefício suficiente.

### D — Manter Python mas adicionar Temporal para workflows

- **Custo:** médio — Temporal Cloud US$50+/mo + reescrever tasks Celery.
- **Decisão:** rejeitado por ora. V2 §19 explicit: "não migrar Celery para Temporal antes de 10k tasks/dia". Volume atual é ~1k tasks/dia.

## Re-abertura desta ADR

Esta decisão deve ser reavaliada se um destes triggers ocorrer:

- Volume de tasks Celery > 10k/dia (gatilho Temporal)
- pgvector latência p95 > 500ms para queries de retrieval (gatilho Qdrant)
- ARPU Pro > US$ 30/mês justificando staff dedicado a Node/TS para frontend rico
- Necessidade comprovada de RSC streaming (não cobrível por SSE)

**Sem trigger comprovado por dados, esta ADR permanece em vigor.**
