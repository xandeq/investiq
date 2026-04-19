# ADR-002 — Orquestração de Agentes: LangGraph Python vs Pydantic AI

- **Status:** Accepted
- **Date:** 2026-04-19
- **Decision deadline:** antes do início da Fase 2 do `INVESTIQ_UPGRADE_PLAN_V2.md`
- **Decision authors:** Alexandre Queiroz (final call), Claude Code (spike runner)
- **Related:** ADR-001 (stack-freeze: linguagem é Python)

## Contexto

ADR-001 congelou que **a orquestração de agentes será em Python** (não Node/TS/Mastra). Resta escolher a biblioteca:

- **LangGraph Python** (LangChain, ~Mar 2024 GA; 2026: estável, ecossistema grande)
- **Pydantic AI** (Pydantic team, lançado mid-2024; 2026: mais novo, mais enxuto, schema-first)

O `INVESTIQ_UPGRADE_PLAN_V2.md` §4 dá preferência a LangGraph mas explicita: *"Alternativa para avaliação: Pydantic AI — mais novo e enxuto; avaliar em spike de 1-2 dias na Fase 2 antes de congelar"*.

A escolha afeta os 11 agentes do Agent Mesh (V2 §3) e os 5 fluxos principais (`decision_copilot_flow`, `ticker_analysis_flow`, `theme_briefing_flow`, `chart_vision_flow`, `whatsapp_scan_flow`).

O `opportunity_detector` atual ([`backend/app/modules/opportunity_detector/`](../../backend/app/modules/opportunity_detector)) implementa um padrão 4-agent **sem** framework de orquestração — pipeline sequencial em [`analyzer.py:98-172`](../../backend/app/modules/opportunity_detector/analyzer.py). Funciona para 1 fluxo simples; **não escala** para state machines com retry/branch/persist.

## Decisão

**Adiada até spike concluído.** Status: *Proposed*.

A spike abaixo deve produzir uma decisão (`Accepted` para uma das opções) **antes de qualquer linha de código LangGraph/Pydantic AI ser escrita em produção**.

## Critérios de avaliação

| # | Critério | Peso | Como medir |
|---|---|---|---|
| 1 | **State persistence** entre passos do fluxo (retomar após crash do worker) | Alto | Há checkpointer nativo? Backend Postgres/Redis suportado? Latência de checkpoint? |
| 2 | **Retry e branching condicional** (ex.: "se Devil's Advocate degrada → re-rota") | Alto | API expressiva? Loops/condições/parallel branches? |
| 3 | **Observabilidade out-of-the-box** | Alto | Hooks/callbacks pra emitir spans OTel? Tracing por step? |
| 4 | **Schema-first input/output (Pydantic v2)** | Médio | Tipos fortes em cada step; integração nativa com FastAPI? |
| 5 | **Maturidade / documentação Python** | Médio | Última release < 60 dias? Issues/PRs ativos? Exemplos production-grade? |
| 6 | **Curva de aprendizado** | Médio | Tempo para reproduzir o pipeline 4-agent do `opportunity_detector` |
| 7 | **Footprint de dependências** | Baixo | `pip install` quanto puxa? Conflito com SDK Anthropic/OpenAI/Voyage atuais? |
| 8 | **Streaming SSE compatível com FastAPI** | Alto | Cada step emite chunk parcial pro chat? |
| 9 | **Custo operacional** (memória do worker, latência por step) | Médio | Benchmark do mesmo flow em ambos |
| 10 | **Lock-in / saída** | Baixo | Quão fácil migrar pra outra opção depois? |

**Peso resumido:** Alto = bloqueia; Médio = influencia; Baixo = tiebreaker.

## Plano de spike (2 dias úteis)

### Dia 1 — Reproduzir o pipeline 4-agent atual em ambas as libs

- **Branch:** `spike/orchestration-langgraph-vs-pydantic-ai` (não merge — só comparação)
- **Tarefa:** Portar o fluxo do [`opportunity_detector/analyzer.py:run_analysis()`](../../backend/app/modules/opportunity_detector/analyzer.py) para:
  - **Versão A:** LangGraph Python — state machine com 4 nós (`cause`, `fundamentals`, `risk`, `recommendation` condicional)
  - **Versão B:** Pydantic AI — 4 agents tipados, orquestração via simple Python `async`
