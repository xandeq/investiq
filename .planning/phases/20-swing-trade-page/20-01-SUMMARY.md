---
phase: 20-swing-trade-page
plan: 20-01
subsystem: api
tags: [fastapi, sqlalchemy, alembic, redis, pydantic-v2, rls, swing-trade]

requires:
  - phase: 06-market-data
    provides: "market:quote / market:historical / market:fundamentals Redis cache"
  - phase: 02-portfolio
    provides: "PortfolioService.get_positions + get_authed_db tenant scoping"
  - phase: 19-opportunity-detector-page
    provides: "RADAR_ACOES curated stock list reused as swing trade universe"

provides:
  - "SwingTradeOperation model + migration 0023 with PostgreSQL RLS"
  - "compute_signals service that reads Redis only (no new brapi calls)"
  - "5 swing-trade API endpoints (GET signals, CRUD operations, close)"
  - "Enriched read-side for open operations (pnl_pct, live_signal sell/stop/hold)"

affects: [20-02-frontend-swing-trade-page, future-swing-trade-reports, tenant-rls-tests]

tech-stack:
  added: []
  patterns:
    - "Redis-only read service pattern (no request-time external API calls)"
    - "Dialect-gated PostgreSQL RLS in alembic migration (SQLite-safe tests)"
    - "Tenant-scoped CRUD via get_authed_db + get_current_tenant_id"
    - "Operation enrichment read-side (DB → +current_price/pnl_brl/live_signal)"

key-files:
  created:
    - backend/app/modules/swing_trade/__init__.py
    - backend/app/modules/swing_trade/models.py
    - backend/app/modules/swing_trade/schemas.py
    - backend/app/modules/swing_trade/service.py
    - backend/app/modules/swing_trade/router.py
    - backend/alembic/versions/0023_add_swing_trade_operations.py
    - backend/tests/test_phase20_swing_trade.py
  modified:
    - backend/app/main.py
    - backend/tests/conftest.py

key-decisions:
  - "BUY rule is drop<=-12% AND (dy is None OR dy>=5%) — unknown DY must not mask genuine dips"
  - "SELL/STOP live_signal computed read-side in _enrich_operation — no DB column"
  - "Radar universe = RADAR_ACOES ∪ user portfolio tickers so held stocks surface in signals"
  - "Migration 0023 guards RLS SQL behind dialect check so alembic head works on sqlite tests"
  - "Soft delete via deleted_at — matches Transaction semantics, never hard delete"
  - "Schemas use Decimal (not float) everywhere — Pydantic v2 + ConfigDict(from_attributes)"

patterns-established:
  - "Module _get_redis() dependency as override seam for tests (mirrors portfolio pattern)"
  - "Service-level fake-redis tests can seed market:quote / market:historical / market:fundamentals JSON directly"

requirements-completed: [SWING-01, SWING-02, SWING-03, SWING-04]

duration: 15min
completed: 2026-04-11
---

# Phase 20 Plan 20-01: Backend — Swing Trade Module Summary

**Tenant-scoped swing trade backend with 5 endpoints, Redis-only signal engine (BUY drop>12% + DY>5%, SELL +10%), and manual operation CRUD backed by migration 0023 (RLS on PostgreSQL).**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-04-11T21:27:53Z
- **Completed:** 2026-04-11T21:42:00Z (approx.)
- **Tasks:** 6/6
- **Files created:** 7
- **Files modified:** 2
- **Tests added:** 32 (all passing locally)

## Accomplishments

- New `backend/app/modules/swing_trade/` package with models, schemas, service, and router.
- Alembic migration **0023_add_swing_trade_operations** chains cleanly from 0022 and upgrades/downgrades verified against sqlite (RLS is gated behind `dialect.name == "postgresql"`).
- `compute_signals` reads exclusively from existing Redis keys (`market:quote:*`, `market:historical:*`, `market:fundamentals:*`) — zero new calls to brapi/yfinance/CoinGecko.
- BUY rule implemented: 30-day drop ≥ 12% AND DY ≥ 5% (or DY unknown). Unknown DY is not allowed to mask a genuine dip.
- Live SELL/STOP/HOLD signals computed at read time for open operations via `_enrich_operation` (pnl_pct ≥ 10% → sell, current ≤ stop_price → stop).
- Manual CRUD endpoints (`POST/GET/PATCH close/DELETE`) tenant-scoped through `get_authed_db` + `get_current_tenant_id`, rate-limited via `slowapi`.
- Radar universe automatically extended with any ticker in the user's portfolio so held stocks always surface in signals.
- Test suite: 7 unit tests for classification, 3 service-level tests with fakeredis, 6 integration tests against the async HTTP client, and 3 auth-gate tests.

