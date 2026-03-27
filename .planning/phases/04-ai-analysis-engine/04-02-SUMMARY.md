---
phase: 04-ai-analysis-engine
plan: 02
subsystem: backend/ai-pipeline
tags: [ai, fastapi, alembic, slowapi, rate-limiting, async-pipeline]
requires: [04-01]
provides: [ai-router, ai-analysis-jobs-table, rate-limiter]
affects: [backend/app/modules/ai, backend/app/main.py, backend/app/core]
tech_stack_added: [slowapi==0.1.9]
tech_stack_patterns: [202-accepted-polling, premium-gate, db-write-back-from-celery]
key_files_created:
  - backend/app/modules/ai/models.py
  - backend/app/modules/ai/schemas.py
  - backend/app/modules/ai/router.py
  - backend/app/core/limiter.py
  - backend/alembic/versions/0004_add_ai_analysis_jobs.py
  - backend/tests/test_ai_pipeline.py
key_files_modified:
  - backend/app/modules/ai/tasks.py
  - backend/app/main.py
  - backend/requirements.txt
decisions:
  - "Plan field read from DB on each POST request (not JWT) — avoids stale plan state in long-lived tokens"
  - "Portfolio allocation fetched inline in POST /ai/analyze/macro — non-fatal if fetch fails (empty allocation passed)"
  - "Celery task dispatch wrapped in try/except — job stays 'pending' but response is not blocked by dispatch failure"
  - "slowapi uses Redis storage_uri from settings.REDIS_URL — same Redis instance as Celery"
metrics:
  completed_date: "2026-03-15"
  tasks_completed: 5
  files_created: 6
  files_modified: 3
---

# Phase 4 Plan 02: Async Analysis Pipeline Summary

## One-liner

Full async job pipeline with ai_analysis_jobs DB table, 4 REST endpoints, 403 premium gate, slowapi rate limiting (5/hour), and Celery write-back.

## What Was Built

### DB Model + Migration

`AIAnalysisJob` model with fields: id (UUID), tenant_id (indexed), job_type, ticker (nullable), status, result_json (Text), error_message, created_at, completed_at. Alembic migration `0004_add_ai_analysis_jobs.py` creates the table with two composite indexes: `(tenant_id, status)` and `(tenant_id, created_at)`.

### Pydantic Schemas

`AnalysisRequest`, `MacroAnalysisRequest`, `JobResponse`, `JobResultResponse` (extends with `result: dict | None`).

### AI Router (4 endpoints)

- `POST /ai/analyze/{ticker}` — premium-gated, rate-limited (5/hour), creates pending job, dispatches Celery task, returns 202
- `POST /ai/analyze/macro` — same pattern, fetches portfolio allocation from PortfolioService for context
- `GET /ai/jobs/{job_id}` — returns job status + parsed result_json when completed
- `GET /ai/jobs` — last 10 jobs for current tenant

Premium gate reads `plan` from DB (not JWT) on every POST request. Free users receive HTTP 403 with upgrade message.

### Rate Limiter

`app/core/limiter.py` — slowapi `Limiter` with Redis storage. Registered in main.py with `RateLimitExceeded` exception handler.

### Celery Write-back

`_update_job_status()` in `tasks.py` writes `status`, `result_json`, `completed_at`, `error_message` back to DB after each task run.

## Deviations from Plan

None — plan executed exactly as written. All components were already present (previous planning session had scaffolded them).

## Self-Check: PASSED

- `backend/app/modules/ai/router.py` — 4 endpoints present
- `backend/app/modules/ai/models.py` — AIAnalysisJob model present
- `backend/alembic/versions/0004_add_ai_analysis_jobs.py` — migration file present
- `backend/app/core/limiter.py` — slowapi limiter present
- `backend/app/main.py` — ai_router registered, limiter integrated
- Commit `3c20dbf` covers all these files
