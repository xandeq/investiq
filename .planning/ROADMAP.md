# InvestIQ v1.3 — FII Screener Roadmap

**Milestone:** v1.3 FII Screener
**Phases:** 17–19 (continues from v1.2 Phase 16)
**Granularity:** Coarse (2 phases — critical path only)
**Status:** Active
**Created:** 2026-04-04

---

## Phases

- [x] **Phase 17: FII Screener Table** — Tabela de FIIs ranqueada por score composto com filtros por segmento e DY mínimo (completed 2026-04-04)
- [x] **Phase 18: FII Detail Page + IA Analysis** — Página /fii/[ticker] com histórico DY/P/VP, portfólio básico e análise IA assíncrona (completed 2026-04-04)
- [x] **Phase 19: Opportunity Detector Page** — Página /opportunity-detector exibindo oportunidades detectadas pelo bot Telegram, com histórico e filtros (completed 2026-04-05)

---

## Phase Details

### Phase 17: FII Screener Table

**Goal:** Usuário vê tabela de FIIs ranqueados por score composto e consegue filtrar por segmento e DY mínimo em segundos.

**Depends on:** v1.2 complete (Phase 16) — global_fiis table and Celery FII metadata pipeline already exist from v1.1

**Requirements:** SCRF-01, SCRF-02, SCRF-03

**Success Criteria** (what must be TRUE):
1. Usuário acessa /fii/screener e vê tabela com colunas Score, Rank, Ticker, Segmento, DY 12m, P/VP e Liquidez Diária para todos os FIIs do universo
2. Tabela vem ordenada do maior para o menor score composto por padrão, com ranks visíveis (1, 2, 3...)
3. Usuário seleciona um segmento no dropdown (Logística, Lajes Corporativas, Shopping, CRI/CRA, FoF, Híbrido, Residencial) e a tabela filtra instantaneamente sem reload de página
4. Usuário digita ou arrasta slider de DY mínimo (ex: 8%) e a tabela exibe apenas FIIs com DY 12m >= esse valor
5. Usuário clica no ticker de qualquer FII na tabela e é levado para a página /fii/[ticker]

**Plans:** 2/2 plans complete

Plans:
- [x] 17-01-PLAN.md — Backend: migration, model, Celery score task, API endpoint, tests
- [x] 17-02-PLAN.md — Frontend: screener table component, filters, page route, nav link

---

### Phase 18: FII Detail Page + IA Analysis

**Goal:** Usuário vê dados históricos, portfólio e análise IA de um FII específico na página /fii/[ticker], com o mesmo padrão de UX assíncrona já estabelecido em /stock/[ticker].

**Depends on:** Phase 17 (screener table working; /fii/[ticker] navigation exists)

**Requirements:** SCRF-04

**Success Criteria** (what must be TRUE):
1. Usuário acessa /fii/[ticker] e vê dados básicos do FII: nome, segmento, P/VP atual, DY 12m, último dividendo, liquidez diária
2. Usuário vê gráfico histórico de DY mensal dos últimos 12 meses (barras) e gráfico histórico de P/VP (linha), ambos alimentados por dados do BRAPI dividendsData
3. Usuário vê seção "Portfólio" com dados básicos disponíveis via BRAPI (número de imóveis, tipo de contrato, vacância quando disponível) — campos ausentes exibem "Dado não disponível"
4. Usuário clica "Gerar Análise IA" e recebe job_id imediatamente; enquanto o job processa, vê spinner com "Analisando..."; ao completar, vê narrativa em PT-BR sobre qualidade do dividendo, sustentabilidade dos proventos e posicionamento do P/VP vs histórico
5. Análise IA exibe CVM disclaimer visível antes do conteúdo gerado ("Análise educacional — não é recomendação de investimento")

**Plans:** 2 plans

Plans:
- [ ] 18-01-PLAN.md — Backend: fetch_fii_data helper, run_fii_analysis Celery task, POST /analysis/fii/{ticker} endpoint, tests
- [ ] 18-02-PLAN.md — Frontend: /fii/[ticker] page, FIIDetailContent, DY/P/VP charts, portfolio section, IA analysis card

### Phase 19: Opportunity Detector Page

**Goal:** Usuário vê na página /opportunity-detector as oportunidades detectadas pelo backend (as mesmas enviadas ao Telegram chat_id 721438452), com histórico, filtros e possibilidade de marcar como acompanhada.

**Depends on:** Phase 18 (padrão de páginas FII estabelecido)

**Requirements:** OPDET-01 (nova — não estava no v1.3 original)

