# InvestIQ — Fase 0 Audit & Reconciliation

**Date:** 2026-04-19
**Branch:** `chore/audit-phase-0`
**Plan reference:** `INVESTIQ_UPGRADE_PLAN_V2.md` §17 (Fase 0) e §21 (template)
**Locked decisions:** D1–D8 (ver mensagem do usuário em `chore(audit): phase 0` PR description)

> Este relatório preenche §21.1–§21.9 do V2. **Nenhuma linha de código de produção foi escrita nesta fase.**
> Cada claim cita arquivo:linha do repositório no estado em que ele estava em `main` (commit `493cb8c`).

---

## Sumário Executivo (≤15 linhas)

- **Stack real ≠ stack documentada no V2.** Backend é FastAPI puro (não FastAPI+Django). 28 tabelas, 29 migrations, ~5.4k linhas de modules Python. ([requirements.txt:1-29](../../backend/requirements.txt), [migrations](../../backend/alembic/versions))
- **v1.5 (Phases 23–26) e v1.7 (Phase 28) já em produção.** Portfolio Health, AI Advisor, Smart Screener, Entry Signals, Comparador RF×RV e Simulador Alocação são *Existente*, não *em planejamento* como o V2 §5 assume.
- **Fundação para a visão V2 está ausente:** sem `events`/`prices`/`features`/`signals`/`outcomes` canônicos, sem `pgvector`, sem `TimescaleDB`, sem ingestion de news, sem Decision Engine determinístico isolável.
- **Padrão 4-agent já existe:** `opportunity_detector` (cause→fundamentals→risk→recommendation) é template natural do Agent Mesh — Fase 3 do V2 reduz de 3-4 sem para ~2 sem.
- **Bloqueios P0 conhecidos do audit `2026-04-AUDIT.md`:** CORS sem `Idempotency-Key` quebra hotfix billing em prod; macro rates null em prod (CDI/IPCA/SELIC) — quebra Comparador e Simulador.
- **Operação descoberta (red flag P1):** sem staging, sem GitHub Actions, sem APM. Deploy direto em VPS via plink/PuTTY. Cada deploy é teste em produção.
- **Custo unitário ainda não medido por usuário** — apenas custo agregado em `analysis_cost_logs` + `ai_usage_logs`. Decisão Fase 1: instrumentar per-tenant antes de adicionar capabilities premium.
- **Quick wins (≤3 dias) destravam ~70% das pendências P0/P1** (ver §21.9).

---

## §21.1 — Inventário de Ingestion

Fonte primária: [`backend/app/celery_app.py:65-167`](../../backend/app/celery_app.py).
Workers usam `psycopg2` (sync); FastAPI usa `asyncpg`. Schema dual documentado em `celery_app.py:13-16`.

### Beat schedule (15 tasks registradas)

| # | Fonte | Task Celery | Frequência | Status | Tabela / Cache destino | Volume/dia |
|---|---|---|---|---|---|---|
| 1 | brapi.dev | `app.modules.market_data.tasks.refresh_quotes` | a/15min, Mon–Fri 10–17 BRT | OK | Redis `market:quote:{TICKER}` + `market:fundamentals:{TICKER}` ([tasks.py:67-140](../../backend/app/modules/market_data/tasks.py)) | ~480 req/d (8 tickers fixos) |
| 2 | BCB (`python-bcb`) | `app.modules.market_data.tasks.refresh_macro` | a/6h | **FALHA EM PROD** | Redis `market:macro:{cdi,ipca,selic,ptax_usd}` ([tasks.py:143-172](../../backend/app/modules/market_data/tasks.py)) | 4/d esperado, **0 observado** ([2026-04-AUDIT.md:200](../../.planning/audits/2026-04-AUDIT.md)) |
| 3 | brapi (universe) | `app.modules.market_universe.tasks.refresh_screener_universe` | diário 07h BRT Mon–Fri | OK | `screener_snapshots` (~2000 rows) | 1/d |
| 4 | brapi (FII) | `app.modules.market_universe.tasks.refresh_fii_metadata` | semanal Mon 06h BRT | OK | `fii_metadata` | 1/sem |
| 5 | tesourodireto.com.br (scraping HTML) | `app.modules.market_universe.tasks.refresh_tesouro_rates` | a/6h | OK | Redis `tesouro:rates:*` | 4/d |
| 6 | brapi (earnings) | `analysis.check_earnings_releases` | nightly 22h BRT Mon–Fri | OK | `analysis_jobs` (gatilho assíncrono) | varia |
| 7 | computado | `app.modules.market_universe.tasks.calculate_fii_scores` | diário 08h | OK | `screener_snapshots` (colunas FII score) | 1/d |
| 8 | brapi (top 30 IBOV) | `opportunity_detector.scan_acoes` | a/15min, Mon–Fri 10–17 BRT | OK | `detected_opportunities` + Redis dedup | ~30 scans×24/d |
| 9 | Binance público | `opportunity_detector.scan_crypto` | a/15min 24/7 | OK | `detected_opportunities` + Redis | ~96/d |
| 10 | Tesouro cache | `opportunity_detector.scan_fixed_income` | a/6h | OK | `detected_opportunities` | 4/d |
| 11 | computado (LLM) | `app.modules.insights.tasks.generate_daily_insights` | diário 08h BRT | OK | `user_insights` | varia |
| 12 | Redis quotes | `app.modules.watchlist.tasks.check_price_alerts` | a/15min Mon–Fri 10–17 BRT | OK | `watchlist_items.alert_triggered_at` + email | varia |
| 13 | (housekeeping) | `screener.cleanup_stale_runs` | a/15min | OK | `screener_runs` (delete) | — |
| 14 | (billing) | `app.modules.billing.tasks.check_expiring_trials` | diário 09h BRT | OK | email + `users.trial_warning_sent` | — |
| 15 | computado | `app.modules.dashboard.digest_tasks.send_weekly_digest` | semanal Mon 08h BRT | OK | email | 1/sem |
| 16 | computado | `app.modules.dashboard.tasks.snapshot_portfolio_daily_value` | diário Mon–Fri 18h30 BRT | OK | `portfolio_daily_value` | 1/d |
| 17 | computado (Redis) | `advisor.refresh_universe_entry_signals` | diário 02h BRT | **STALE 19h** | Redis `entry_signals:universe` ([2026-04-AUDIT.md:204](../../.planning/audits/2026-04-AUDIT.md)) | 1/d |

