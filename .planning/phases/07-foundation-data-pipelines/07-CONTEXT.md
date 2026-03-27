# Phase 7: Foundation + Data Pipelines - Context

**Gathered:** 2026-03-21
**Status:** Ready for planning

<domain>
## Phase Boundary

All infrastructure required by v1.1 is in place: global DB tables exist (no tenant scoping), TaxEngine enforces correct IR regressivo rules with DB-stored rates, Redis namespaces for v1.1 are defined and isolated from existing `market:*` keys, and the three Celery beat pipelines are running and populating data that screener and catalog endpoints (Phase 8) will read.

Phase 7 delivers **no user-facing endpoints** — it is pure infrastructure: migrations, Celery tasks, TaxEngine, and data pipelines.

</domain>

<decisions>
## Implementation Decisions

### Tesouro Direto data source
- **D-01:** ANBIMA API is the primary source for Tesouro Direto rates (credentials are in hand — production endpoint, real live rates)
- **D-02:** ANBIMA credentials go into AWS Secrets Manager at `tools/anbima` — Celery worker fetches at task startup, same pattern as `tools/brapi` and other API keys
- **D-03:** CKAN CSV (Tesouro Nacional open data) is the fallback if ANBIMA API fails — no auth, updated daily, URL to confirm during research
- **D-04:** `refresh_tesouro_rates` task runs every 6 hours on the existing beat schedule — ANBIMA provides intraday updates

### CDB/LCI/LCA catalog
- **D-05:** `fixed_income_catalog` table is seeded via Alembic migration INSERT statements (no admin endpoint needed in Phase 7)
- **D-06:** Updates to reference rates are done via direct SQL — acceptable because these only shift significantly when CDI moves meaningfully (monthly at most)
- **D-07:** Seed rows to include:
  - CDB % CDI: 6m (95–100%), 1a (100–107%), 2a (105–110%), 5a (108–115%)
  - LCI/LCA % CDI: 6m (80–88%), 1a (85–92%), 2a (88–95%)
  - CDB IPCA+: 3a (IPCA+5%), 5a (IPCA+5.5%)
  - LCA IPCA+: 2a (IPCA+4%), 5a (IPCA+4.5%)
- **D-08:** UI must always label these as "taxas de referência de mercado" — never "oferta ao vivo" (requirement from STATE.md)

### TaxEngine schema
- **D-09:** `tax_config` table — one row per IR tier. Schema: `(id, asset_class, holding_days_min, holding_days_max, rate_percent, is_exempt, label)`
- **D-10:** Scope is IR regressivo + LCI/LCA PF exemption + FII dividend exemption — NOT full IR matrix (acoes R$20k limit, day-trade are Phase 2/v2 scope)
- **D-11:** Seed data:
  - IR regressivo: 4 tiers (≤180d = 22.5%, 181–360d = 20%, 361–720d = 17.5%, >720d = 15%)
  - LCI/LCA PF: `is_exempt=true, rate_percent=0` for all holding periods
  - FII dividend: `is_exempt=true, rate_percent=0`
- **D-12:** No admin API — rate changes go through direct SQL (`docker exec ... psql`)
- **D-13:** TaxEngine is a pure Python service class that reads from `tax_config` at init time (cached in-process, no per-call DB hit)

### brapi.dev universe fetch
- **D-14:** Paid brapi plan confirmed — 15k req/month limit is not a constraint
- **D-15:** Daily rebuild schedule: weekdays only (Mon–Fri), never weekends (B3 data unchanged on weekends)
- **D-16:** Partial failure handling: accept partial snapshot, log per-ticker failures, continue. Failed tickers retain their previous snapshot row (stale but present). No transaction rollback on the entire run.
- **D-17:** Per-ticker sleep: 200ms between requests (from STATE.md). On 429 from brapi: exponential backoff up to 3 retries, then skip ticker and log.

### Module structure for v1.1
- **D-18:** New top-level module `app/modules/market_universe/` contains Phase 7 code:
  - `models.py` — global tables (screener_snapshots, fii_metadata, fixed_income_catalog, tax_config)
  - `tasks.py` — three beat tasks (refresh_screener_universe, refresh_fii_metadata, refresh_tesouro_rates)
  - `tax_engine.py` — TaxEngine service class
  - No router yet (Phase 7 has no endpoints)
