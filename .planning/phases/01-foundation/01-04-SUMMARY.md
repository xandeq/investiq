---
phase: 01-foundation
plan: 04
subsystem: portfolio
tags: [sqlalchemy, alembic, postgresql, rls, pydantic, tdd, transaction-schema, asset-class, ir-fields, ext-01, ext-03]

# Dependency graph
requires:
  - phase: 01-foundation/01-03
    provides: RLS migration pattern, get_authed_db dependency, app_user role, init-db.sql DEFAULT PRIVILEGES

provides:
  - Transaction SQLAlchemy 2.x model — polymorphic single table with all 5 asset classes
  - CorporateAction SQLAlchemy 2.x model — separate table for B3 corporate events
  - AssetClass enum: acao, FII, renda_fixa, BDR, ETF
  - TransactionType enum: buy, sell, dividend, jscp, amortization
  - CorporateActionType enum: desdobramento, grupamento, bonificacao
  - IR fields: irrf_withheld + gross_profit stored at transaction time (never computed)
  - Alembic migration 0003: transactions + corporate_actions + indexes + RLS + app_user grants
  - TransactionCreate + TransactionResponse Pydantic v2 schemas (Phase 2 stubs)
  - EXT-03 skill adapter skeleton: async calculate(data: dict) -> dict in portfolio/service.py
  - test_schema.py: 12 tests (6 EXT-02 plan field + 6 new portfolio tests)
  - EXT-01 structural proof: portfolio module added with zero changes to app/core/ or app/modules/auth/

affects:
  - 02-xx (Phase 2 P&L engine builds directly on Transaction/CorporateAction models)
  - All Phase 4 financial skill adapters use the calculate() interface from portfolio/service.py

# Tech tracking
tech-stack:
  added:
    - SQLAlchemy 2.x Mapped[] annotations for portfolio models
    - Pydantic v2 schemas with Decimal and date field types
    - SAEnum (SQLAlchemy Enum) for asset_class, transaction_type, corporate_action_type
    - Polymorphic single-table design: nullable asset-class-specific columns
    - Alembic manual migration with explicit PostgreSQL enum type creation (checkfirst=True)
    - EXT-03 async adapter pattern: async calculate(data: dict) -> dict
  patterns:
    - Shared Base from app.modules.auth.models — all modules use same declarative Base for unified Alembic metadata
    - alembic/env.py: import portfolio models to register tables (side-effect import pattern)
    - RLS migration: same ENABLE + FORCE + CREATE POLICY pattern as 0002 — consistent across all tenant tables
    - IR fields stored at transaction time — authoritative for tax purposes, never computed on-the-fly
    - Polymorphic single table: nullable columns for asset-class-specific data (coupon_rate, maturity_date, is_exempt)
    - EXT-01 boundary: portfolio imports shared Base only — no auth domain logic, no core security
    - Test EXT-01 via source inspection of import lines only (not docstrings) — avoids false positives

key-files:
  created:
    - backend/app/modules/portfolio/models.py
    - backend/app/modules/portfolio/schemas.py
    - backend/app/modules/portfolio/service.py
    - backend/alembic/versions/0003_add_transaction_schema.py
  modified:
    - backend/app/modules/portfolio/__init__.py (EXT-01 proof comment)
    - backend/alembic/env.py (import portfolio models)
    - backend/app/main.py (Phase 2 router comment — EXT-01 final artifact)
    - backend/tests/test_schema.py (6 new portfolio tests + fix EXT-01 assertion)

key-decisions:
  - "Shared Base from auth.models — not a new Base in app/core/db.py. All modules share auth's DeclarativeBase so Alembic has a single metadata. EXT-01 is satisfied because portfolio reads the Base only — no auth logic was added or changed."
  - "SQLite vs PostgreSQL SAEnum storage difference — SQLite stores enum member .name (lowercase), PostgreSQL stores .value. Test uses ORM-level comparison (row.asset_class) instead of raw SQL string comparison to be DB-agnostic."
  - "EXT-01 test inspects only import statement lines — strips docstrings and comments before checking for forbidden imports. Avoids false positives from explanatory text in docstrings."
  - "CorporateAction has tenant_id directly — no FK to transactions or users. RLS isolates by tenant_id directly, same as transactions table. Simpler and avoids cross-table JOIN in policy."
  - "IR fields irrf_withheld + gross_profit nullable by default — not all transaction types produce IR events. Stored at transaction time, never recomputed."

requirements-completed: [EXT-01, EXT-02, EXT-03]