### Tasks não-beat (on-demand)

- `app.modules.imports.tasks` — `parse_pdf_import`, `parse_csv_import` (broker import via `correpy` + `pdfplumber` + GPT-4o fallback) — [imports/tasks.py:1-30](../../backend/app/modules/imports/tasks.py)
- `app.modules.ai.tasks` — `run_dcf`, `run_valuation`, `run_earnings`, `run_macro_impact`, `run_portfolio_advisor` (skills LLM)
- `app.modules.advisor.tasks` — análise IA assíncrona da carteira (Phase 24)
- `app.modules.analysis.tasks` — Phase 12 AI analysis engine
- `app.modules.wizard.tasks` — wizard "Onde Investir" (Phase 11)

### Fontes de dados — vs alvo V2

| Fonte alvo V2 (§3, §21.1) | Estado atual | Decisão |
|---|---|---|
| brapi | ✅ existe | Manter |
| yfinance | ⚠️ adapter existe ([market_data/adapters/yfinance_adapter.py](../../backend/app/modules/market_data/adapters/yfinance_adapter.py)) mas não está em beat | Reservar para US tickers (Fase 5+) |
| BCB | ✅ existe | Manter |
| **ANBIMA** | ❌ **NÃO EXISTE** — D2 confirma premissa errada do V2 | Remover do roadmap; ficar com Tesouro scraping (Fase 1) |
| Tesouro (oficial) | ⚠️ Scraping HTML — funcional mas frágil | Migrar para fonte oficial quando latência importar (red flag P2) |
| python-bcb | ✅ usado dentro do BCB adapter | Manter |
| CVM RSS | ❌ NÃO EXISTE | Adicionar Fase 2 |
| Valor Econômico | ❌ NÃO EXISTE | Adicionar Fase 2 (scraping + RSS) |
| InfoMoney | ❌ NÃO EXISTE | Adicionar Fase 2 |
| MoneyTimes | ❌ NÃO EXISTE | Adicionar Fase 2 |
| Reddit / StockTwits | ❌ NÃO EXISTE | Adicionar Fase 3 |
| Binance | ✅ existe (apenas em opp_detector) | Reusar como Crypto adapter |

---

## §21.2 — Inventário de Schema Atual

29 migrations Alembic (`001` → `0029`), cadeia completa sem gaps ([2026-04-AUDIT.md:185](../../.planning/audits/2026-04-AUDIT.md)). Lista por `__tablename__` extraída de [`backend/app/modules/*/models.py`](../../backend/app/modules):

### Tabelas existentes (28 totais)

