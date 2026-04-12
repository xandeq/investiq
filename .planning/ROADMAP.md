# InvestIQ v1.4 — Ferramentas de Análise — Roadmap

**Milestone:** v1.4 Ferramentas de Análise
**Phases:** 21–22 (continues from v1.3 Phase 20)
**Granularity:** Coarse (2 phases — natural delivery boundaries)
**Status:** Active
**Created:** 2026-04-12

---

## Phases

- [ ] **Phase 21: Screener de Ações** — Tabela filtrável de ~900 ações com endpoint filterable, paginação e link para /stock/[ticker]
- [ ] **Phase 22: Catálogo Renda Fixa** — Frontend do catálogo RF com retorno líquido IR por prazo, filtros e indicadores visuais (backend exists from v1.1)

---

## Phase Details

### Phase 21: Screener de Ações
**Goal:** Usuário pode explorar e filtrar o universo completo de ações brasileiras por fundamentos diretamente na plataforma
**Depends on:** Nothing (screener universe ~900 tickers already populated nightly by Celery beat from v1.1; screener_snapshots table exists)
**Requirements:** SCRA-01, SCRA-02, SCRA-03, SCRA-04
**Success Criteria** (what must be TRUE):
  1. Usuário acessa /acoes/screener e vê tabela com colunas Ticker, Nome, Setor, Preço Atual, Variação 12m%, DY 12m, P/L e Market Cap — cada coluna é clicável para ordenar
  2. Usuário aplica filtros (DY mínimo slider, P/L máximo input, Setor dropdown B3, Market Cap small/mid/large) e a tabela atualiza instantaneamente sem reload de página
  3. Usuário clica em qualquer ticker da tabela e é navegado para /stock/[ticker] — a página de análise completa já existente abre corretamente
  4. Tabela exibe paginação e usuário navega entre páginas de resultados
**Plans:** 1/3 plans executed

Plans:
- [x] 21-01-PLAN.md — Migration 0024 + brapi 52WeekChange + Celery upsert for variacao_12m_pct
- [ ] 21-02-PLAN.md — GET /screener/universe endpoint (schemas, service, router, tests)
- [ ] 21-03-PLAN.md — Frontend /acoes/screener page (feature dir, filters, sort, pagination)

---

### Phase 22: Catálogo Renda Fixa
**Goal:** Usuário compara produtos de renda fixa com retorno líquido real (após IR regressivo) por prazo, sem precisar sair da plataforma
**Depends on:** Nothing (fixed_income_catalog table + TaxEngine + Celery pipeline fully operational from v1.1; RF API endpoint may already exist)
**Requirements:** RF-01, RF-02, RF-03
**Success Criteria** (what must be TRUE):
  1. Usuário acessa /renda-fixa e vê catálogo agrupado por tipo (Tesouro Direto, CDB, LCI/LCA) com taxa, vencimento e valor mínimo de aplicação por produto
  2. Cada produto exibe retorno líquido calculado pelo TaxEngine para prazos 90d, 1a, 2a, 5a — produtos LCI/LCA têm badge ou destaque visual de isenção IR
  3. Usuário filtra catálogo por tipo (Tesouro/CDB/LCI/LCA) e prazo mínimo e ordena por retorno líquido — tabela atualiza sem reload
  4. Cada produto exibe indicador visual (ícone verde/vermelho ou texto) se o retorno líquido supera CDI ou IPCA no prazo selecionado
**Plans:** TBD

---

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 21. Screener de Ações | 1/3 | In Progress|  |
| 22. Catálogo Renda Fixa | 0/TBD | Not started | - |

---

## Requirements Coverage

