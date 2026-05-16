# Phase v1.8: Audit & Hardening — Context

**Gathered:** 2026-05-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Revisar e endurecer o que já existe sem quebrar produção. Nenhuma feature nova até o audit estar fechado.

**Escopo:**
1. Fechar os findings do audit de abril/2026 (P0 → P1 → P2 em ordem)
2. Deploy das 3 branches Wave E pendentes (c021df1 + 051fb5a + 3921f2b) com migrations 0033/0034
3. Gap analysis conceitual contra o UPGRADE_PLAN (sem troca de stack)
4. Waves de hardening pequenas com PR atômico, teste verde antes de avançar

**Fora de escopo:** Novas features (Wave F, admin dashboard, RLS DB-level, chat conversacional, WhatsApp scan, vision agent). Tudo isso vai para backlog explícito.

</domain>

<decisions>
## Implementation Decisions

### Stack — não negociável (ADR-001/002)
- **D-01:** FastAPI + SQLAlchemy 2.x async + Alembic + Celery + Redis + PostgreSQL + Next.js 15 — stack congelada.
- **D-02:** LangGraph reservado para Fase 5 Premium — não usar agora.
- **D-03:** ADR-003 (Redis cache + tier-based model + kill switch LLM) permanece.
- **D-04:** Princípio mestre: evoluir incrementalmente, nunca reescrever. Refactor in-place.

### Prioridade de hardening
- **D-05:** P0 antes de qualquer outra coisa (CORS/Idempotency-Key + macro rates null).
- **D-06:** Wave E deploy (migrations 0033/0034 + beat tasks) acontece na mesma janela dos P0, pois o backend precisa ser re-deployado de qualquer forma.
- **D-07:** Quick wins (alertas de preço, observabilidade barata, test fixes) ficam na Wave 1.
- **D-08:** P2/P3 compõem Wave 2 e Wave 3.

### Critério de "v1.8 shipped"
- **ABERTA — confirmar com usuário** (ver seção de perguntas no PLAN.md).
- Proposta padrão: v1.8 = hardening completo (P0+P1 zero, P2 material reduzido), sem feature nova obrigatória.

### Outcome tracking
- **ABERTA — confirmar com usuário** (ver seção de perguntas no PLAN.md).
- Tabela `signal_outcomes` (migration 0030) e ORM model `SignalOutcome` já existem.
- `outcome_tracker/` router/service/tasks existem e estão registrados em main.py.
- Questão: começar a popular outcomes agora (mesmo sem UI de paper trading formal)?

### Devil's advocate
- **ABERTA — confirmar com usuário** (ver seção de perguntas no PLAN.md).
- Proposta: entrar agora via Haiku + cache como passo final barato do Advisor, não Opus.

### Schema canônico de eventos
- **ABERTA — confirmar com usuário** (ver seção de perguntas no PLAN.md).
- `news_events` (migration 0034) e `sentiment_snapshots` (migration 0033) já existem no código local.
- Questão: criar tabela unificada `events` ou usar as duas tabelas separadas (atual)?

### Alertas de preço (watchlist)
- **D-09:** `check_price_alerts` está registrado no beat (`check-price-alerts`, every 30min 10-17h Mon-Fri).
- O test `test_email_content_contains_key_info` falha porque patcha o caminho Brevo/httpx antigo — o código real usa `core/email.py` (Resend primário). Fix é P1-1 (test fixes cluster).
- A task em si implementa dedup via Redis (TTL 23h), MGET pipeline, email via `send_price_alert_email`. Funcional em design; test de confirmação quebrado.
- **ABERTA — confirmar com usuário:** alertas estão disparando em produção ou só o teste está quebrado?

### Observabilidade
- **D-10:** Sentry SDK (FastAPI + Celery) é o quick win de APM — zero configuração de infra, $0 no free tier.
- **D-11:** Métricas Prometheus mínimas do §15 do UPGRADE_PLAN: latência de endpoint, contagem de erros Celery, cache hit/miss Redis.
- **D-12:** `auth/service.py` e `portfolio/service.py` sem logging — adicionar structured logs como P1-5.

### Async Redis
- **D-13:** Substituir `_get_sync_redis_for_signals()` em `advisor/service.py` por `redis.asyncio` client (mesma URL, sem mudança de schema).