- **Output esperado:** mesmo `OpportunityReport` com mesmo conteúdo (validar com 5 fixtures determinísticos do scanner real)
- **Métricas a coletar:**
  - LOC (linhas de código de orquestração, fora dos prompts)
  - Latência mediana por flow (5 runs cada)
  - Tokens consumidos (devem ser iguais — sanity check)

### Dia 2 — Testar features avançadas que o opportunity_detector ainda não tem

Cada teste deve responder S/N:

- [ ] **State persistence:** matar o worker entre `cause` e `fundamentals`, reiniciar, fluxo retoma do ponto?
- [ ] **Retry com backoff:** `risk` falha 2x na chamada LLM, succeeds na 3ª — fluxo prossegue sem perder contexto?
- [ ] **Branching condicional:** `recommendation` só roda se `risk.is_opportunity == True` (já existe no padrão atual — validar que a lib expressa nativamente)
- [ ] **Devil's Advocate hook:** após `recommendation`, chamar critic em modelo diferente; se crítica grave, degradar BUY→WAIT
- [ ] **Streaming SSE:** cada step emite um chunk pro chat client (`data: {"step": "cause", "status": "done", "preview": "..."}\n\n`)
- [ ] **OTel spans:** cada step gera span com `trace_id` correlacionável em Grafana
- [ ] **Schema validation:** input do flow é Pydantic; output é Pydantic; mismatch falha imediatamente

### Critérios de "**ACCEPTED**" para uma das opções

A spike emite uma das três conclusões:

1. **LangGraph wins** — se ≥7 dos 10 critérios pesam pra LangGraph (incluindo todos de peso Alto)
2. **Pydantic AI wins** — mesmo critério reverso
3. **Empate técnico** — se nem (1) nem (2): default para **LangGraph** (V2 §4 já dá preferência; ecossistema maior reduz risco de bus factor)

## Critério de congelamento da decisão

A decisão é congelada (esta ADR vira `Accepted`) **somente se**:

- [ ] Spike concluído com relatório anexado a esta ADR (nova seção "Spike Results")
- [ ] Fluxo de `opportunity_detector` reproduzido em ambas as libs com mesmo output
- [ ] Métricas das 7 features avançadas coletadas
- [ ] Decisão revisada por 1 segundo par (idealmente outro engenheiro Python sênior; aceitamos LLM-as-reviewer com prompt estruturado se humano não disponível)
- [ ] PR de **re-abertura desta ADR** mergeado com status atualizado

**Sem todos esses checks, ADR-002 permanece `Proposed` e a Fase 2 do roadmap não inicia o trabalho de orquestração.**

## Consequências antecipadas

### Se LangGraph for escolhido

- **Positivo:** ecossistema LangChain (tools, retrievers, callbacks) reaproveitável; comunidade grande; checkpointers Postgres/Redis prontos.
- **Negativo:** dependência pesada (puxa LangChain core + deps); state machine API verbose; histórico de breaking changes em minor versions.
- **Mitigação:** pinar versão exata em `requirements.txt`; documentar API usada em ADR de follow-up.

### Se Pydantic AI for escolhido

- **Positivo:** schema-first (alinha com FastAPI/Pydantic v2 já em uso); footprint menor; API mais limpa.
- **Negativo:** mais novo (menos exemplos production-grade); checkpointing pode ser DIY; ecossistema menor.
- **Mitigação:** se faltar feature crítica, escrever wrapper ad-hoc em Python (já é a abordagem atual sem framework).

### Se ambas forem rejeitadas (decisão "fica como está — Python puro")

- **Positivo:** zero nova dependência; padrão `opportunity_detector` já provado em prod.
- **Negativo:** state persistence, retry inteligente, branching expressivo — tudo DIY. Não escala para 5 flows.
- **Decisão:** essa opção **só é aceita** se ambos os spikes mostrarem perda > 30% de produtividade vs Python puro — o que é improvável.

## Não fazer (V2 §19 — aplicável a esta decisão)

- ❌ Trazer Mastra (TS) ou outra opção em outra linguagem — ADR-001 fechou Python.
- ❌ Adotar **ambas** as libs — fragmenta padrão; inviabiliza onboarding.
- ❌ Pular a spike e ir direto pra LangGraph — premissa "ecossistema maior" sem benchmark é justamente o tipo de erro que motivou ADR-001.
- ❌ Estender spike além de 2 dias — se nem em 2 dias dá pra decidir, default LangGraph e seguir.