**Success Criteria** (what must be TRUE):
1. Usuário acessa /opportunity-detector e vê lista de oportunidades detectadas (ticker, tipo, descrição, score, timestamp)
2. Usuário pode filtrar por tipo de oportunidade (DY alto, P/VP baixo, etc.) e por período
3. Cada oportunidade mostra os dados que foram enviados ao Telegram (mesma informação)
4. Página é protegida por auth (PROTECTED_PATHS)
5. Backend expõe endpoint GET /opportunity-detector/history (persiste as oportunidades detectadas em tabela)

**Plans:** 2/2 plans complete

Plans:
- [x] 19-01-PLAN.md — Backend: DetectedOpportunity model, migration 0022, persistence hook in dispatch_opportunity, GET /history + PATCH /{id}/follow endpoints, tests
- [x] 19-02-PLAN.md — Frontend: /opportunity-detector page with filters (asset type + days), risk badges, follow toggle, expandable detail rows

**Telegram context:**
- Bot configurado e funcionando — chat_id `721438452`
- Backend já detecta e envia oportunidades via Telegram
- Falta: persistir no DB + expor via API + página frontend

---

## Progress Tracking

| Phase | Status | Plans Complete | Completed |
|-------|--------|----------------|-----------|
| 17 - FII Screener Table | ✅ DEPLOYED | 2/2 | 2026-04-04 |
| 18 - FII Detail Page + IA | ✅ DEPLOYED | 2/2 | 2026-04-04 |
| 19 - Opportunity Detector Page | 2/2 | Complete    | 2026-04-05 |

**Totals:** 3 phases | 5/5 requirements mapped | 66% complete

---

## Requirements Coverage

### v1.3 Requirements to Phases Mapping

| Requirement | Phase | Description | Status |
|-------------|-------|-------------|--------|
| SCRF-01 | 17 | Tabela FIIs ranqueados por score composto (DY 12m + P/VP + liquidez) | Pending |
| SCRF-02 | 17 | Filtro por segmento | Pending |
| SCRF-03 | 17 | Filtro por DY mínimo 12m | Pending |
| SCRF-04 | 18 | Página /fii/[ticker] com histórico DY/P/VP, portfólio e análise IA assíncrona | Pending |
| OPDET-01 | 19 | Página /opportunity-detector com histórico, filtros e follow | Pending |

**Coverage Summary:**
- Total v1.3 requirements: 5
- Mapped to phases: 5
- Unmapped: 0
- **Coverage: 100% ✓**

---

## Key Design Decisions

### Why 2 Phases

Coarse granularity with 4 requirements maps naturally to 2 delivery boundaries:

- **Phase 17** (SCRF-01/02/03): All three requirements deliver one coherent capability — a filterable screener table. Backend needs score calculation added to global_fiis pipeline; frontend needs new /fii/screener page. These 3 requirements cannot ship partially — the table is only useful with filters.
- **Phase 18** (SCRF-04): The detail page is a distinct, deeper capability that depends on the screener table for navigation. Reuses the async Celery job pattern from /stock/[ticker] analysis (v1.2 Phase 12–13 pattern).

Combining into 1 phase would create a monster phase. Splitting into 3+ phases would over-engineer 4 requirements.

### Backend Architecture Notes

- **Score formula:** `normalized_score = (DY_rank * 0.5) + (P_VP_rank * 0.3) + (liquidity_rank * 0.2)` where ranks are percentile within FII universe (0–100). Higher = better for DY and liquidity; lower P/VP = better (invert rank).
- **Data source:** BRAPI `/v2/quote/{ticker}?modules=dividendsData,summaryProfile` for FII quotes + dividends history.
- **DY 12m calculation:** Sum of dividendsData.cashDividends for last 12 months / current price.
- **Score pipeline:** Add Celery beat task to recalculate scores nightly after FII metadata pipeline completes. Store score + ranks in global_fiis table (add columns via migration).
- **IA analysis pattern:** Reuse exact Celery job pattern from stock analysis (POST returns job_id, GET /fii-analysis/{job_id}). New FII-specific prompt focused on dividend quality, P/VP vs NAV, portfolio sustainability.

### Reuse from v1.2

- Async job pattern (POST → job_id → WebSocket polling) — Phase 12/13
- LLM provider chain (Claude Haiku → Groq fallback) — Phase 14
- CVM disclaimer component — Phase 12
- `get_global_db` pattern for FII global tables — v1.1

---

*Roadmap created: 2026-04-04*
*Milestone: InvestIQ v1.3 — FII Screener*
*Status: Active — Phase 19 planned*
*Last updated: 2026-04-04 — Phase 19 planned with 2 plans (backend + frontend)*