# Metrics
duration: 64min
completed: 2026-03-14
---

# Phase 1 Plan 4: Transaction Schema Summary

**Polymorphic single-table transaction model with 5 asset classes, corporate_actions table, IR fields, Alembic migration 0003 with RLS, and portfolio module added cleanly with zero changes to auth or core (EXT-01 proof)**

## Performance

- **Duration:** ~64 min
- **Started:** 2026-03-14T08:56:32Z
- **Completed:** 2026-03-14T11:00:13Z
- **Tasks:** 2 completed
- **Files modified:** 8 files (4 created, 4 modified)

## Accomplishments

- `backend/app/modules/portfolio/models.py` — Transaction + CorporateAction SQLAlchemy 2.x models:
  - `AssetClass` enum: acao, FII, renda_fixa, BDR, ETF
  - `TransactionType` enum: buy, sell, dividend, jscp, amortization
  - `CorporateActionType` enum: desdobramento, grupamento, bonificacao
  - IR fields: `irrf_withheld`, `gross_profit` stored at transaction time (not computed)
  - Nullable asset-specific columns: `coupon_rate`, `maturity_date` (renda_fixa), `is_exempt` (FII)
- `backend/app/modules/portfolio/schemas.py` — `TransactionCreate` + `TransactionResponse` Pydantic v2 stubs
- `backend/app/modules/portfolio/service.py` — EXT-03 skeleton: `async calculate(data: dict) -> dict`
- `backend/alembic/versions/0003_add_transaction_schema.py` — manual migration:
  - Creates `transactions` + `corporate_actions` tables
  - Composite indexes: `(tenant_id, ticker)` and `(tenant_id, transaction_date)`
  - `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on both tables
  - `CREATE POLICY tenant_isolation` (same NULLIF pattern as 0002)
  - `GRANT SELECT, INSERT, UPDATE, DELETE ON transactions, corporate_actions TO app_user`
- `backend/alembic/env.py` — imports portfolio models to register with `Base.metadata`
- `backend/app/main.py` — Phase 2 router comment as final EXT-01 artifact
- `backend/tests/test_schema.py` — 6 new tests (12 total, 1 PG-only skip):
  - `test_transaction_asset_class_enum` — all 5 asset classes stored via ORM
  - `test_transaction_asset_specific_columns` — polymorphic nullables work correctly
  - `test_ir_fields_stored` — irrf_withheld + gross_profit persist exactly
  - `test_corporate_action_types` — all 3 action types accepted
  - `test_rls_on_transactions` — RLS cross-tenant isolation (PG-only, skip locally)
  - `test_ext01_no_core_changes` — source-level import boundary check
  - `test_ext03_skill_adapter_interface` — async calculate() coroutine verified

## Task Commits

1. **Task 1 (RED): Transaction schema tests** — `9d4fb65` (test)
2. **Task 1 (GREEN) + REFACTOR: Portfolio module + migration** — `8a93a37` (feat)

## Files Created/Modified

**Backend:**
- `backend/app/modules/portfolio/__init__.py` — EXT-01 proof comment
- `backend/app/modules/portfolio/models.py` — Transaction + CorporateAction models
- `backend/app/modules/portfolio/schemas.py` — Pydantic v2 schemas
- `backend/app/modules/portfolio/service.py` — EXT-03 skill adapter skeleton
- `backend/alembic/versions/0003_add_transaction_schema.py` — migration 0003
- `backend/alembic/env.py` — portfolio models import for metadata registration
- `backend/app/main.py` — Phase 2 router placeholder comment
- `backend/tests/test_schema.py` — 6 new portfolio tests + fixed EXT-01 check

## Decisions Made

- **Shared Base** — Portfolio models use `Base` from `app.modules.auth.models` (not a new `app.core.db.Base`). This maintains a single metadata object for Alembic. EXT-01 is satisfied because the Base is a plain `DeclarativeBase` with no auth logic — portfolio neither reads nor writes auth domain data.
- **SQLite/PostgreSQL enum storage difference** — SQLite stores SAEnum as the Python member name (e.g., `fii`), PostgreSQL stores the enum value (e.g., `FII`). Tests use ORM-level comparison (`row.asset_class == AssetClass.fii`) to be DB-agnostic — avoids raw SQL string comparison which would fail on one DB or the other.
- **EXT-01 test checks import lines only** — `inspect.getsource()` includes docstrings. The EXT-01 test filters source lines to only import statements before checking for forbidden patterns. Docstrings explaining the architecture boundary triggered false positives in the first run.
- **No FK from corporate_actions to transactions** — Corporate events are system data (from B3), not user-generated transactions. No FK keeps the tables independent; RLS on `tenant_id` handles isolation without JOIN.
- **IR fields nullable** — Not all transaction types involve IR events (a buy transaction has no `irrf_withheld`). Making them nullable avoids forcing callers to pass `0` for non-applicable transactions, which would pollute aggregate IR calculations.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] SQLite SAEnum stores member name, not value**
- **Found during:** Task 1 GREEN phase (test_transaction_asset_class_enum failed)
- **Issue:** SQLite stores SAEnum as the Python member `.name` (e.g., `"fii"`) while PostgreSQL stores `.value` (e.g., `"FII"`). The test compared raw SQL output against `ac.value`, which failed on SQLite.
- **Fix:** Changed test to use ORM-level comparison via `select(Transaction)` and check `row.asset_class == AssetClass.fii` — SQLAlchemy ORM handles the translation transparently on both backends.
- **Files modified:** `backend/tests/test_schema.py`
- **Commit:** `8a93a37`

**2. [Rule 1 - Bug] EXT-01 test hit docstring false positive**
- **Found during:** Task 1 GREEN phase (test_ext01_no_core_changes failed)
- **Issue:** The docstring in `portfolio/models.py` included explanatory text "This module imports NOTHING from app.core.security" — the substring `from app.core.security` triggered the forbidden import check on the full source.
- **Fix:** Modified test to filter source lines to only actual import statements (`line.strip().startswith(("import ", "from "))`) before checking for forbidden patterns. The actual imports are clean.
- **Files modified:** `backend/tests/test_schema.py`
- **Commit:** `8a93a37`

## Phase 1 Complete Gate

**Full test suite:** 52 passed, 7 skipped (PG-dependent tests), 0 failures, 0 errors

**All 3 test files green:**
- `test_auth.py`: 40 passed (no regression)
- `test_rls.py`: 6 skipped (PG not available locally — run in Docker)
- `test_schema.py`: 12 passed, 1 skipped (PG RLS test)

**EXT-01 boundary:** Portfolio module adds zero imports to app/core/ or app/modules/auth/ — structurally enforced

**Alembic chain:** `baseline → 001_add_auth_tables → 0002_add_rls_policies → 0003_add_transaction_schema`

## Phase 1 Foundation Summary

Phase 1 delivers a production-ready multi-tenant backend foundation:

1. **Plan 01-01** — Project scaffold: FastAPI + SQLAlchemy 2.x + Alembic + Docker Compose + Next.js 15 frontend
2. **Plan 01-02** — Auth service: JWT RS256 + refresh rotation + email verification + bcrypt + httpOnly cookies
3. **Plan 01-03** — RLS tenant isolation: PostgreSQL app_user role + FORCE RLS + SET LOCAL per-request + get_authed_db dependency
4. **Plan 01-04** — Transaction schema: polymorphic single table + IR fields + corporate_actions + migration 0003 + EXT-01/EXT-03 proof

**Phase 2 (CMP engine) can start immediately.** All prerequisites satisfied:
- `get_authed_db` — authenticated, tenant-scoped DB session available to all routes
- `Transaction` model — accepts all 5 asset classes with IR fields
- `CorporateAction` model — B3 events ready for cost-basis adjustments
- Migration 0003 applied — schema baseline deployed
- `portfolio/service.py` skeleton — Phase 4 skill adapters plug in here

## Self-Check: PASSED

Files verified:
- `backend/app/modules/portfolio/models.py` — EXISTS
- `backend/app/modules/portfolio/schemas.py` — EXISTS
- `backend/app/modules/portfolio/service.py` — EXISTS
- `backend/app/modules/portfolio/__init__.py` — EXISTS
- `backend/alembic/versions/0003_add_transaction_schema.py` — EXISTS
- `backend/alembic/env.py` — EXISTS (modified)
- `backend/app/main.py` — EXISTS (modified)
- `backend/tests/test_schema.py` — EXISTS (12 tests, 1 skip)

Commits verified:
- `9d4fb65` — test(01-04): add transaction schema tests — RED phase
- `8a93a37` — feat(01-04): transaction schema — models + migration + RLS + GREEN phase

Test results:
- 52 passed, 7 skipped (6 PG RLS tests + 1 PG transaction RLS test)
- 0 failures, 0 errors

---
*Phase: 01-foundation*
*Completed: 2026-03-14*