## Próximos passos

1. Mergear este PR (`chore(audit): phase 0 — audit & reconciliation`) com ADR-002 em `Proposed`.
2. Executar Fase 1 do V2 (Decision Engine + schema canônico) — **não depende desta ADR**.
3. Antes do início da Fase 2: agendar 2 dias para spike conforme plano acima.
4. Atualizar esta ADR para `Accepted` com seção "Spike Results" e decisão final.

---

## Decision

**Accepted — 2026-04-19**

LangGraph Python selecionado como orquestrador do Agent Mesh do
InvestIQ V2.

## Evidence

Spike executado em branch `spike/adr-002` (commit
`b4b095e5b270eae6d139bd3c392d8aad121ebb87`).

Resultado quantitativo da avaliação ponderada em 11 critérios:

| Biblioteca | Score ponderado |
|---|---|
| LangGraph | 7.69 |
| Pydantic AI | 6.67 |

Relatório completo em
[`spike/adr-002:spike/SPIKE_RESULTS.md`](../../../../tree/spike/adr-002/spike/SPIKE_RESULTS.md).

### Critérios decisivos

**C1 — State persistence (peso 15%)**
- LangGraph: `MemorySaver` → `AsyncPostgresSaver` requer ~5 linhas
  de config e zero mudanças na camada de aplicação.
- Pydantic AI: serialização/deserialização manual do state a cada
  checkpoint, ~15+ linhas intrusivas em todos os steps resumíveis.

**C5 — SSE streaming (peso 10%)**
- LangGraph: `astream_events(version="v2")` emite eventos conforme
  nós paralelos individuais completam.
- Pydantic AI: `asyncio.gather()` bloqueia até todos os branches
  paralelos terminarem antes de emitir qualquer evento. Usuário
  não vê nada durante a fase de research.

### Onde Pydantic AI venceu

- Dependency footprint menor: 4.5 MB vs 9 MB
- Type safety mais forte: `Agent[Deps, Output]` vs
  `TypedDict` + `dict[str, Any]`
- Curva de aprendizado mais rasa

Trade-offs aceitos ao escolher LangGraph (ver abaixo).

## Trade-offs accepted

1. **Dependency footprint 2× maior.** Aceitável no VPS Hetzner
   atual. Revisar se footprint virar restrição real.

2. **Type safety mais fraca que Pydantic AI.**
   Mitigação: inputs e outputs de cada nó são Pydantic models do
   domínio. State interno como TypedDict é aceitável — fica
   confinado a `backend/app/orchestration/`.

3. **Curva de aprendizado mais íngreme.**
   Custo pago uma vez. Primeiro fluxo real (`decision_copilot_flow`
   na Fase 1) documenta padrões pros próximos.

## Architectural guardrails

Para manter custo de reversão baixo caso LangGraph introduza
breaking change major ou apareça alternativa superior:

1. **Agentes são funções async Python puras**, não classes que
   herdam de LangGraph.
2. **State dos fluxos é TypedDict local** ao módulo do fluxo, não
   exportado pra camada de negócio.
3. **Inputs/outputs de cada nó são Pydantic models do domínio**
   (não tipos LangGraph).
4. **Imports de `langgraph` confinados a
   `backend/app/orchestration/`.** Código de negócio em
   `backend/app/modules/` não importa LangGraph direto.

Custo estimado de migrar fora de LangGraph em 12 meses se
API mudar radicalmente, respeitando os guardrails acima:
**~1-2 semanas.**

## Review triggers

Reabrir esta decisão se:

- LangGraph introduzir breaking change major que quebre
  `AsyncPostgresSaver` ou `astream_events`.
- Aparecer biblioteca com state persistence + streaming
  equivalentes e tipagem mais forte (ex: Pydantic AI evoluir
  C1 e C5 nos próximos 12 meses).
- Footprint de 9 MB virar restrição real de deploy.

## Status history

| Data | Status | Commit |
|---|---|---|
| 2026-04-19 | Proposed | `b00e432` |
| 2026-04-19 | Accepted | `4d84992` |