| Requirement | Phase | Description | Status |
|-------------|-------|-------------|--------|
| SCRA-01 | Phase 21 | Tabela de ações ordenável (Ticker, Nome, Setor, Preço, Var 12m%, DY, P/L, Market Cap) | Pending |
| SCRA-02 | Phase 21 | Filtros DY mínimo / P/L máximo / Setor B3 / Market Cap | Pending |
| SCRA-03 | Phase 21 | Click ticker → /stock/[ticker] | Pending |
| SCRA-04 | Phase 21 | Paginação da tabela | Pending |
| RF-01 | Phase 22 | Catálogo agrupado por tipo com taxa, vencimento, valor mínimo | Pending |
| RF-02 | Phase 22 | Retorno líquido IR por prazo (90d/1a/2a/5a) + destaque isenção LCI/LCA | Pending |
| RF-03 | Phase 22 | Filtros por tipo/prazo, ordenação por retorno líquido, indicador CDI/IPCA | Pending |

**Coverage:** 7/7 ✓

---

## Architecture Notes

### Phase 21 — Screener de Ações

**Backend exists:**
- `screener_snapshots` table populated nightly by Celery beat (~900 tickers, from v1.1)
- Goldman Sachs screener endpoint at `/screener/` — returns top 10 scored stocks only
- **What's missing:** New endpoint returning full universe with filterable columns (DY, P/L, Setor, Market Cap, Variação 12m)

**Approach:**
- New `GET /screener/universe` endpoint returns all tickers with the required columns
- Frontend filters client-side with useMemo (same approach as Phase 17 FII Screener — ~900 tickers fits in browser memory)
- Paginação client-side or server-side (prefer client-side for consistency with Phase 17)

**Pattern to reuse:** Phase 17 FII Screener — same table + filter UX, same useMemo client-side approach, same Tailwind table styling

### Phase 22 — Catálogo Renda Fixa

**Backend exists (verify before creating new):**
- `fixed_income_catalog` table populated nightly by Celery beat (from v1.1)
- TaxEngine fully operational — IR regressivo (22.5%→15%) + LCI/LCA isenção
- RF API endpoint may already exist at `/renda-fixa` or `/fixed-income` — check before building new one

**Approach:**
- Frontend-only phase if backend endpoint exists
- If endpoint missing: thin FastAPI route wrapping TaxEngine calculations against fixed_income_catalog
- Retorno líquido calculation: TaxEngine.calculate(principal, rate, days) → net return per prazo bracket
- CDI/IPCA beat indicator: compare product net return vs current CDI rate (stored in DB or fetched from python-bcb)

---

## Key Design Decisions

### Why 2 Phases

Coarse granularity with 7 requirements maps to 2 natural delivery boundaries:

- **Phase 21** (SCRA-01/02/03/04): All four requirements deliver one coherent capability — a filterable ações screener table. They cannot ship partially (table is only useful with filters + navigation + paging). Backend universe already exists; work is a new API endpoint + frontend page.
- **Phase 22** (RF-01/02/03): All three requirements deliver one coherent capability — a usable RF catalog. Backend is fully operational; work is primarily frontend with TaxEngine integration. This is a distinct, independent capability with no dependency on Phase 21.

Each phase has 1–2 plans max (consistent with coarse granularity).

### Reuse from v1.3

- Client-side filtering with useMemo (Phase 17 FII Screener) — same pattern for Phase 21
- Table + filter UX component patterns — reuse as-is
- `get_global_db` pattern for global (non-tenant) data tables
- Nav link addition pattern for new pages

---

## v1.3 Reference (Archived)

v1.3 phases (17–20) completed 2026-04-11. Archive: `.planning/milestones/v1.3-ROADMAP.md` (if created).

| Phase | Status | Completed |
|-------|--------|-----------|
| 17 - FII Screener Table | ✅ DEPLOYED | 2026-04-04 |
| 18 - FII Detail Page + IA | ✅ DEPLOYED | 2026-04-04 |
| 19 - Opportunity Detector Page | ✅ DEPLOYED | 2026-04-05 |
| 20 - Swing Trade Page | ✅ DEPLOYED | 2026-04-11 |

---

*Roadmap created: 2026-04-12*
*Milestone: InvestIQ v1.4 — Ferramentas de Análise*