## Task Commits

Each task was committed atomically (`--no-verify` per parallel-executor protocol):

1. **Task 20-01-01: module + SwingTradeOperation model** — `1a92e26` (feat)
2. **Task 20-01-02: alembic migration 0023** — `b2f1dff` (feat)
3. **Task 20-01-03: pydantic schemas** — `ba9732b` (feat)
4. **Task 20-01-04: signal + operation service** — `98fc99a` (feat)
5. **Task 20-01-05: router with 5 endpoints** — `be9edc6` (feat)
6. **Task 20-01-06: register router in main.py** — `aefe170` (feat)
7. **Tests: unit + integration suite** — `7b516d2` (test)

Final metadata commit covers SUMMARY/STATE/ROADMAP (see below).

## Files Created/Modified

### Created

- `backend/app/modules/swing_trade/__init__.py` — package marker.
- `backend/app/modules/swing_trade/models.py` — `SwingTradeOperation` SQLAlchemy 2.x model (tenant_id, status, soft delete).
- `backend/app/modules/swing_trade/schemas.py` — 6 pydantic v2 models (signals + CRUD + enriched OperationResponse with pnl_pct/pnl_brl/days_open/live_signal).
- `backend/app/modules/swing_trade/service.py` — `compute_signals`, `get_operations`, `create_operation`, `close_operation`, `delete_operation`, `_classify_signal`, `_enrich_operation`.
- `backend/app/modules/swing_trade/router.py` — 5 endpoints under `/swing-trade`.
- `backend/alembic/versions/0023_add_swing_trade_operations.py` — down_revision=0022, dialect-gated RLS policy + index (tenant_id) and (tenant_id, status).
- `backend/tests/test_phase20_swing_trade.py` — 32 tests (classification, compute_signals, CRUD, auth).

### Modified

- `backend/app/main.py` — imports `swing_trade_router` and mounts it at `/swing-trade`.
- `backend/tests/conftest.py` — imports `app.modules.swing_trade.models` so `Base.metadata.create_all` picks up the new table in the in-memory sqlite test DB.

## Decisions Made

- **Radar universe union** — instead of duplicating RADAR_ACOES, we import it and union with the user's held tickers so a held FII/stock not in the curated list still gets a signal.
- **Dialect-gated RLS** — `ALTER TABLE ... ENABLE ROW LEVEL SECURITY` and `CREATE POLICY` only execute when `op.get_bind().dialect.name == "postgresql"`. SQLite-based tests run the table creation only, so the full alembic head is reachable from tests.
- **Unknown DY = allow BUY** — when fundamentals are stale/missing, a 30-day drop ≥ 12% still produces a BUY signal. Fundamentals staleness should not suppress otherwise valid swing opportunities.
- **Live signal is read-side only** — `live_signal` (sell/stop/hold) is computed in `_enrich_operation` from the DB row + current price. Not stored on the model, so it stays current without background recomputation.
- **Soft delete** — `deleted_at` column matches Transaction semantics; DELETE endpoint returns 204 and list queries filter on `deleted_at IS NULL`.
- **Uppercase ticker on write** — `create_operation` calls `data.ticker.upper()` to match portfolio normalization, so queries don't care about casing.
- **Conftest registration** — registering the model in `tests/conftest.py` (mirroring `_odm`, `_pm`, etc.) was the right place to keep the sqlite test DB in sync.

## Deviations from Plan

