---
phase: 02-portfolio-engine-market-data
plan: "02-01"
subsystem: infrastructure
tags: [celery, redis, background-tasks, market-data, psycopg2]
dependency_graph:
  requires: []
  provides: [celery-worker-service, celery-beat-service, celery-app-factory, sync-db-engine]
  affects: [02-02-market-data-tasks, 02-03-portfolio-calculations]
tech_stack:
  added: [celery==5.4.0, psycopg2-binary==2.9.9, python-bcb==0.3.1, yfinance==0.2.51, fakeredis==2.26.2, pandas==2.2.0, requests==2.32.3]
  patterns: [celery-beat-separate-service, lazy-engine-init, sync-session-for-async-app]
key_files:
  created:
    - backend/app/celery_app.py
    - backend/app/core/db_sync.py
    - backend/tests/test_market_data_tasks.py
  modified:
    - backend/requirements.txt
    - backend/tests/conftest.py
    - docker-compose.yml
decisions:
  - celery-beat-separate-docker-service
  - psycopg2-for-celery-not-asyncpg
  - lazy-sync-engine-init
metrics:
  duration: 6
  completed_date: "2026-03-14"
  tasks_completed: 3
  files_changed: 6
---

# Phase 02 Plan 01: Celery + Redis Infrastructure Summary

**One-liner:** Celery worker/beat Docker services with Redis broker, beat_schedule for B3 market hours (15min quotes, 6h macro), and psycopg2 sync engine for worker DB access.

## What Was Built

### `backend/app/celery_app.py`
Celery app factory (`create_celery_app`) using Redis as both broker and result backend. Beat schedule:
- `refresh-quotes-market-hours`: every 15 min, Mon-Fri, 10h-17h BRT (B3 market hours)
- `refresh-macro-every-6h`: every 6 hours (SELIC/CDI/IPCA not time-sensitive)

Task modules included: `app.modules.market_data.tasks` (to be created in 02-02).

### `backend/app/core/db_sync.py`
Synchronous SQLAlchemy engine for Celery workers. Key design:
- Lazy initialization (no DB connection at import time — tests safe)
- `_build_sync_url()` converts `postgresql+asyncpg://` to `postgresql+psycopg2://`
- `get_sync_db_session(tenant_id=None)` context manager with proper rollback
- Optional RLS tenant context (`SET LOCAL rls.tenant_id`) for future tenant-scoped tasks

### Docker Compose Services
Two new services added after `backend`:
- `celery-worker`: `celery -A app.celery_app worker --loglevel=info --concurrency=2`
- `celery-beat`: `celery -A app.celery_app beat --loglevel=info --scheduler celery.beat.PersistentScheduler`

Beat runs as a SEPARATE service — not embedded in worker — to avoid duplicate task scheduling when scaling workers.

### Test Infrastructure
- `backend/tests/test_market_data_tasks.py`: 4 test stubs (broker alive, Redis write, brapi client, macro)
- `backend/tests/conftest.py`: Added `fake_redis_sync`, `fake_redis_async`, `mock_brapi_client` fixtures

## Decisions Made

**1. celery-beat-separate-docker-service**
Beat runs as its own Docker service using `PersistentScheduler`. If beat were embedded in the worker (`celery worker --beat`), scaling the worker to multiple instances would cause duplicate task execution. Separate service eliminates this risk permanently.

**2. psycopg2-for-celery-not-asyncpg**
Celery tasks are synchronous. The existing FastAPI app uses `asyncpg` (async-only). Importing the async session factory inside a Celery task would fail. `db_sync.py` uses `psycopg2-binary` with a dedicated sync engine — two separate engines coexist without conflict.

**3. lazy-sync-engine-init**
The sync engine is created on first use, not at module import time. This prevents import-time DB connection errors in test environments (where `DATABASE_URL` is SQLite) and in CI. The engine is a module-level singleton once created.

## Verification Results

```
pytest tests/test_market_data_tasks.py::test_celery_broker_alive    PASSED
pytest tests/ -x -q    56 passed, 7 skipped (all passing, no regressions)
docker-compose.yml YAML validation    OK
```

## Deviations from Plan

**1. [Rule 3 - Blocking] Installed celery locally for test execution**
- **Found during:** Task 2 verification
- **Issue:** `celery` package not installed in local Python env (only in Docker); `test_celery_broker_alive` was skipping via `pytest.skip`
- **Fix:** Installed `celery==5.4.0` locally with `pip install celery==5.4.0`
- **Files modified:** none (local env change only)
- **Impact:** Test now passes in both local and Docker contexts

## Self-Check: PASSED

- FOUND: backend/app/celery_app.py
- FOUND: backend/app/core/db_sync.py
- FOUND: backend/tests/test_market_data_tasks.py
- FOUND: .planning/phases/02-portfolio-engine-market-data/02-01-SUMMARY.md
- FOUND commit 8ab62af: test(02-01) Wave 0 test stubs
- FOUND commit 9322981: chore(02-01) Docker services and dependencies
- FOUND commit ab9b561: feat(02-01) Celery app factory and sync DB engine
