# Phase 22: Catálogo Renda Fixa - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Adicionar filtros inline (tipo + prazo mínimo), sort por retorno líquido e indicador CDI/IPCA à página `/renda-fixa` já existente. A página, o componente `RendaFixaContent`, os endpoints `GET /renda-fixa/catalog` e `GET /renda-fixa/tesouro`, e os schemas Pydantic já estão todos implementados e funcionando. Phase 22 é **quase 100% frontend** — pequeno ajuste no backend para expor CDI/IPCA rate via endpoint.

</domain>

<decisions>
## Implementation Decisions

### Filtros — inline useMemo, sem botão de aplicar

- **D-01:** Filtros inline/instant: atualizam a tabela ao clicar/digitar, sem botão "Aplicar" — mesmo padrão do Phase 21 (AcoesUniverseContent useMemo)
- **D-02:** Filtro de tipo: botões toggle (Todos | Tesouro | CDB | LCI | LCA) — não dropdown
- **D-03:** Filtro de prazo mínimo: input numérico em meses (ex: "12" para ≥12 meses) — filtra por `min_months >= valor`
- **D-04:** Implementar como extensão do `RendaFixaContent.tsx` existente — não criar novo componente ou feature dir

### Sort por retorno líquido

- **D-05:** Sort por coluna de retorno líquido (net_pct) aplicado a um prazo selecionado — o usuário escolhe o prazo (6m | 1a | 2a | 5a) e a tabela ordena por esse net_pct
- **D-06:** Prazo de ordenação selecionável via tabs ou botões de prazo — estado local `selectedPrazo` controla qual coluna é referência para sort
- **D-07:** Sort via `useMemo` sobre os dados já carregados — sem chamada adicional ao backend

### Indicador CDI/IPCA (beat indicator)

- **D-08:** CDI e IPCA disponíveis em `market:macro:cdi` e `market:macro:ipca` no Redis — já populados pelo python-bcb Celery beat
- **D-09:** Criar endpoint `GET /renda-fixa/macro-rates` que lê `market:macro:cdi` e `market:macro:ipca` do Redis e retorna `{cdi: "10.65", ipca: "5.06"}` — mesmo padrão de `query_tesouro_rates()` em `service.py`
- **D-10:** No frontend, buscar macro rates via `useQuery` com staleTime longo (1h) — chamada leve, dados raramente mudam
- **D-11:** Para cada célula de retorno líquido: mostrar ícone verde ✓ se `net_pct > cdi_anualizado_para_prazo` OU `net_pct > ipca_anualizado_para_prazo` — exibir qual benchmark supera (CDI ou IPCA ou ambos)
- **D-12:** LCI/LCA com `is_exempt: true` têm badge "Isento IR" já implementado — manter, não alterar

### Prazos — manter "6m" (não corrigir para "90d")

- **D-13:** Labels de prazo permanecem: `6m | 1a | 2a | 5a` — "6 meses" faz mais sentido financeiro que "90 dias" para IR regressivo. Não alterar o existing `ir_breakdowns` period_label

### Claude's Discretion

- Layout exato do filtro bar (acima da tabela, card separado, ou linha inline)
- Ícone específico para o beat indicator (✓ verde / ✗ vermelho ou texto "bate CDI" / "abaixo CDI")
- Empty state quando nenhum produto passa no filtro
- Skeleton/loading enquanto macro rates carregam

</decisions>

<specifics>
## Specific Ideas

- Filtros de tipo como botões toggle (`Todos | Tesouro | CDB | LCI | LCA`) ficam visualmente próximos à tabela — padrão já estabelecido no FII screener para segmentos
- O prazo selecionado para sort pode funcionar também como destaque visual da coluna ativa (fundo levemente colorido ou bold no header)
- Beat indicator simples: célula verde se bate CDI, laranja se bate só IPCA, cinza se não bate nenhum

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Componente existente a modificar
- `frontend/src/features/screener_v2/components/RendaFixaContent.tsx` — implementação atual completa (filtros e sort a adicionar aqui, não em novo arquivo)
- `frontend/src/features/screener_v2/hooks/useRendaFixa.ts` — hooks existentes `useFixedIncomeCatalog`, `useTesouroRates` — adicionar `useMacroRates` aqui
- `frontend/src/features/screener_v2/types.ts` — tipos existentes `FixedIncomeCatalogRow`, `TesouroRateRow` — adicionar `MacroRatesResponse` aqui
- `frontend/app/renda-fixa/page.tsx` — página existente (NÃO modificar — apenas o componente muda)

### Backend a estender
- `backend/app/modules/screener_v2/router.py` — adicionar `GET /renda-fixa/macro-rates` aqui (router já montado em `/renda-fixa` no main.py)
- `backend/app/modules/screener_v2/service.py` — adicionar `query_macro_rates()` seguindo padrão de `query_tesouro_rates()`
- `backend/app/modules/screener_v2/schemas.py` — adicionar `MacroRatesResponse` Pydantic schema
- `backend/app/modules/comparador/service.py` — referência para leitura de `market:macro:cdi` do Redis (linha 55)

### Padrão de sort/filter useMemo
- `frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx` — Phase 21 useMemo + sort por coluna + filtros inline — padrão a replicar

### Dados e estrutura
- `backend/app/modules/market_data/schemas.py` — `MacroIndicators` schema com campos `cdi`, `ipca` (Redis keys `market:macro:cdi`, `market:macro:ipca`)
- `backend/app/modules/market_universe/models.py` — `FixedIncomeCatalog` model para referência dos campos

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `typeBadge(type)` em `RendaFixaContent.tsx` — badge colorido CDB/LCI/LCA — manter
- `IRBadge({ is_exempt, ir_rate_pct })` — badge "Isento" para LCI/LCA — manter (RF-02 já satisfeito)
- `fmt(val, decimals, suffix)` — helper numérico — já presente
- `useFixedIncomeCatalog`, `useTesouroRates` em `useRendaFixa.ts` — padrão para `useMacroRates`

### Established Patterns
- `query_tesouro_rates()` em `service.py` — lê Redis e retorna lista — copiar padrão para `query_macro_rates()`
- `useMemo` no `AcoesUniverseContent.tsx` (Phase 21) — filtro + sort client-side — replicar para `RendaFixaContent`
- `market:macro:cdi` e `market:macro:ipca` no Redis — valores como string decimal (ex: `"10.65"`)

### Integration Points
- `RendaFixaContent.tsx` recebe dados de `useFixedIncomeCatalog()` (catalog rows com `ir_breakdowns`) e `useTesouroRates()` — adicionar `useMacroRates()` no mesmo componente
- Beat indicator calculado no frontend: `parseFloat(cdi) / 100` → anualizar para prazo → comparar com `net_pct`
- `GET /renda-fixa/macro-rates` montado automaticamente pelo router já registrado em `main.py` linha 126 — sem alteração em `main.py`

### O que NÃO existe hoje (gaps a implementar)
- Nenhum filtro de tipo ou prazo na `RendaFixaContent.tsx` atual
- Nenhum sort por retorno líquido
- Nenhum indicador CDI/IPCA por célula
- Nenhum endpoint `GET /renda-fixa/macro-rates` (CDI/IPCA expostos apenas internamente)

</code_context>

<deferred>
## Deferred Ideas

- Nenhuma sugestão de escopo adicional surgiu durante a discussão

</deferred>

---

*Phase: 22-catalogo-renda-fixa*
*Context gathered: 2026-04-12*
