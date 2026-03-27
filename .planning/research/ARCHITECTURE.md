# Architecture Research

**Domain:** Investment portfolio SaaS — v1.1 integration architecture (screeners, renda fixa, allocation simulator, AI wizard)
**Researched:** 2026-03-21
**Confidence:** HIGH for integration patterns (codebase read directly) / MEDIUM for new external data sources

## Executive Summary

v1.1 adds 4 new feature areas, but only 2 genuinely new architectural patterns:
1. **Global (non-tenant) data tables** — `screener_snapshots` and `fii_metadata` have no `tenant_id`. The existing FastAPI dependency stack always sets tenant context; a new `get_global_db` dependency is needed for screener endpoints.
2. **Daily universe refresh** — a new Celery beat task category that builds market-wide snapshots vs the existing per-user recalc pattern.

Everything else reuses existing patterns: sync endpoints reading from PostgreSQL/Redis, Celery async tasks for AI calls, existing `call_llm()` from `ai/provider.py`.

## New Components

| Component | Type | Pattern | Depends On |
|-----------|------|---------|------------|
| `screener_snapshots` table | PostgreSQL (global, no RLS) | Migration only | Phase 1 existing |
| `fii_metadata` table | PostgreSQL (global, no RLS) | Migration only | Phase 1 existing |
| `fixed_income_catalog` table | PostgreSQL (global, no RLS) | Admin-seeded | Phase 1 existing |
| `tesouro_rates` Redis key | Redis cache | `tesouro:rates:{TYPE}` namespace | Existing Redis |
| `refresh_screener_universe` | Celery beat task | Daily, batch brapi.dev | brapi.dev client |
| `refresh_fii_metadata` | Celery beat task | Weekly, CVM CSV download | CVM Open Data |
| `refresh_tesouro_rates` | Celery beat task | Every 6h | ANBIMA/Tesouro CSV |
| `screener/` module | FastAPI router | Sync, global DB | `screener_snapshots` |
| `renda_fixa/` module | FastAPI router | Sync, Redis + DB | Redis cache, `fixed_income_catalog` |
| `simulador/` module | FastAPI router | Sync backend math | Redis, PostgreSQL |
| `advisor/` module | FastAPI router + Celery task | Async 202 + poll | All of above + portfolio |

## Modified Components

| Component | Change | Risk |
|-----------|--------|------|
| `market_data/service.py` | Add `refresh_screener_universe()` Celery task | Low — additive |
| `market_data/brapi_client.py` | Add `fetch_quote_list()` for bulk ticker list | Low — additive |
| Celery beat schedule | Add 3 new scheduled tasks | Low — additive |
| FastAPI dependencies | Add `get_global_db()` (no tenant context) | Medium — new pattern |
| Redis key schema | New namespaces: `screener:*`, `tesouro:*`, `fii:*` | Low if documented upfront |

## Data Flow: Screener

```
[Celery Beat — daily]
  → BrapiClient.fetch_quote_list(type="stock", fundamental=True)
  → batch loop (50 tickers/request, ~18 requests for ~900 tickers)
  → upsert screener_snapshots (ticker, dy, pl, pvp, ev_ebitda, volume, sector, updated_at)

[User Request — sync]
  GET /screener/acoes?dy_min=5&pvp_max=2&sector=financeiro
  → FastAPI (get_global_db — no tenant context)
  → SELECT * FROM screener_snapshots WHERE dy >= 5 AND pvp <= 2 AND sector = 'financeiro'
  → optional: LEFT JOIN user_transactions to flag "já tenho" tickers
  → return paginated results
```

**Key: screener filter is a simple SQL query, not an external API call per request.**

## Data Flow: FII Metadata

```
[Celery Beat — weekly]
  → download CVM CSV from dados.cvm.gov.br/dados/FII/
  → parse with pandas (already in Celery environment)
  → upsert fii_metadata (ticker, segmento, vacancia_financeira, pl, num_cotistas, updated_at)

[User Request — sync]
  GET /screener/fiis?segmento=tijolo&pvp_max=1.0&dy_min=8
  → FastAPI (get_global_db)
  → JOIN screener_snapshots + fii_metadata ON ticker
  → return with segment-aware P/VP context
```

## Data Flow: Renda Fixa Catalog

```
[Celery Beat — every 6h]
  → fetch Tesouro Transparente CSV (tesourotransparente.gov.br/ckan)
  → fallback: python-bcb SGS series for reference rates
  → cache: SET tesouro:rates:SELIC_2029 {taxa, preco_compra, vencimento} EX 21600
  → CDI reference: already cached in market:macro:CDI (v1.0)

[User Request — sync]
  GET /renda-fixa/catalogo
  → FastAPI (no tenant needed)
  → GET tesouro:rates:* from Redis (all Tesouro bonds)
  → GET market:macro:CDI from Redis (CDI reference rate — v1.0)
  → assemble fixed_income_catalog rows (CDB/LCI/LCA reference ranges)
  → compute TaxEngine.net_return(rate, days, asset_class) for each item
  → return catalog with net returns by holding period
```

## Data Flow: Simulador de Alocação

