# Phase 21: Screener de Ações - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

New page `/acoes/screener` com tabela filtrável de ~900 ações B3. Usuário filtra por DY mín, P/L máx, Setor e Market Cap, ordena por qualquer coluna e clica no ticker para ir para `/stock/[ticker]`. Dados vêm de snapshot diário pré-calculado — sem chamadas externas por requisição. Análise individual de ações (página `/stock/[ticker]`) é escopo de outra phase já existente.

</domain>

<decisions>
## Implementation Decisions

### Variação 12m% — nova coluna no banco

- **D-01:** Adicionar coluna `variacao_12m_pct Numeric(10,6) NULLABLE` na tabela `screener_snapshots` via Migration 0024 (head atual: 0023)
- **D-02:** Atualizar `BrapiClient.fetch_fundamentals()` em `backend/app/modules/market_data/adapters/brapi.py` para extrair `52WeekChange` de `defaultKeyStatistics` e retorná-lo como `variacao_12m`
- **D-03:** Atualizar o upsert em `backend/app/modules/market_universe/tasks.py` (`refresh_screener_universe`) para mapear e persistir `variacao_12m_pct` — campo pode ser NULL para tickers sem histórico completo
- **D-04:** Exibir na tabela como `Var. 12m%` formatado com cor (verde se positivo, vermelho se negativo) — mesma lógica do `changeBadge()` do `AcoesScreenerContent` já existente

### Rota e arquitetura frontend

- **D-05:** Nova página em `frontend/app/acoes/screener/page.tsx` (nova estrutura de diretório — não existe hoje)
- **D-06:** Novo feature directory `frontend/src/features/acoes_screener/` com componentes, hooks e tipos próprios
- **D-07:** A página existente `/screener/acoes` (em `frontend/app/screener/acoes/`) fica intacta — duas rotas coexistem. A nav link principal vai apontar para `/acoes/screener`
- **D-08:** Filtros funcionam client-side com `useMemo` (igual Phase 17 FII Screener) — não server-side como `/screener/acoes` existente

### Novo endpoint de universo

- **D-09:** Novo endpoint `GET /screener/universe` em `backend/app/modules/screener_v2/router.py` — retorna todos os ~900 tickers do snapshot mais recente, sem filtros, sem paginação
- **D-10:** Response inclui campos: `ticker`, `short_name`, `sector`, `regular_market_price`, `variacao_12m_pct`, `dy` (decimal), `pl`, `market_cap`
- **D-11:** DY é armazenado como decimal (0.09 = 9%) — o frontend multiplica por 100 para exibir. Mesma convenção do FII screener
- **D-12:** Endpoint requer `get_current_user` + `get_global_db` (padrão screener_v2)

### Filtros e colunas da tabela

- **D-13:** Filtros exatos conforme ROADMAP: DY mín (input numérico em %), P/L máx (input), Setor B3 (dropdown), Market Cap (botões small/mid/large)
- **D-14:** Thresholds Market Cap: **Small < R$ 2B**, **Mid R$ 2B–10B**, **Large > R$ 10B** — valores em R$ devem aparecer como tooltip ou label no filtro para o usuário entender o critério
- **D-15:** Ordenação client-side por qualquer coluna — clique no header alterna asc/desc. Estado de sort armazenado em `useState`
- **D-16:** Paginação client-side — PAGE_SIZE=50 (mesmo padrão do `FIIScoredScreenerContent`)
- **D-17:** Click no ticker → `<Link href={/stock/${ticker}}>` — página de análise já existente

### Claude's Discretion

- Valores exatos dos setores B3 disponíveis no dropdown (pesquisar via `SELECT DISTINCT sector FROM screener_snapshots ORDER BY sector` antes de hardcodar)
- Skeleton/loading state enquanto endpoint carrega
- Mensagem de empty state quando nenhum ativo passa nos filtros
- Ordenação inicial (default): sem ordenação definida ou por market_cap desc
- Exact spacing e typography

</decisions>

<specifics>
## Specific Ideas