### TypeScript build errors
- **D-14:** `typescript: { ignoreBuildErrors: true }` em `next.config.ts` — remover e corrigir erros expostos. Proposta P1-3 do audit.

### Execução
- **D-15:** Cada wave = 1 PR pequeno. Testes verdes antes de avançar.
- **D-16:** Sem `git push` sem autorização explícita do usuário.
- **D-17:** Deploy backend via `bash deploy-backend.sh --migrate`; frontend via `bash deploy-frontend.sh`.
- **D-18:** SSH via `ssh -i ~/.ssh/id_ed25519_vps root@185.173.110.180` (não plink, não senha).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit existente
- `.planning/audits/2026-04-AUDIT.md` — Findings P0–P3 completos, smoke tests, coverage estimates, feature audits por módulo (v1.4–v1.7). Fonte primária para as waves de hardening.

### Estado do projeto
- `.planning/PROJECT.md` — Visão, constraints, stack decisions, requirements validated/active/out-of-scope.
- `.planning/STATE.md` — Progress bar v1.7, accumulated context, infra details, deploy patterns.
- `.planning/ROADMAP.md` — Architecture notes Phase 28, key design decisions.

### ADRs implícitos (documentados no STATE.md)
- ADR-001: Stack congelada (FastAPI + Next.js 15 + PostgreSQL + Redis + Celery) — `STATE.md` §Accumulated Context / §Architecture
- ADR-002: LangGraph para Fase 5 Premium apenas — `STATE.md` §Decisions
- ADR-003: LLM cost guardrails (Redis cache + tier model + kill switch) — `STATE.md` §Decisions

### Wave E — código pendente deploy
- `backend/app/modules/briefing_engine/` — 14 seções de briefing, context_assembler, router
- `backend/app/modules/news/` — adapters (reddit, stocktwits, CVM, finnhub, gnews), ingestion, tasks
- `backend/app/modules/outcome_tracker/` — models (signal_outcomes 0030), router, service, tasks
- `backend/app/modules/swing_trade/copilot.py` — Copilot V2 com sentiment context
- `backend/alembic/versions/0033_add_sentiment_snapshots.py`
- `backend/alembic/versions/0034_add_news_events.py`

### Frontend
- `frontend/next.config.ts` — TypeScript `ignoreBuildErrors: true` (alvo P1-3)
- `frontend/e2e/` — Playwright E2E tests

### Infra
- `backend/app/main.py` — CORS config (alvo P0-1: Idempotency-Key), router registrations
- `backend/app/celery_app.py` — beat schedule completo (Wave E tasks registrados em lines 231-248)
- `backend/app/core/db.py:44` — RLS tenant_id interpolation (alvo P2-7)

### Referência conceitual (não trocar stack)
- Brief do usuário de 2026-05-13 (esta sessão) — UPGRADE_PLAN conceitos a absorver vs ignorar vs adiar.
  Absorver: schema canônico de eventos, decision engine com gates, Kelly fracionário, devil's advocate,
  outcome tracking, observabilidade §15, gates de qualidade, anti-padrões §20.
  Ignorar: prescrições de stack Node/TS/.NET/Mastra/Temporal/Qdrant/Vercel AI SDK.
  Adiar: chat conversacional, agent mesh, vision agent, WhatsApp scan, theme briefing.

</canonical_refs>

<code_context>
## Existing Code Insights

### Estado real do codebase (2026-05-13)

**Migration head local:** 0034 (add_news_events) — Wave E Phase 30 schema já no repositório.
**Migration head em produção:** 0032 (add_ai_mode_to_users) — commits c021df1/051fb5a/3921f2b pendentes deploy.

### Módulos Wave E já no código (pendentes deploy)
- `briefing_engine/` — registrado em main.py (line 161) com prefix `/briefing`
- `outcome_tracker/` — registrado em main.py (line 159) com prefix `/outcomes`
- `news/adapters/` — reddit_adapter.py, stocktwits_adapter.py existem
- `news/tasks.py` — `ingest_sentiment_snapshots`, `ingest_news_events` registrados no beat
- Beat tasks Wave E: `ingest-sentiment-snapshots` (*/30 min pregão), `ingest-news-events` (*/2h), `auto-close-outcomes` (18h30 Mon-Fri), `send-morning-briefing` (08h30 Mon-Fri)

