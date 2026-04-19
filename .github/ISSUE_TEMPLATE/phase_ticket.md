---
name: Fase do Roadmap V2
about: Ticket de fase do `INVESTIQ_UPGRADE_PLAN_V2.md`. Cada PR de fase deve passar por todos os 12 gates do checklist.
title: "[Fase X.Y] <título>"
labels: ["roadmap-v2"]
assignees: []
---

## Contexto

> Fase do `INVESTIQ_UPGRADE_PLAN_V2.md` §17. Linkar para o ADR ou audit que originou esta fase, se houver.

- **Fase / sub-fase:** `Fase X.Y`
- **Plano de origem:** `INVESTIQ_UPGRADE_PLAN_V2.md` §17 — Fase X
- **Audit de referência:** [`docs/audit/PHASE_0_AUDIT.md`](../../docs/audit/PHASE_0_AUDIT.md) (§ relevante)
- **ADRs aplicáveis:** ADR-001 (stack-freeze), ADR-002 (orquestração), demais
- **Capability afetada:** ver [`docs/reconciliation/CAPABILITY_MAPPING.md`](../../docs/reconciliation/CAPABILITY_MAPPING.md)

## Objetivo (1 frase)

> Entregar `<entregável-âncora mensurável>` que destrava `<próxima fase ou métrica>`.

## Entregáveis

- [ ] Entregável 1 (concreto, observável — endpoint, dashboard, métrica)
- [ ] Entregável 2
- [ ] ...

## Critério de aceite

> Reflete o gate da fase em V2 §17. Sem este critério atendido, a fase NÃO está completa.

- [ ] Gate técnico (ex.: `pytest decision_engine/` ≥ 90% cobertura)
- [ ] Gate operacional (ex.: dashboard mostra métrica X)
- [ ] Gate de produto (ex.: query Y retorna em ≤Z s)

---

## ✅ Checklist obrigatório de gates de PR (12 itens — D7)

> **Origem:** decisão D7 da Fase 0 do `INVESTIQ_UPGRADE_PLAN_V2.md`.
> Todos os 12 itens devem estar marcados antes de mergear. Itens N/A devem ser marcados com `~~strikethrough~~` + 1 linha de justificativa.

### Testes e qualidade de código

- [ ] **Testes unitários** dos módulos críticos (decision engine, Kelly, dedup) — *cobertura linha-a-linha das regras determinísticas*
- [ ] **Testes de integração dos agentes** (mock de APIs externas — Anthropic/OpenAI/brapi/BCB)
- [ ] **Cobertura de teste ≥ 80%** nos módulos novos/alterados — *medir com `pytest --cov` no escopo do PR*
- [ ] **Linter + type check verdes** — `ruff check` + `mypy` (backend), `next lint` + `tsc --noEmit` (frontend)

### Operação

- [ ] **Dashboards/alertas atualizados** se métricas mudaram — Grafana / Sentry / `app_logs` filter
- [ ] **`.env.example` atualizado** se vars novas — sem valores reais; placeholders descritivos
- [ ] **Migration SQL idempotente (Alembic)** — `upgrade()` e `downgrade()` reversíveis; rodada em DB local antes do PR
- [ ] **Métricas OpenTelemetry emitidas com `trace_id` correlacionável** — span por step do flow; propagação para Celery via `apply_async(headers=...)`

### Custo e risco

- [ ] **Custo LLM estimado do fluxo documentado** — `tokens × modelo × chamadas/request` no PR description; somar ao [`TIER_MATRIX.md`](../../docs/reconciliation/TIER_MATRIX.md) se capability nova
- [ ] **Disclaimer CVM Res. 20/2021 presente em outputs** que chegam ao usuário final — texto canônico em [`ai/skills/__init__.py`](../../backend/app/modules/ai/skills/__init__.py); aplicar via Pydantic field obrigatório

### Documentação

- [ ] **Documentação do endpoint/fluxo alterado** — OpenAPI auto-gerado deve refletir a mudança; README do módulo atualizado se contrato externo mudou
- [ ] **ADR criado/atualizado** se houve decisão arquitetural — em [`docs/adr/ADR-NNN-<slug>.md`](../../docs/adr/) com status `Accepted` ou `Proposed`

---

## Resumo de impacto (preencher antes de marcar "Ready for review")

### Custo

- **LLM/request estimado:** $X.XX (modelo × tokens)
- **LLM/usuário/mês estimado para o tier afetado:** $X.XX (linkar atualização do TIER_MATRIX)
- **Infra:** novo recurso? (R2 bucket / Redis key namespace / Postgres extensão)

### Risco

- **Reversibilidade:** migration tem `downgrade()` testado? Quanto tempo para rollback?
- **Blast radius:** afeta tenants existentes? Quantos? Como degrada graciosamente se falhar?
- **Dependência externa:** novo provider (Anthropic/Voyage/Tavily)? SLA conhecido?

### Observabilidade

- **Spans novos emitidos:** `<flow_name>.<step>`
- **Métricas novas:** `investiq_<capability>_<metric>_total{tier=...}`
- **Logs estruturados:** entries com `trace_id` para depurar incidentes

---

## Plano de rollout

- [ ] **Feature flag?** se sim, qual e default = `OFF`
- [ ] **Smoke test em staging** (quando staging existir — ver red flag P1 em [`PHASE_0_AUDIT.md` §21.8](../../docs/audit/PHASE_0_AUDIT.md#218--red-flags-de-risco-ordenados-por-severidade))
- [ ] **Deploy plan:** ordem de deploy (backend → frontend ou vice-versa); janela; rollback steps
- [ ] **Monitoramento pós-deploy:** quais métricas vou olhar nas 1h, 24h, 7d seguintes?

---

## Lista do que NÃO vai junto neste PR (V2 §19 + ADR-001)

> Auto-disciplina: marcar o que **não** entra para evitar scope creep.

- [ ] Sem reescrita de stack (ADR-001)
- [ ] Sem novo provider LLM além dos congelados (ADR-001 §LLMs)
- [ ] Sem nova dependência heavy (LangChain/LangGraph só após ADR-002 `Accepted`)
- [ ] Sem novo serviço externo pago sem aprovação (ver V2 §4 corte de Benzinga/Polygon/etc.)
- [ ] Sem feature flag permanente (toda flag tem data de morte no PR description)

---

## Comentário do revisor (obrigatório antes de merge)

> Revisor confirma:
> 1. Os 12 gates do D7 estão marcados ou justificados;
> 2. O PR description tem custo + risco + observabilidade preenchidos;
> 3. O critério de aceite da fase é atendido **com evidência** (link, screenshot, test report).

cc @xandeq
