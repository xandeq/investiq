---
phase: 07-foundation-data-pipelines
plan: 01
subsystem: database
tags: [sqlalchemy, alembic, postgres, celery, tax-engine, market-universe, rls, global-tables]

# Dependency graph
requires:
  - phase: 06-monetization
    provides: alembic migration chain through 0014_add_trial_fields (down_revision for 0015)
provides:
  - 4 global SQLAlchemy 2.x models (ScreenerSnapshot, FIIMetadata, FixedIncomeCatalog, TaxConfig)
  - Alembic migration 0015 creating all 4 tables with indexes, GRANTs, and seed data
  - get_global_db async FastAPI dependency (no SET LOCAL rls.tenant_id)
  - TaxEngine service class with get_rate(), is_exempt(), net_return(), from_db()
  - 20 unit tests covering models, get_global_db, and TaxEngine
affects:
  - 07-02 (Celery beat tasks write to screener_snapshots, fii_metadata via get_sync_db_session)
  - 08-screener (reads screener_snapshots via get_global_db)
  - 09-renda-fixa (reads fixed_income_catalog, uses TaxEngine via get_global_db)
  - 10-allocation (uses TaxEngine net_return for comparison)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Global table pattern: no tenant_id column, no RLS policy, GRANT to app_user instead"
    - "get_global_db: same async_session_factory as get_tenant_db but without SET LOCAL"
    - "TaxEngine: DB-driven rates injected at init, pure Python after that - no per-call DB hit"
    - "TDD: test file written first (RED), implementation second (GREEN), 16 tests for TaxEngine"

key-files:
  created:
    - backend/app/modules/market_universe/__init__.py
    - backend/app/modules/market_universe/models.py
    - backend/app/modules/market_universe/tax_engine.py
    - backend/alembic/versions/0015_add_market_universe_tables.py
    - backend/tests/test_tax_engine.py
    - backend/tests/test_global_db.py
  modified:
    - backend/app/core/db.py (added get_global_db)
    - backend/tests/conftest.py (AUTH_DATABASE_URL fix + market_universe model registration)

key-decisions:
  - "Global tables use GRANT SELECT/INSERT/UPDATE/DELETE instead of RLS - app_user has direct access since no per-tenant data"
  - "TaxEngine accepts pre-loaded rows (not a session) to enable pure unit testing without DB fixtures"
  - "Composite unique constraint on (ticker, snapshot_date) enables INSERT ON CONFLICT for daily screener upserts"
  - "AUTH_DATABASE_URL must be set to sqlite+aiosqlite in test env - was missing from conftest (pre-existing bug)"

patterns-established:
  - "Pattern: Global table = no tenant_id + no RLS + GRANT to app_user + use get_global_db or get_sync_db_session(None)"
  - "Pattern: TaxEngine per-request instantiation (not module-level singleton) - picks up DB changes after restart"
  - "Pattern: Mock config rows using @dataclass for unit testing service classes that read from DB"

requirements-completed:
  - SCRA-04

# Metrics
duration: 8min
completed: 2026-03-22
---

# Phase 7 Plan 01: Market Universe Foundation Summary

**4 global PostgreSQL tables (screener_snapshots, fii_metadata, fixed_income_catalog, tax_config) via Alembic migration 0015 with seed data, get_global_db async dependency, and TaxEngine IR regressivo calculator with 20 unit tests**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-22T04:39:27Z
- **Completed:** 2026-03-22T04:47:30Z
- **Tasks:** 2
- **Files modified:** 8 (6 created + 2 modified)

## Accomplishments

- Created `market_universe` module with 4 SQLAlchemy 2.x models using `Mapped[T]` + `mapped_column()` — zero `tenant_id` columns, zero RLS policies
- Created Alembic migration 0015 with 4 global tables, composite unique constraint on (ticker, snapshot_date), 3 indexes, 5 GRANT statements, 7 tax_config seed rows, 14 fixed_income_catalog seed rows
- Added `get_global_db` async FastAPI dependency to `db.py` — uses `async_session_factory` without `SET LOCAL rls.tenant_id`
- Implemented `TaxEngine` with `get_rate()`, `is_exempt()`, `net_return()`, `from_db()` — DB-driven rates (no hardcoded constants), instantiate per-request
- 20 unit tests: 4 for get_global_db (no RLS injection verified), 16 for TaxEngine (all 4 IR tiers, 6 boundary values, 3 exempt classes, net_return)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create market_universe module with models and Alembic migration 0015** - `b0a5a97` (feat)
2. **Task 2: Implement TaxEngine service class with unit tests** - `f5de9f3` (feat, TDD)