### Módulos com problemas identificados
- `advisor/service.py` — `_get_sync_redis_for_signals()` bloqueia event loop async (P2-2)
- `advisor/router.py:230` — `limit: int = 100` sem cap (P2-1)
- `main.py:70` — CORS sem `Idempotency-Key` em `allow_headers` (P0-1)
- `dashboard/router.py:59`, `ir_helper/router.py:34` — FastAPI `regex=` deprecado (P2-10)
- `core/db.py:44`, `core/db_sync.py:105` — f-string interpolation para tenant_id (P2-7)

### Módulos sem logging
- `auth/service.py` — zero logger calls (P1-5)
- `portfolio/service.py` — zero logger calls (P1-5)

### Reusable Assets
- `core/email.py` — send_price_alert_email, Resend primário (test_price_alerts_task.py patcha caminho antigo)
- `signal_engine/` — gates determinísticos, compute_signals() — não alterar
- `swing_trade/` — Kelly em kelly.py, copilot.py com Copilot V2

### Integration Points
- Wave E deploy conecta em: Celery beat (já registrado), PostgreSQL (migrations 0033/0034), Redis (sentiment TTL), Telegram bot (briefings)
- Sentry SDK: adicionar em `main.py` (middleware) + `celery_app.py` (signals)

### Test Suite
- 57 test files em `backend/tests/`
- 18 falhas (conforme audit abril): `test_phase12_foundation.py` (6 stale patches), `test_dashboard_api.py` (2 — sem PortfolioDailyValue ORM), `test_price_alerts_task.py` (1 — caminho email antigo), `test_phase20_swing_trade.py` (2 — asyncio/trio delete), outros 7
- Frontend: zero testes unitários (sem Vitest/Jest no package.json)
- Playwright E2E: existem em `frontend/e2e/`, última execução v1.7

</code_context>

<specifics>
## Specific Ideas

- Alertas de preço: o usuário mencionou explicitamente como "quick win #1 — confiança do usuário". Verificar se estão disparando em produção antes de concluir que o único problema é o teste.
- Sentry como quick win de APM: zero infra, free tier, integra em <2h (FastAPI middleware + Celery signals).
- Devil's advocate: se entrar, vai com Haiku (barato) como último passo do Advisor. Não Opus. Cache obrigatório.
- Outcome tracking: tabela já existe (signal_outcomes, migration 0030). Questão é apenas começar a popular vs esperar paper trading formal.
- Cada wave = 1 PR. Commit message claro. Testes verdes antes de avançar.

</specifics>

<deferred>
## Deferred Ideas

### Para Fase 2 do roadmap (News por ticker)
- Tabela `events` unificada (se decidido no v1.8-audit que vale criar agora, sai na Wave 2; caso contrário, Phase 2 do roadmap)
- News ticker tagging com LLM para fontes novas além de CVM/GNews

### Para Fase 5 (Premium / LangGraph)
- Agent mesh completo
- Chat conversacional

### Para Fase 6 (Paper trading + outcome tracking formal)
- UI de operações paper (entry/exit) ligada ao outcome_tracker
- Calibração automática de PATTERN_WEIGHTS via outcomes acumulados

### Para roadmap backlog
- Admin dashboard (MON-04) — assinantes, status Stripe, churn
- PostgreSQL RLS enforcement no DB level (AUTH-05)
- X API paga (sentiment source)
- Benzinga
- WhatsApp scan, vision agent, theme briefing
- Frontend unit tests (Vitest + React Testing Library)
- Mobile PWA

### Capacidades do UPGRADE_PLAN adiadas para fases 2–6
- Schema de eventos canônico unificado (`events` table) — depende de decisão sobre `news_events` + `sentiment_snapshots` actuais
- Decision engine com gates auditáveis — gates já são determinísticos no signal_engine; auditabilidade completa é Fase 5
- Outcome tracking com UI — Fase 6
- Calibração automática — Fase 6 (depende de outcomes acumulados)
- Devil's advocate como passo padrão — decisão aberta neste ciclo

</deferred>

---

*Phase: v1.8-audit-hardening*
*Context gathered: 2026-05-13*