| # | Tabela | Módulo | Colunas-chave | Mapeamento V2 (§7) | Migration necessária |
|---|---|---|---|---|---|
| 1 | `users` | auth | id, email, plan, trial_ends_at, stripe_customer_id, subscription_status | mantém | `ALTER` para adicionar `risk_profile`, `kelly_fraction_cap` (Fase 4) |
| 2 | `refresh_tokens` | auth | id, user_id, token_hash, status, expires_at | mantém | nenhuma (mas P2: revogação no Redis — Fase 1) |
| 3 | `verification_tokens` | auth | id, user_id, token_hash, purpose | mantém | nenhuma |
| 4 | `transactions` | portfolio | tenant_id, ticker, asset_class (acao/fii/renda_fixa/bdr/etf), transaction_type (buy/sell/dividend/jscp/amortization), is_exempt, import_hash | **= `positions` do V2 §7** (renome conceitual; tabela física fica) | `ALTER`: adicionar `asset_kind` (V2 §7 quer "stock/unit/fii/etf/bdr/crypto/fixed_income/fund") + `is_fractional` |
| 5 | `corporate_actions` | portfolio | tenant_id, ticker, action_type (desdobramento/grupamento/bonificacao), action_date, factor | **REDUZIDA vs V2 §7** — V2 quer dividend/JCP/split/bonus/subscription + `data_com`/`data_ex`/`payment_date`/`amount_per_share`/`tax_rate` | nova migration: estender enum + colunas |
| 6 | `import_files` | imports | bytes do arquivo, mime, status | mantém | nenhuma |
| 7 | `import_jobs` | imports | tenant_id, file_id, status, parser_used (correpy/csv/xlsx/pdfplumber/gpt4o) | mantém | nenhuma |
| 8 | `import_staging` | imports | rows pré-confirmação | mantém | nenhuma |
| 9 | `ai_analysis_jobs` | ai (legacy) | job assíncrono original | **DEPRECAR** em favor de `analysis_jobs` | drop em Fase 4 (após migração) |
| 10 | `analysis_jobs` | analysis (Phase 12) | tenant_id, ticker, skill, status, result_json | mantém | nenhuma |
| 11 | `analysis_quota_logs` | analysis | tenant_id, period, count | mantém | nenhuma |
| 12 | `analysis_cost_logs` | analysis | tenant_id, provider, model, tokens_in, tokens_out, cost_usd | mantém — **base para custo unitário** | nenhuma |
| 13 | `ai_usage_logs` | ai | tenant_id, provider, model, duration_ms, success | mantém | nenhuma |
| 14 | `app_logs` | logs | level, title, traceback, request_path | **substitui Sentry parcialmente** | nenhuma (Fase 2 adicionar Sentry-as-mirror) |
| 15 | `subscriptions` | billing | user_id, stripe_subscription_id (UNIQUE), plan, status, current_period_end | mantém | nenhuma |
| 16 | `stripe_events` | billing | id (evt_), event_type, status (success/error) — idempotency log | mantém | nenhuma (P3: alerting) |
| 17 | `idempotent_checkout_requests` | billing | idempotency_key (PK), user_id, checkout_url | mantém | P2: TTL via cleanup task |
| 18 | `investor_profiles` | profile | tenant_id, risk_tolerance, horizon | **base do `user_memories.preference` do V2** | nenhuma; Fase 4 adiciona `user_memories` ao redor |
| 19 | `watchlist_items` | watchlist | tenant_id, ticker, price_alert_target, alert_triggered_at | mantém | Fase 4 estender para `signal_alert` (não só preço) |
| 20 | `user_insights` | insights | tenant_id, type, payload, created_at | mantém | Fase 3: ligar a sinais do Decision Engine |
| 21 | `screener_runs` | screener | tenant_id, params, status (sync com cleanup-stale) | mantém | nenhuma |
| 22 | `screener_snapshots` | market_universe | ticker, sector, dy, pl, pvp, market_cap, variacao_12m_pct, fii_score | **= `features` parcial do V2** — agregado pré-calculado | manter; `features` separado para OHLCV-derived (RSI/MACD/etc.) |
| 23 | `fii_metadata` | market_universe | ticker, segment, vacancia, último_dy | mantém | nenhuma |
| 24 | `fixed_income_catalog` | market_universe | tipo (CDB/LCI/LCA/Tesouro), prazo, taxa, emissor | mantém | nenhuma |
| 25 | `tax_config` | market_universe | brackets IR regressivo, isenções FII/LCI/LCA | mantém | nenhuma |
| 26 | `wizard_jobs` | wizard | tenant_id, perfil, status, result | mantém — **reutilizado por `advisor` (Phase 23+)** com discriminator `perfil="advisor"` | nenhuma |
| 27 | `detected_opportunities` | opp_detector | ticker, asset_type, drop_pct, period, cause/fund/risk/rec JSON | **= `signals` do V2 §7 — primeira metade** | Fase 6: unificar com `swing_trade_operations` em `outcomes` (D4) |
| 28 | `swing_trade_operations` | swing_trade | tenant_id, ticker, entry/stop/target, status (open/closed), source (manual/auto) | **= `signals`+`outcomes` do V2 — segunda metade** | Fase 6: unificar (D4) |
| 29 | `portfolio_daily_value` | dashboard | tenant_id, date, total_value | mantém — mas **sem ORM model** (P3 do audit) | Fase 1: criar `PortfolioDailyValue` ORM |

### Tabelas-alvo do V2 §7 que NÃO existem hoje

| Tabela alvo V2 | Propósito | Esforço | Fase |
|---|---|---|---|
| `events` | MarketEvent canônico (news/filing/social/macro) | M | 1 |
| `prices` | OHLCV histórico persistente (hoje só Redis cache) | M | 2 (TimescaleDB hypertable) |
| `features` | RSI/MACD/EMA/ATR/VWAP/BB/regime calculados | M | 2 |
| `signals` | tabela canônica unificando `detected_opportunities` + `swing_trade_operations` (D4) | S | 6 |
| `outcomes` | exits realizados com `is_paper` flag | S | 6 |
| `user_memories` | preference / rejected_setup / winning_pattern / risk_tolerance / thesis_history (pgvector) | M | 4 |
| `ticker_state` | halt / circuit breaker (consultado pelo Quality Gate) | S | 1 |