- **D-19:** `get_global_db` FastAPI dependency goes in `app/core/db.py` alongside existing `get_db` and `get_tenant_db`

### Claude's Discretion
- Exact ANBIMA OAuth2 token refresh logic (client_credentials grant assumed, confirm during research)
- CVM FII vacancy data fetch URL and CSV format for `refresh_fii_metadata`
- Batching strategy within brapi.dev requests (single ticker per call vs batch endpoint if available)
- Index design for `screener_snapshots` (composite on ticker + snapshot_date likely sufficient)

</decisions>

<specifics>
## Specific Ideas

- Redis namespace isolation is strict: Phase 7 keys use `screener:universe:{TICKER}`, `tesouro:rates:{BOND_CODE}`, `fii:metadata:{TICKER}` — never `market:*` prefix (would collide with existing Phase 2 market data)
- `screener_snapshots` table stores the latest fundamentals snapshot per ticker — Phase 8 reads this, never calls brapi.dev at request time
- TaxEngine is used by: Phase 8 renda fixa catalog (net yield), Phase 9 comparador (IR-adjusted returns), Phase 10 simulator — it must be a shared, importable service, not embedded in tasks

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Existing Celery infrastructure
- `backend/app/celery_app.py` — Beat schedule registration, task module includes, Celery config (model to follow for new tasks)
- `backend/app/modules/market_data/tasks.py` — `_get_redis()` helper pattern, brapi.dev fetch pattern, retry logic, Redis write TTL pattern

### DB session patterns
- `backend/app/core/db_sync.py` — `get_sync_db_session(tenant_id=None)` for global tables (pass None to skip RLS), `get_superuser_sync_db_session()` for unrestricted access in tasks
- `backend/app/core/db.py` — `get_db`, `get_tenant_db` — new `get_global_db` goes here

### Migration template
- `backend/alembic/versions/0013_add_screener_runs.py` — Table creation, index, GRANT pattern
- Latest migration: `0014_add_trial_fields` → Phase 7 uses `0015_add_market_universe_tables`
- For global tables: omit `tenant_id` column and RLS GRANT — still GRANT SELECT/INSERT/UPDATE/DELETE to app_user

### Redis namespace documentation
- `backend/app/modules/market_data/service.py` — Existing `market:*` key schema (avoid these prefixes in Phase 7)

### v1.1 architecture decisions
- `.planning/STATE.md` §v1.1 Architecture Decisions — all locked architectural choices
- `.planning/REQUIREMENTS.md` §v1.1 Requirements — SCRA-04 is the Phase 7 requirement

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_get_redis()` in market_data/tasks.py: sync Redis client factory — copy this pattern into market_universe/tasks.py
- `get_sync_db_session(tenant_id=None)`: already supports global (unscoped) DB access — use this for all Phase 7 task DB writes
- brapi.dev BrapiClient in market_data: reuse or extract for screener universe fetch

### Established Patterns
- Task pattern: `@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)` — use for all 3 new tasks
- Beat registration: add entries to `celery_app.py` `beat_schedule` dict — existing entries show crontab pattern
- Model pattern: SQLAlchemy 2.x `Mapped[T]` with `mapped_column()` — all Phase 7 models use this
- Global tables have NO `tenant_id` column and NO RLS policy — reference `users` table as example

### Integration Points
- Phase 7 tasks write to DB and Redis; Phase 8 reads from both — schema must be stable before Phase 8 planning
- TaxEngine (`tax_engine.py`) is consumed by Phases 8, 9, 10 — must be importable from `app.modules.market_universe.tax_engine`
- New beat tasks must be registered in `celery_app.includes` list before `beat_schedule` entries will fire

</code_context>

<deferred>
## Deferred Ideas

- Admin UI for updating CDB/LCI/LCA reference rates — Phase 7 uses direct SQL; admin interface is out of scope for v1.1
- Full IR matrix (acoes monthly R$20k exemption, day-trade 20%) — v2 scope (IR-01, IR-02, IR-03)
- brapi.dev checkpoint/resume for failed runs — accepted partial snapshot is sufficient for v1.1; checkpoint complexity deferred
- Tesouro Direto websocket / real-time rate streaming — well outside v1.1 scope

</deferred>

---

*Phase: 07-foundation-data-pipelines*
*Context gathered: 2026-03-21*