- Tabela deve ter `max-w-7xl` container (igual FII screener e opportunity detector — escala bem para 8 colunas)
- Coluna Ticker com `font-mono font-bold text-sm` + short_name abaixo em `text-xs text-gray-500` (padrão estabelecido em FIIScoredScreenerContent e AcoesScreenerContent)
- Var. 12m% com badge colorida (verde/vermelho) — reutilizar o `changeBadge()` já existente em `frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx`
- Market Cap formatado como "R$ 42.5B" / "R$ 850M" — reutilizar `fmtBRL()` já implementado no mesmo arquivo
- Setor como texto simples (sem badge colorida por setor — setores de ações são muitos, badges ficam poluídas)

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Backend — padrão de endpoint e queries
- `backend/app/modules/screener_v2/router.py` — Padrão exato dos endpoints screener_v2, dependências, limiter, response models. Adicionar `GET /screener/universe` aqui
- `backend/app/modules/screener_v2/schemas.py` — Schemas Pydantic existentes (AcaoRow, AcaoScreenerResponse) — criar novo schema `ScreenerUniverseResponse` e `ScreenerUniverseRow`
- `backend/app/modules/screener_v2/service.py` — Padrão de query async com SQLAlchemy — criar `query_screener_universe()` aqui
- `backend/app/modules/market_universe/models.py` — Modelo `ScreenerSnapshot` — adicionar campo `variacao_12m_pct` aqui (Migration 0024)
- `backend/app/modules/market_universe/tasks.py` — Celery task `refresh_screener_universe` — adicionar mapeamento de `variacao_12m_pct` no upsert
- `backend/app/modules/market_data/adapters/brapi.py` — `BrapiClient.fetch_fundamentals()` — adicionar extração de `52WeekChange` de `defaultKeyStatistics`

### Frontend — componentes de referência (padrão a replicar)
- `frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx` — Implementação de referência: useMemo filtering, sort por coluna, paginação client-side, table rows
- `frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx` — `changeBadge()`, `fmtBRL()`, `fmt()` — reutilizar essas funções. Padrão de filtros de ação existente
- `frontend/app/fii/screener/page.tsx` — Padrão de page.tsx: AppNav + max-w-7xl + heading
- `frontend/app/screener/acoes/page.tsx` — Página existente (manter, não modificar)

### Migração
- `backend/alembic/versions/0023_*.py` — Migration head atual (confirmar filename antes de criar 0024)
- `backend/alembic/env.py` — Padrão de migration

### Testes
- `backend/tests/test_market_universe_tasks.py` — Testes do Celery task — atualizar para incluir `variacao_12m_pct`
- `tests/e2e/` — Playwright tests — adicionar spec para /acoes/screener

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `changeBadge(val: string | null)` em `AcoesScreenerContent.tsx` — verde/vermelho para % — reutilizar diretamente para Var. 12m%
- `fmtBRL(val: number | null)` em `AcoesScreenerContent.tsx` — formata market cap em B/M — reutilizar diretamente
- `fmt(val, decimals, suffix)` — helper numérico com fallback "—" — presente em ambos FII e Acoes screener
- `segmentoBadge()` — NÃO reutilizar para setores de ações (são muitos setores; texto simples é melhor)
- `AppNav` + estrutura max-w-7xl — padrão de todas as páginas de análise

### Established Patterns
- **Client-side useMemo**: filtros aplicados sobre `data.results` em memória. `useFIIScoredScreener` hook como modelo para `useAcoesUniverse` novo hook
- **`get_global_db`**: dependência padrão para `screener_snapshots` (global table, sem tenant_id). Já usado em `fii_screener/router.py` e `screener_v2/router.py`
- **DY decimal convention**: `dy` = 0.09 significa 9% — multiplicar por 100 no frontend. Confirmado em FII screener e screener_v2
- **`@limiter.limit("30/minute")`** em todos os endpoints screener — manter

### Integration Points
- `backend/app/main.py` linha 125: `screener_v2_router` já montado em `/screener` — o novo `GET /screener/universe` é adicionado ao mesmo router sem tocar em `main.py`
- `backend/app/modules/market_universe/tasks.py:refresh_screener_universe` — o upsert pg_insert precisa de `variacao_12m_pct` na lista de `set_()` columns
- `frontend/app/acoes/` — diretório existe (`frontend/app/acoes/screener` já está lá per `ls`). Criar `page.tsx` dentro de `frontend/app/acoes/screener/`

### Critical Data Gap Discovered
- `screener_snapshots` NÃO tem `variacao_12m_pct` hoje (apenas `regular_market_change_percent` = variação do dia)
- `BrapiClient.fetch_fundamentals()` busca `defaultKeyStatistics` do brapi — `52WeekChange` está disponível nesse módulo mas NÃO está sendo extraído hoje
- A migration 0024 e a atualização do Celery task são **pré-requisitos** para o frontend exibir a coluna corretamente

</code_context>

<deferred>
## Deferred Ideas

- Nenhuma sugestão de escopo adicional surgiu durante a discussão — usuário manteve-se dentro do escopo da phase

</deferred>

---

*Phase: 21-screener-de-acoes*
*Context gathered: 2026-04-12*