### Extensões Postgres necessárias

| Extensão | Estado atual | Fase |
|---|---|---|
| `pgcrypto` | ✅ provável (UUID) | — |
| `pg_trgm` | ⚠️ não verificado | — |
| `timescaledb` | ❌ não instalada | 1 |
| `vector` (pgvector) | ❌ não instalada | 1 |

---

## §21.3 — Inventário de Capabilities

Tabela cobrindo as 12 capabilities do V1 §2 + `opportunity_detector` (template do Agent Mesh).
Para mapeamento completo com nomenclatura unificada, ver [`docs/reconciliation/CAPABILITY_MAPPING.md`](../reconciliation/CAPABILITY_MAPPING.md).

| # | V1 ref | Capability alvo | Existe hoje? | Módulo/arquivo | Gap principal |
|---|---|---|---|---|---|
| 1 | §2.1 | Decision Copilot | **Parcial** — análise por ativo (advisor + opp_detector) sem orquestração unificada | [advisor/router.py](../../backend/app/modules/advisor/router.py), [opportunity_detector/analyzer.py](../../backend/app/modules/opportunity_detector/analyzer.py) | Falta `decision_copilot_flow` LangGraph + streaming SSE + Decision Engine determinístico antes do LLM |
| 2 | §2.2 | Análise de carteira (Portfolio Health) | **Existente (shipped)** — Phase 23 D3 | [advisor/service.py:compute_portfolio_health](../../backend/app/modules/advisor/service.py), [ai/skills/portfolio_advisor.py](../../backend/app/modules/ai/skills/portfolio_advisor.py) | Renomear → "Portfolio Agent"; expor como tool do Decision Copilot |
| 3 | §2.3 | Análise de ativo | **Existente (shipped)** — Phase 12 AI Analysis Engine | [analysis/dcf.py](../../backend/app/modules/analysis/dcf.py), [analysis/earnings.py](../../backend/app/modules/analysis/earnings.py), [ai/skills/dcf.py](../../backend/app/modules/ai/skills/dcf.py), [valuation.py](../../backend/app/modules/ai/skills/valuation.py) | Empacotar como tools do Asset Research Agent |
| 4 | §2.4 | Análise de gráfico (Chart Vision) | **Não existe** | — | Tudo (Fase 5) |
| 5 | §2.5 | Notícias do dia | **Não existe** — sem ingestion de news | — | Ingestion (Fase 2) + ranking + digest |
| 6 | §2.6 | Briefing de tema (Theme Briefing) | **Não existe** | — | Tudo (Fase 5) — Tavily + cross-ref carteira |
| 7 | §2.7 | Análise grupo WhatsApp (WhatsApp Scan) | **Não existe** | — | Tudo (Fase 5 — premium Enterprise) |
| 8 | §2.8 | Renda fixa | **Existente (shipped)** — v1.4 RF-01/02/03 + v1.6 Comparador + v1.7 Simulador | [screener_v2/router.py](../../backend/app/modules/screener_v2/router.py), [comparador/service.py](../../backend/app/modules/comparador/service.py), [simulador/service.py](../../backend/app/modules/simulador/service.py) | Renomear → "Fixed Income Agent" — mas **bloqueado em prod** por macro nulls (P0 do audit) |
| 9 | §2.9 | Fundos (FIA/FIM/multimercados) | **Não existe** | — | Tudo (Fase posterior — não MVP) |
| 10 | §2.10 | Alertas | **Existente (shipped)** | [watchlist/router.py](../../backend/app/modules/watchlist/router.py), [watchlist/tasks.py](../../backend/app/modules/watchlist/tasks.py) | Estender triggers de `price_alert_target` → `signal_alert` (Fase 4) |
| 11 | §2.11 | Modo debate (Devil's Advocate) | **Não existe** | — | Cross-model critic — modelo diferente do gerador (Fase 4) |
| 12 | §2.12 | Backtest rápido | **Não existe** | — | Tudo (Fase 6 — gate para dinheiro real) |
| ➕ | — | `opportunity_detector` (Phase 1) | **Existente (shipped)** — D6 confirma | [opportunity_detector/scanner.py](../../backend/app/modules/opportunity_detector/scanner.py) + 4 agents async | **Template do Agent Mesh** — porta para LangGraph na Fase 3 |

---

## §21.4 — Métricas Operacionais Atuais

> Critério V2 §21.4: **não inventar número.** Onde não há instrumentação, marcar explicitamente.

| Métrica | Valor atual | Fonte / Como medido | Status |
|---|---|---|---|
| Eventos ingeridos/dia (canônicos) | **0** | Não há tabela `events` — só Redis cache de cotações | Não instrumentado |
| Cotações refresh/dia | ~480 (8 tickers × 24×4 ciclos) | [market_data/tasks.py:44-53](../../backend/app/modules/market_data/tasks.py) | Estimado por agendamento, não medido |
| Sinais gerados/dia (entry signals universo) | **Desconhecido** | Job grava em Redis sem contador persistido | Não instrumentado |
| Detected opportunities/dia | Variável | `detected_opportunities` cresce via 3 scans | Mensurável (não dashboardado) |
| Usuários ativos | **Desconhecido** | Sem tabela `user_sessions`; sem analytics | Não instrumentado |
| Custo LLM/mês | Parcialmente medido | `analysis_cost_logs` + `ai_usage_logs` agregam por chamada — sem dashboard agregado | Parcialmente instrumentado |
| Custo LLM/usuário/mês | **Desconhecido** | Não há agregação por `tenant_id` em endpoint admin | Não instrumentado |
| Latência p50 endpoints | **Não instrumentada** | Amostra do audit `2026-04-AUDIT.md:78-91`: `/screener/universe` 3.17s; `/advisor/health` 419ms; `/advisor/screener` 482ms; `/portfolio/pnl` 171ms | Amostra única, não p50/p95 contínuo |
| Latência p95 endpoints | Não instrumentada | — | Não instrumentado |
| Uptime últimos 30 dias | **Desconhecido** | Sem health-checker externo (UptimeRobot etc.) | Não instrumentado |
| Cobertura de testes backend | 96% pass rate (620/645) — cobertura % não medida | `pytest`; ver [2026-04-AUDIT.md:23](../../.planning/audits/2026-04-AUDIT.md) | Pass rate medido; cobertura % não |
| Testes backend totais | 645 (620 pass / 18 fail / 7 skip) | 45 arquivos `test_*.py` em `backend/tests/` | Medido |
| Testes frontend unitários | **0** — sem Vitest/Jest configurado | `frontend/package.json` sem `test` script | Não instrumentado |
| E2E Playwright | 16 specs em `frontend/e2e/` | Última execução: 3/3 verified em deploy v1.7 (commit `a0bf332`) | Medido pontualmente, não contínuo |
| Logger calls totais (backend) | 412 | grep `logger\.` em backend ([2026-04-AUDIT.md:299](../../.planning/audits/2026-04-AUDIT.md)) | Medido |

**Decisão Fase 1:** instrumentar latência p50/p95 + custo/`tenant_id`/mês via OpenTelemetry antes de adicionar capabilities premium pagas (Fase 5).

---

## §21.5 — Gaps de Observabilidade

Checklist V2 §21.5:

- [ ] **Logs estruturados com `trace_id`?** — **NÃO.** [`core/logging.py`](../../backend/app/core/logging.py) usa formato JSON em produção mas sem `trace_id` / `request_id` correlacionável. Grep `trace_id` no backend: 0 hits.
- [ ] **Métricas Prometheus expostas?** — **NÃO.** Sem `/metrics` endpoint, sem `prometheus_client` em `requirements.txt`.
- [ ] **Tracing OpenTelemetry?** — **NÃO.** Sem `opentelemetry-*` em `requirements.txt`.
- [ ] **Alertas configurados?** — **NÃO.** Sem PagerDuty/Slack webhook/email-on-error. Único mecanismo é o middleware [`main.py:74-109`](../../backend/app/main.py) que grava 500s na tabela `app_logs` — **sem leitor**.
- [ ] **Dashboards existentes?** — **NÃO.** Sem Grafana, Datadog, NewRelic. `/admin/logs` lê `app_logs` mas é endpoint admin manual ([logs/router.py](../../backend/app/modules/logs/router.py)).
- [ ] **Sentry / APM?** — **NÃO.** Confirmado em [2026-04-AUDIT.md:307-308](../../.planning/audits/2026-04-AUDIT.md). Grep `sentry|opentelemetry|prometheus|otel` no backend: 0 hits.
- [ ] **Frontend ErrorBoundary?** — **NÃO.** Sem `error.tsx` em `frontend/app/`. Erro em componente derruba página inteira ([2026-04-AUDIT.md:325-326](../../.planning/audits/2026-04-AUDIT.md)).
- [ ] **Auth audit trail?** — **NÃO.** [`auth/service.py`](../../backend/app/modules/auth/service.py) tem **0 logger calls** ([2026-04-AUDIT.md:303](../../.planning/audits/2026-04-AUDIT.md)). Login/registro/reset sem trilha.
- [ ] **Erros engolidos?** — **SIM** (problema). [`main.py:107`](../../backend/app/main.py) `except Exception: pass`; [`core/email.py:41,49,108,154`](../../backend/app/core/email.py) idem.

**Decisão Fase 2:** Sentry SDK (FastAPI + Celery integrations) + OpenTelemetry + Grafana Cloud free tier. `trace_id` injetado no middleware + propagado para Celery tasks. Bash `app_logs` → Sentry mirror.

---

## §21.6 — Gaps de Segurança

Checklist V2 §21.6:

- [ ] **Segredos em vault (não `.env` commitado)?** — **PARCIAL.**
  - `.env` está no `.gitignore` ([2026-04-AUDIT.md:117](../../.planning/audits/2026-04-AUDIT.md)) mas `.env.example` registra defaults inseguros.
  - `SECRET_KEY = "change-me-in-production"` no [`core/config.py:13`](../../backend/app/core/config.py) — e literalmente é `"change-me-in-production"` no `.env` de produção (S2 do audit). Embora não usado para assinar nada hoje (JWT é RS256), futuro código que usar `settings.SECRET_KEY` herda valor conhecido.
  - JWT keys carregadas de AWS Secrets Manager *ou* de arquivos `jwt_*.pem` ([`core/security.py:49-78`](../../backend/app/core/security.py)). Migrar para arquivos locais (CLAUDE.md global instrui que AWS SM está descontinuado).
- [ ] **Auth com 2FA?** — **NÃO.** bcrypt + JWT RS256 + email verification + password reset; sem TOTP/WebAuthn/SMS.
- [ ] **Rate limit por usuário?** — **PARCIAL.** [`core/limiter.py`](../../backend/app/core/limiter.py) usa `slowapi` com `get_remote_address` (IP-based). Endpoints sensíveis (checkout) sobrescrevem com chave por user_id ([`billing/router.py:28-36`](../../backend/app/modules/billing/router.py)). **Maioria dos endpoints autenticados ainda é IP-based** — usuários atrás de NAT compartilham bucket.
- [ ] **Logs de auditoria de decisões?** — **NÃO** para auth (S5 do audit). Decisões IA têm trilha em `analysis_jobs.result_json` + `ai_usage_logs` mas **sem trace_id correlacionando** (ver §21.5).
- [ ] **Disclaimer CVM presente em outputs?** — **PARCIAL.**
  - Texto canônico: `"Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"` em [`ai/skills/__init__.py:11-14`](../../backend/app/modules/ai/skills/__init__.py).
  - **V2 §16 quer Res. 20/2021** — **divergência de número**. Confirmar com jurídico.
  - Presente em: `advisor/*`, `ai/skills/*` (todas as 5 skills). Ausente em: `screener_v2`, `simulador`, `comparador`, `wizard` outputs (auditar caso a caso na Fase 1).
- [ ] **CSP / HSTS / X-Frame / X-Content-Type?** — **NÃO** no frontend ([2026-04-AUDIT.md:148-153](../../.planning/audits/2026-04-AUDIT.md)). `frontend/next.config.ts` sem `headers()` callback.
- [ ] **JWT refresh token revogável?** — **NÃO.** Token roubado vale 7 dias mesmo após logout/troca de senha ([2026-04-AUDIT.md:121-127](../../.planning/audits/2026-04-AUDIT.md)).
- [ ] **CORS allow_headers cobre Idempotency-Key?** — **NÃO** ([`main.py:70`](../../backend/app/main.py)). **P0 do audit** — quebra hotfix billing em produção.

**Decisão Fase 1:** corrigir P0/P1 do audit `2026-04-AUDIT.md` (Idempotency-Key, SECRET_KEY, headers Next.js) antes de qualquer feature nova. 2FA fica para Fase 6+ (gate dinheiro real).

---

## §21.7 — Gap Analysis Consolidado

Esforço: S = ≤2 dias, M = 3–7 dias, L = 8–20 dias.
Impacto: 1 = cosmético, 5 = bloqueia visão V2.

| Área | Estado atual | Alvo V2 | Esforço | Impacto | Fase |
|---|---|---|---|---|---|
| Schema canônico de eventos (`events`) | ❌ inexistente | V2 §6-7 com Pydantic v2 | M | 5 | 1 |
| Decision Engine determinístico (gates + Kelly) | Parcial — lógica espalhada em `opportunity_detector/agents/risk.py` + `recommendation.py` | Módulo Python puro `decision_engine/` testável isoladamente, ≥90% cobertura | M | 5 | 1 |
| Tabela `outcomes` + paper trading flag | Parcial via `swing_trade_operations` + `detected_opportunities` (D4) | Tabela canônica com `is_paper`, tracker que fecha automaticamente | S | 5 | 6 |
| Tabela `signals` canônica | Parcial via duas tabelas legadas (D4) | Unificar; FK para `outcomes` | S | 4 | 6 |
| `prices` hypertable | ❌ só Redis cache | TimescaleDB hypertable persistente | M | 3 | 2 |
| `features` (RSI/MACD/etc.) | ❌ inexistente | TimescaleDB hypertable + cálculo no ingestion | M | 4 | 2 |
| `user_memories` + retrieval | ❌ inexistente (parcial via `investor_profiles`) | pgvector + 5 tipos (preference/rejected/winning/risk/thesis) | M | 3 | 4 |
| `ticker_state` (halt) | ❌ inexistente | tabela + consulta no Quality Gate | S | 4 | 1 |
| `corporate_actions` estendida | Reduzida (só split/grup/bonif) | + dividend/JCP/subscription + data_com/data_ex/payment_date/amount/tax_rate | S | 3 | 1 |
| Dedup semântico de news | ❌ não há news | pgvector cosine > 0.92 | M | 4 | 2 |
| Extensão TimescaleDB | ❌ não instalada | hypertables `events`/`prices`/`features` | S | 3 | 1 |
| Extensão pgvector | ❌ não instalada | embeddings in-DB | S | 4 | 1 |
| Ingestion BR-first (CVM/Valor/InfoMoney/MoneyTimes) | ❌ inexistente | 5 Celery tasks novas | L | 4 | 2 |
| Classificador Haiku batch (Anthropic Batch API) | ❌ inexistente | a/15min, ≥500 eventos/d com confidence>0.7 | M | 4 | 2 |
| OpenTelemetry + Sentry | ❌ inexistente | trace_id end-to-end + Grafana free | M | 4 | 2 |
| LangGraph Python orquestração | ❌ inexistente | spike vs Pydantic AI (ADR-002), depois flow `decision_copilot_flow` | M | 4 | 3 (após spike Fase 2) |
| Devil's Advocate cross-model | ❌ inexistente | modelo diferente do gerador; degrada BUY→WAIT em ≥10% | S | 4 | 4 |
| Streaming SSE no FastAPI para chat | ❌ inexistente | endpoint `POST /api/decide` com SSE | S | 3 | 3 |
| Chart Vision Agent | ❌ inexistente | screenshot → ticker + timeframe ≥80% acerto | L | 3 | 5 |
| Theme Briefing Agent | ❌ inexistente | Tavily + Opus + cross-ref carteira | M | 3 | 5 |
| WhatsApp Scan Agent | ❌ inexistente | extract tickers + pump&dump detection | M | 2 | 5 (Enterprise) |
| Backtester | ❌ inexistente | janelas históricas | L | 4 | 6 |
| Kill switch global | ❌ inexistente | hard-coded loss limit diário | S | 5 | 6 |
| Staging environment + CI | ❌ inexistente (D6) | GitHub Actions + ambiente staging isolado | M | 4 | 2 |
| RLS revisão de tenant_id | ✅ existe ([`core/db.py:44`](../../backend/app/core/db.py)) — risco menor de SQL injection (S7 do audit) | bindparams parametrizado | S | 2 | 1 |
| `stripe_events` alerting | ✅ tabela existe; **sem alerta** (S8) | dashboard + webhook on `status="error"` | S | 2 | 2 |
| Frontend security headers | ❌ inexistente | CSP/HSTS/X-Frame/X-Content-Type (P1-2) | S | 3 | 1 |
| Frontend ErrorBoundary | ❌ inexistente | `error.tsx` em segments principais (P1-4) | S | 3 | 1 |
| `typescript: ignoreBuildErrors: true` | ❌ silencia erros em prod (P1-3) | desligar; corrigir erros expostos | S | 3 | 1 |

---

## §21.8 — Red Flags de Risco (ordenados por severidade)

> O que pode causar **perda de capital / dados / reputação** se ficar como está.

### P0 — Bloqueia v1.8 / risco financeiro imediato

1. **Macro rates null em produção (CDI/IPCA/SELIC).** [`refresh_macro` task nunca rodou com sucesso ou Redis foi limpo](../../.planning/audits/2026-04-AUDIT.md). Comparador RF×RV (v1.6) e Simulador (v1.7) servem benchmarks `null`. Usuário pode tomar decisão financeira com preview falsamente neutro. **Fix: D6 quick win #2**.
2. **CORS bloqueia `Idempotency-Key`.** [`main.py:70`](../../backend/app/main.py) — hotfix billing duplicate-subscriptions (migration 0029) é **silenciosamente não-funcional** em prod. Risco real de cobrança duplicada Stripe. **Fix: D6 quick win #1**.

### P1 — Risco operacional / reputacional

3. **Sem ambiente de staging (D6).** Todo deploy é teste em produção. Bug de regressão impacta usuários reais antes de detectar. Inexiste GitHub Actions, inexiste pipeline de validação automática.
4. **`SECRET_KEY = "change-me-in-production"` no `.env` de produção.** Mesmo não usado hoje, qualquer código futuro que importar `settings.SECRET_KEY` herda valor conhecido publicamente em git.
5. **JWT refresh token sem revogação.** Token roubado vale 7 dias. Usuário trocando senha não invalida sessões antigas.
6. **Sem APM/Sentry/OTel.** Incidentes invisíveis até usuário reclamar. `app_logs` table escreve mas não tem leitor automático.
7. **`typescript: ignoreBuildErrors: true` em [`frontend/next.config.ts`](../../frontend/next.config.ts).** Type errors silenciados em build de produção.
8. **Sem React `ErrorBoundary`.** Erro de runtime em qualquer componente derruba página inteira.

### P2 — Tech debt acumulando

9. **ANBIMA citada no V2 não existe; Tesouro Direto via scraping HTML.** Frágil para escalar; quebra silenciosamente em mudança de layout.
10. **`portfolio_daily_value` sem ORM model.** Schema só em migration; quebra 2 testes do dashboard; SQLAlchemy não gerencia.
11. **18 testes falhando** (620/645) — em sua maioria stale patches em `test_phase12_foundation.py`. Cobertura efetiva caindo silenciosamente.
12. **Sync Redis em contexto async** (advisor service) — bloqueia event loop sob carga.
13. **`advisor/screener` `limit` sem teto** ([`router.py:230`](../../backend/app/modules/advisor/router.py)) — risco DoS via `limit=999999`.
14. **`idempotent_checkout_requests` sem TTL** — rows acumulam indefinidamente.

### P3 — Cosmético / documentado

15. FastAPI `regex=` deprecado em 2 routers.
16. `datetime.utcnow()` deprecado em 2 arquivos.
17. `allow_methods` inclui `PUT` não usado.

### Red flags de data quality descobertos pelo Inbox v1 (deploy 19/04/2026)

- **P0 (herdado):** Macro rates zerados em produção (CDI/IPCA/SELIC = 0.00 no banner do dashboard). Celery beat `refresh_macro` não roda ou Redis vazio. Impacto: banner dashboard, qualquer cálculo que dependa de taxas de referência. Evidência: validação prod 19/04/2026. **Resolução:** Fase 2 (ingestion consolidation).

- **P0 (herdado):** `data_stale=true` persistente em `GET /dashboard/summary`. Cotações desatualizadas. Mesma raiz do item anterior — scheduler Celery. **Resolução:** Fase 2.

- **P2 (descoberto via Inbox):** Enrichment de `screener_snapshots.sector` incompleto. Tickers sem mapeamento caem em fallback `"Outros"`. Impacto: análise de concentração sectorial do Portfolio Health Check gera cards com semântica degradada (`"88% em Outros"` em vez de `"88% em Financeiro"`). Arquivo: [`advisor/service.py:142`](../../backend/app/modules/advisor/service.py). **Resolução:** Fase 3 (data quality pass no Asset Research Agent).

- **P3 (herdado):** Orphan `frontend/src/features/advisor/hooks/useAdvisorJob.ts` resolvido na Tarefa 2 deste ciclo (arquivo deletado, era untracked desde sempre).

---

## §21.9 — Quick Wins (≤5 itens, 1–3 dias cada)

Priorizados por *impacto destravado* ÷ *tempo*. Todos são **independentes** (não bloqueiam um ao outro).

| # | Quick Win | Tempo | Impacto destravado |
|---|---|---|---|
| 1 | **Adicionar `"Idempotency-Key"` em [`main.py:70`](../../backend/app/main.py) `allow_headers`** + redeploy backend. | 30min | P0-1 — destrava hotfix duplicate-subscriptions em prod (R$ direto em risco) |
| 2 | **Force-run `refresh_macro` no VPS + verificar Celery beat ativo + redeploy backend** (precisa para o response incluir field `selic`). | 2–3h | P0-2 — destrava Comparador (v1.6) e Simulador (v1.7) em prod |
| 3 | **Rodar Decision Engine sintético com dados históricos do `screener_snapshots`** — validar gates + Kelly bootstrap em ~3 dias sem ingestion nova (V2 §17 Fase 1 quick win literal). | 2–3 dias | Valida Fase 1 do V2 antes de migration nova; gera 20 casos de teste determinísticos |
| 4 | **Headers de segurança em [`frontend/next.config.ts`](../../frontend/next.config.ts)** (CSP/HSTS/X-Frame/X-Content-Type) + desligar `typescript: ignoreBuildErrors`. | 1 dia | P1-2 + P1-3 do audit |
| 5 | **Mover `refresh-universe-entry-signals-daily` de 02h BRT → 08h30 BRT** ([`celery_app.py:163-167`](../../backend/app/celery_app.py)) — sinais deixam de ser 19h stale. | 5min código + verificação prod | P2-3 do audit; melhora qualidade de signals do `/advisor/signals/universe` |

**Não-quick-wins (≥1 semana — entram na Fase 1 formal):**
- Decision Engine completo testado.
- pgvector + TimescaleDB extensions.
- Tabelas `events`/`prices`/`features`/`signals`/`outcomes`/`user_memories`/`ticker_state`.
- Sentry + OpenTelemetry + Grafana.

---

## Próximos passos pós-Fase 0

1. **Reconciliar este audit com o usuário.** Confirmar §21.4 numbers que marquei "Não instrumentado" — dado o D8 quer pricing parametrizado, custo LLM/usuário/mês precisa virar dashboard antes de capabilities premium.
2. **ADR-001 e ADR-002** congelam decisões de stack (este PR).
3. **Renomeação no repo** — mapeamento "v1.5 M1/M2/M3/M4" → nomes Agent Mesh fica em [`docs/reconciliation/CAPABILITY_MAPPING.md`](../reconciliation/CAPABILITY_MAPPING.md). Renomeação física dos módulos é **Fase 1 task**, não Fase 0.
4. **Fase 1 inicia** após este PR mergear + 5 quick wins acima aplicados.

---

**Autor:** Claude Code (Sonnet 4.6) executando Fase 0 do `INVESTIQ_UPGRADE_PLAN_V2.md`.
**Revisor pendente:** Alexandre Queiroz (`xandeq@gmail.com`).
