---
phase: 05-import-broker-integration
plan: 01
subsystem: api
tags: [correpy, pdfplumber, gpt4o, celery, fastapi, sqlalchemy, pdf-parsing, csv-import, staging-workflow]

# Dependency graph
requires:
  - phase: 04-ai-analysis-engine
    provides: Celery task pattern, db_sync.py psycopg2 session, AIAnalysisJob model pattern, AWS SM key fetch
  - phase: 02-portfolio-engine-market-data
    provides: Transaction model, AssetClass/TransactionType enums, portfolio_id convention
  - phase: 01-foundation
    provides: Base declarative, RLS pattern, JWT auth, get_authed_db, get_current_tenant_id

provides:
  - ImportFile, ImportJob, ImportStaging SQLAlchemy models with indexes
  - compute_import_hash() SHA-256 duplicate detection utility
  - Alembic migration 0005 — import_files, import_jobs, import_staging tables + RLS
  - Parser cascade: correpy → pdfplumber → gpt4o (sync, Celery-compatible)
  - CSV parser with CSVTransactionRow Pydantic validation
  - parse_pdf_import + parse_csv_import Celery tasks (psycopg2, no asyncpg)
  - ImportService async service layer (7 operations)
  - FastAPI router — 7 endpoints at /imports prefix
  - Transaction.import_hash column for import deduplication

affects:
  - 05-import-broker-integration (phase 2 plans)
  - frontend import UI (future plan)

# Tech tracking
tech-stack:
  added:
    - correpy==0.6.0 (SINACOR nota de corretagem PDF parser)
    - pdfplumber==0.11.4 (table extraction fallback)
    - pdf2image==1.17.0 (PDF to images for GPT-4o vision)
    - poppler-utils (system dep in Dockerfile for pdf2image)
  patterns:
    - Parser cascade pattern: correpy → pdfplumber → gpt4o (each returns [] on failure, triggering next)
    - Staging workflow: upload → parse (async) → review → confirm/cancel
    - File bytes stored in DB (LargeBinary), never passed as Celery task arg
    - Lazy _dispatch_*_parse functions in router for Celery test isolation
    - compute_import_hash() for idempotent duplicate detection at confirm time

key-files:
  created:
    - backend/app/modules/imports/__init__.py
    - backend/app/modules/imports/models.py
    - backend/app/modules/imports/schemas.py
    - backend/app/modules/imports/service.py
    - backend/app/modules/imports/tasks.py
    - backend/app/modules/imports/router.py
    - backend/app/modules/imports/parsers/__init__.py
    - backend/app/modules/imports/parsers/correpy_parser.py
    - backend/app/modules/imports/parsers/pdfplumber_parser.py
    - backend/app/modules/imports/parsers/gpt4o_parser.py
    - backend/app/modules/imports/parsers/csv_parser.py
    - backend/alembic/versions/0005_add_import_tables.py
    - backend/tests/test_imports_api.py
    - backend/tests/test_import_parsers.py
    - backend/tests/test_import_tasks.py
    - backend/tests/fixtures/sample_nota_corretagem.pdf
    - backend/tests/fixtures/sample_import.csv
  modified:
    - backend/requirements.txt (added correpy, pdfplumber, pdf2image)
    - backend/Dockerfile (added poppler-utils)
    - backend/app/main.py (registered imports_router)
    - backend/app/modules/portfolio/models.py (added import_hash column to Transaction)
    - backend/tests/conftest.py (fixed namespace collision, registered ImportFile/Job/Staging models)

key-decisions:
  - "File bytes stored as LargeBinary in import_files — never passed as Celery task arg (Redis message size limit)"
  - "Parser cascade returns [] on failure to trigger next parser — no exceptions propagated upward"
  - "correpy _normalize_ticker: regex for B3-format ticker + fracionario F suffix removal"
  - "Duplicate detection uses ORM query (not raw SQL) for SQLite test compatibility"
  - "conftest.py model imports use 'as _pm' aliases to prevent rebinding the FastAPI 'app' variable"
  - "Transaction.import_hash added to ORM model (not just migration) so test SQLite DB includes it"
  - "gpt4o_parser uses requests (sync) not httpx.AsyncClient — called from Celery worker context"

patterns-established:
  - "Parser cascade: each parser function returns [] on failure, never raises — triggers cascade automatically"
  - "Celery task reads file bytes from DB by file_id — prevents Redis message overflow for large PDFs"
  - "Staging workflow: ParseJob → staged rows → user confirm — transactions written only after confirm"
  - "ImportService.confirm_import: batch duplicate detection via existing import_hash set, within-batch dedup too"

requirements-completed:
  - IMP-01
  - IMP-02
  - IMP-03

# Metrics
duration: 21min
completed: 2026-03-15
---

# Phase 5 Plan 01: Import Broker Integration Backend Summary

**Complete broker import pipeline: PDF nota de corretagem parser cascade (correpy/pdfplumber/GPT-4o), CSV validator with Pydantic, Celery tasks with psycopg2, and 7 FastAPI endpoints for the upload/review/confirm workflow**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-15T19:07:30Z
- **Completed:** 2026-03-15T19:28:30Z
- **Tasks:** 3
- **Files modified:** 22

## Accomplishments