## Files Created/Modified

- `backend/app/modules/market_universe/__init__.py` - Empty module init
- `backend/app/modules/market_universe/models.py` - ScreenerSnapshot, FIIMetadata, FixedIncomeCatalog, TaxConfig (no tenant_id)
- `backend/app/modules/market_universe/tax_engine.py` - TaxEngine with DB-driven IR rates
- `backend/alembic/versions/0015_add_market_universe_tables.py` - Migration creating 4 global tables + GRANT + 21 seed rows
- `backend/tests/test_global_db.py` - 4 unit tests verifying no SET LOCAL injection
- `backend/tests/test_tax_engine.py` - 16 unit tests (TDD) using MockTaxConfig dataclass stubs
- `backend/app/core/db.py` - Added get_global_db async generator
- `backend/tests/conftest.py` - Fixed AUTH_DATABASE_URL env var + registered market_universe models

## Decisions Made

- **Global table access pattern:** Tables use `GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO app_user` instead of RLS. Since these are universe-level tables (not per-tenant), RLS would require a fake tenant context. Direct GRANT is correct.
- **TaxEngine constructor accepts rows (not session):** Enables pure unit testing with MockTaxConfig dataclasses — no DB, no fixtures, no mocking of SQLAlchemy. Phases 8/9/10 pass pre-loaded rows from `get_global_db`.
- **Instantiate TaxEngine per-request:** Tax rates in `tax_config` can be updated via direct SQL. Module-level singleton would serve stale rates after DB update until restart. Per-request init is fast (10 rows).
- **Composite unique on (ticker, snapshot_date):** Required for `INSERT INTO screener_snapshots ... ON CONFLICT (ticker, snapshot_date) DO UPDATE` pattern used by Plan 02 Celery tasks.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Fixed AUTH_DATABASE_URL missing from test conftest**
- **Found during:** Task 1 verification (`python -m pytest tests/test_global_db.py`)
- **Issue:** conftest.py set `DATABASE_URL=sqlite+aiosqlite:///:memory:` but not `AUTH_DATABASE_URL`. When `db.py` imported, `_auth_engine = create_async_engine(settings.AUTH_DATABASE_URL)` tried to use the default `postgresql+asyncpg://` URL, causing `ModuleNotFoundError: No module named 'asyncpg'` (asyncpg not installed locally — backend runs in Docker).
- **Fix:** Added `os.environ["AUTH_DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"` to conftest before app import. Also added `market_universe` models import so `Base.metadata.create_all()` covers the new tables.
- **Files modified:** `backend/tests/conftest.py`
- **Verification:** All 4 test_global_db tests pass
- **Committed in:** `b0a5a97` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking issue)
**Impact on plan:** Pre-existing test infrastructure gap (AUTH_DATABASE_URL not set). Fix was minimal and necessary. No scope creep.

## Issues Encountered

- `asyncpg` not installed in local Windows Python environment — expected, backend runs in Docker. Tests use `sqlite+aiosqlite` via conftest. All tests pass.

## User Setup Required

None — no external service configuration required. Alembic migration 0015 runs against the existing PostgreSQL DB when `alembic upgrade head` is executed during next deploy.

## Next Phase Readiness

- Plan 02 (Celery beat tasks) can write to `screener_snapshots`, `fii_metadata` via `get_sync_db_session(tenant_id=None)`
- Phases 8, 9, 10 can read via `get_global_db` FastAPI dependency
- TaxEngine is importable and tested: `from app.modules.market_universe.tax_engine import TaxEngine`
- No blockers

---
*Phase: 07-foundation-data-pipelines*
*Completed: 2026-03-22*