None — plan executed as written with one minor, non-semantic addition: the radar universe is unioned with the user's portfolio tickers (see Decisions). This is a 1-line fallback that makes the `in_portfolio` path reachable without requiring the held ticker to be in RADAR_ACOES, which aligns with the plan's acceptance criteria ("in_portfolio=True, include quantity").

The plan did not mention `live_signal` as a field — I added it to `OperationResponse` because task 20-01-04 specified "Add SELL signal to OperationResponse if pnl_pct >= 10" and "Add STOP signal if current_price <= stop_price", which has no natural home without a dedicated field. `live_signal` ∈ `{"hold", "sell", "stop"}` keeps the API shape strict.

## Issues Encountered

- **Alembic sqlite + asyncpg vs psycopg import**: running `alembic upgrade head` on a throwaway sqlite URL fails on migration 0001 because it uses PostgreSQL-only `DO $$ ... END $$;` for enum creation. This is pre-existing and unrelated to 0023. I verified 0023 in isolation by executing `upgrade()` against a sqlite connection via `MigrationContext.configure` + `Operations.context`, and both upgrade and downgrade passed. The production alembic chain is unchanged and correct for PostgreSQL.
- **No model registration in tests**: the first conftest change (registering `_stm`) was necessary — without it, `Base.metadata.create_all` during the session fixture would not know about `swing_trade_operations` and the integration tests would fail with "no such table". Pattern matches what every previous module already does.

## User Setup Required

None — this plan adds code only. No environment variables, no external services, no new secrets. The migration should be run on the VPS PostgreSQL during the next deploy (`alembic upgrade head`).

## Next Phase Readiness

- Plan 20-02 (frontend) can consume `GET /swing-trade/signals` and the `/operations` CRUD immediately.
- `compute_signals` will return empty lists until the existing market-data Celery beat has populated `market:quote/historical/fundamentals:*` for the radar tickers — this is already the case in production.
- RLS policy on `swing_trade_operations` is applied via 0023; `get_authed_db` already runs `SET LOCAL app.current_tenant_id` so the policy will work on PostgreSQL.
- Before shipping the frontend plan: remember to add `/swing-trade` to `frontend/middleware.ts` `PROTECTED_PATHS` (called out in 20-RESEARCH.md §6).

---

## Self-Check: PASSED

**Files verified to exist:**

- FOUND: backend/app/modules/swing_trade/__init__.py
- FOUND: backend/app/modules/swing_trade/models.py
- FOUND: backend/app/modules/swing_trade/schemas.py
- FOUND: backend/app/modules/swing_trade/service.py
- FOUND: backend/app/modules/swing_trade/router.py
- FOUND: backend/alembic/versions/0023_add_swing_trade_operations.py
- FOUND: backend/tests/test_phase20_swing_trade.py
- FOUND: backend/app/main.py (swing_trade router registration)
- FOUND: backend/tests/conftest.py (swing_trade model registration)

**Commits verified in git log:**

- FOUND: 1a92e26 feat(20-01): add SwingTradeOperation model
- FOUND: b2f1dff feat(20-01): add alembic migration 0023 for swing_trade_operations
- FOUND: ba9732b feat(20-01): add pydantic schemas for swing trade module
- FOUND: 98fc99a feat(20-01): add swing trade signal + operation service
- FOUND: be9edc6 feat(20-01): add swing trade router with 5 endpoints
- FOUND: aefe170 feat(20-01): register swing_trade router in main.py
- FOUND: 7b516d2 test(20-01): add swing trade unit + integration tests

**Verification commands from plan:**

- `python -c "from app.modules.swing_trade.models import SwingTradeOperation; print('OK')"` → OK
- `python -c "from app.modules.swing_trade.router import router; print(len(router.routes), 'routes')"` → 5 routes
- `python -m pytest tests/test_phase20_swing_trade.py` → 32 passed
- `python -m pytest tests/test_portfolio_api.py tests/test_opportunity_detector_history.py tests/test_phase20_swing_trade.py` → 65 passed (no regressions)
- Isolated sqlite migration: upgrade creates table with 15 columns + 2 indexes, downgrade drops cleanly.

---

*Phase: 20-swing-trade-page*
*Completed: 2026-04-11*