- ImportFile/ImportJob/ImportStaging SQLAlchemy models with Alembic migration 0005 including RLS policies and import_hash UniqueConstraint on staging
- Parser cascade (correpy primary, pdfplumber fallback, gpt4o vision last resort) with _normalize_ticker() for B3 SINACOR format
- CSVTransactionRow Pydantic model with field validation for asset_class and transaction_type enums
- parse_pdf_import and parse_csv_import Celery tasks using psycopg2 (db_sync) with file bytes read from DB
- FastAPI router with 7 endpoints: upload PDF/CSV, poll job, confirm (dedup), cancel, reparse, history, template download
- 26 tests passing across 3 test files (API x2 event loops, parsers, tasks)

## Task Commits

1. **Task 1: Test stubs + fixtures** - `31535e8` (test)
2. **Task 2: Models, migration, parsers** - `caf2e81` (feat)
3. **Task 3: Celery tasks, service, router** - `f21b491` (feat)

## Files Created/Modified

- `backend/app/modules/imports/models.py` - ImportFile, ImportJob, ImportStaging + compute_import_hash()
- `backend/app/modules/imports/parsers/correpy_parser.py` - parse_with_correpy() + _normalize_ticker()
- `backend/app/modules/imports/parsers/pdfplumber_parser.py` - Table extraction with SINACOR TABLE_SETTINGS
- `backend/app/modules/imports/parsers/gpt4o_parser.py` - Vision-based parser via requests (sync)
- `backend/app/modules/imports/parsers/csv_parser.py` - CSVTransactionRow + parse_csv()
- `backend/app/modules/imports/tasks.py` - parse_pdf_import + parse_csv_import Celery tasks
- `backend/app/modules/imports/service.py` - ImportService (create, get, confirm, cancel, reparse, list)
- `backend/app/modules/imports/router.py` - 7 FastAPI endpoints
- `backend/alembic/versions/0005_add_import_tables.py` - Migration with RLS + import_hash on transactions
- `backend/app/modules/portfolio/models.py` - Added Transaction.import_hash column
- `backend/app/main.py` - Registered imports_router at /imports
- `backend/tests/conftest.py` - Fixed 'app' namespace collision + registered imports models

## Decisions Made

- File bytes stored as LargeBinary in import_files — never passed as Celery task arg (Redis message size limit for 5-10MB PDFs)
- Parser cascade returns [] on failure, never raises — clean cascade trigger without exception handling overhead
- Duplicate detection uses ORM query (not raw SQL `SELECT import_hash`) for SQLite test DB compatibility
- Transaction.import_hash added to ORM model AND migration so test SQLite DB includes the column

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Transaction.import_hash missing from ORM model**
- **Found during:** Task 3 (confirm_import service)
- **Issue:** Plan specified adding import_hash only in migration 0005, but test SQLite DB is built from ORM metadata (Base.metadata.create_all). The column was absent in test DB, causing `OperationalError: no such column: import_hash`.
- **Fix:** Added `import_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)` to Transaction model in portfolio/models.py
- **Files modified:** backend/app/modules/portfolio/models.py
- **Verification:** test_confirm_writes_transactions and test_duplicate_detection pass
- **Committed in:** f21b491 (Task 3 commit)

**2. [Rule 1 - Bug] conftest.py 'import app.modules.*' rebinded FastAPI 'app' variable**
- **Found during:** Task 3 (running API tests)
- **Issue:** `import app.modules.portfolio.models` (bare import) binds the top-level `app` package to the local `app` name, overwriting the FastAPI instance imported via `from app.main import app`. This caused `AttributeError: module 'app' has no attribute 'dependency_overrides'` in the client fixture.
- **Fix:** Changed all bare `import app.modules.*` lines in conftest.py to use `as _pm`, `as _aim`, `as _im` aliases to avoid namespace collision.
- **Files modified:** backend/tests/conftest.py
- **Verification:** `python -m pytest tests/test_auth.py` passes (40 tests), all import tests pass
- **Committed in:** f21b491 (Task 3 commit)

**3. [Rule 2 - Missing Critical] Raw SQL for import_hash query replaced with ORM query**
- **Found during:** Task 3 (running confirm tests on SQLite)
- **Issue:** `text("SELECT import_hash FROM transactions WHERE ...")` is PostgreSQL-only syntax for column selection in some SQLite contexts.
- **Fix:** Replaced raw SQL with `select(_Transaction.import_hash).where(...)` ORM query.
- **Files modified:** backend/app/modules/imports/service.py
- **Verification:** test_confirm_writes_transactions and test_duplicate_detection pass on SQLite
- **Committed in:** f21b491 (Task 3 commit)

---

**Total deviations:** 3 auto-fixed (2 Rule 1 bugs, 1 Rule 2 missing critical)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

Pre-existing: test_ai_pipeline.py tests fail with Redis ConnectionRefusedError — the slowapi rate limiter tries to connect to a real Redis instance. This was failing before this plan and is not caused by these changes. 26 import tests pass; 140 other tests pass; only AI pipeline + RLS tests require external services.

## Next Phase Readiness

- Complete import backend: models, migration, parsers, tasks, service, router all implemented
- Frontend import UI ready to be built (Phase 5 Plan 02+)
- Real XP/Clear PDF fixtures needed for integration testing with actual broker notes (pre-existing concern)

## Self-Check: PASSED

All key files confirmed present. All task commits verified in git log.
- backend/app/modules/imports/models.py: FOUND
- backend/app/modules/imports/tasks.py: FOUND
- backend/app/modules/imports/router.py: FOUND
- backend/app/modules/imports/service.py: FOUND
- backend/alembic/versions/0005_add_import_tables.py: FOUND
- 31535e8 (test stubs): FOUND
- caf2e81 (models + parsers): FOUND
- f21b491 (tasks + router + service): FOUND

---
*Phase: 05-import-broker-integration*
*Completed: 2026-03-15*