```
[User Request — sync, < 500ms]
  POST /simulador/alocacao
  { valor: 50000, prazo_anos: 3, perfil: "moderado", incluir_carteira: true }

  → GET user portfolio from PostgreSQL (if incluir_carteira=True)
  → GET CDI, SELIC, IPCA from Redis (market:macro:*)
  → GET screener_snapshots aggregate stats (avg DY for ações/FIIs)
  → GET tesouro:rates:* for current RF rates
  → AllocationEngine.compute(portfolio, valor, prazo, perfil, macro)
      - returns: mix percentual + 3 cenários (pess/base/otimista) + IR-adjusted projections
  → return synchronously (all data in-memory, no external calls)
```

**Key: stays on backend. Brazilian IR rules (tabela regressiva) must be server-side.**

## Data Flow: Wizard "Onde Investir" (Async)

```
[User Request — 202 accepted]
  POST /advisor/wizard
  { valor: 50000, prazo_anos: 5, perfil: "moderado" }
  → FastAPI creates AdvisorRun(status=PENDING)
  → dispatch_advisor_run.delay(run_id, user_id)
  → return { run_id, status_url }

[Celery Task — async]
  → fetch portfolio context (user's current positions + P&L)
  → fetch screener top-10 ações (DY > CDI, P/VP < 1.5, alta liquidez)
  → fetch screener top-10 FIIs (Tijolo, DY > 10%, P/VP < 1.1)
  → fetch Tesouro rates + CDI from Redis
  → fetch macro context (SELIC, IPCA trend from python-bcb)
  → build LLM prompt (~8-12KB):
      - carteira atual + alocação percentual
      - valor disponível + prazo + perfil
      - macro snapshot
      - screener top picks (context, not "recommendations")
      - HARD CONSTRAINT in prompt: "output ONLY asset class percentages, never ticker names"
  → call_llm() from ai/provider.py (unchanged)
  → parse output: { acoes_pct, fiis_pct, renda_fixa_pct, caixa_pct, rationale }
  → update AdvisorRun(status=COMPLETE, result=...)

[Frontend Poll]
  GET /advisor/wizard/{run_id}
  → return status + result when COMPLETE
  → display: CVM disclaimer FIRST, then allocation percentages
```

## Redis Namespace Schema (v1.1 additions)

```
# New namespaces — DO NOT mix with existing market:* keys
screener:universe:{TICKER}     # Per-ticker screener snapshot (daily)
screener:last_refresh          # Timestamp of last universe rebuild
fii:metadata:{TICKER}          # FII segment/vacancy/cotistas (weekly)
tesouro:rates:{BOND_CODE}      # Tesouro Direto rate + price (6h)
tesouro:last_refresh           # Timestamp of last Tesouro refresh

# Existing namespaces (DO NOT change)
market:quotes:{TICKER}         # Per-ticker quote (60s TTL)
market:macro:CDI               # CDI rate (1h TTL)
market:macro:SELIC             # SELIC rate (1h TTL)
market:macro:IPCA              # IPCA rate (24h TTL)
```

## New FastAPI Dependency: get_global_db

```python
# app/dependencies.py — ADD alongside existing get_db()
async def get_global_db():
    """
    DB session WITHOUT tenant context injection.
    Used ONLY for global tables: screener_snapshots, fii_metadata, fixed_income_catalog.
    Never use for user data queries.
    """
    async with async_session() as session:
        # DO NOT set app.current_tenant — global data, no RLS needed
        yield session
```

**Why:** The existing `get_db()` always sets `SET LOCAL app.current_tenant = '{tenant_id}'`. Screener tables have no `tenant_id` column and no RLS policy. Using `get_global_db` makes the intent explicit and prevents accidental tenant context contamination.

## Build Order (strict dependencies)

1. **Migrations** — `screener_snapshots`, `fii_metadata`, `fixed_income_catalog` tables + `get_global_db` dependency
2. **Data pipelines** — `refresh_screener_universe` + `refresh_fii_metadata` + `refresh_tesouro_rates` Celery tasks (can be developed in parallel)
3. **Screener endpoints** — sync, reads from step 1+2 tables
4. **Renda fixa catalog endpoint** — sync, reads Tesouro Redis + `fixed_income_catalog` table
5. **Simulador endpoint** — sync, reads Redis + portfolio + above tables
6. **Wizard advisor module** — async Celery, aggregates everything from steps 1-5

Steps 2-4 can be developed in parallel once step 1 is done. Step 5 depends on step 4. Step 6 depends on all.

## Anti-Patterns to Avoid

1. **Calling brapi.dev per screener request** — must be pre-cached in `screener_snapshots`. If the table is empty (first run), return 503 with `Retry-After: 3600` header.
2. **Using `get_db()` for screener queries** — it sets tenant context which is wrong for global tables. Always use `get_global_db()` for screener/catalog endpoints.
3. **Wizard outputting specific tickers** — enforce in prompt template with explicit negative constraint. Add post-processing validation that errors if LLM response contains a 4-6 character uppercase string (ticker pattern).
4. **Frontend IR calculation** — Brazilian tabela regressiva must be server-side. Never send the raw rate to frontend and have it calculate net return.

---
*Research completed: 2026-03-21*
*Scope: v1.1 integration architecture — see v1.0 SUMMARY.md for base architecture*
