---
phase: 15-data-quality-advanced-features
plan: 02
type: summary
status: done
date: 2026-04-03
commit: 86721ef
---

# Phase 15-02 Summary — Data Quality Flags + History Endpoint

## What was done

### history.py (new module)
- `get_completeness_flag(completeness_dict)` — green ≥ 80%, yellow ≥ 50%, red < 50%
- `get_analysis_history(ticker, tenant_id, ...)` — returns completed/stale analyses, tenant-scoped, newest first, max 50
- `compute_analysis_diff(old, new, type)` — pct_change per metric, suppresses < 1% noise, ZeroDivision-safe

### tasks.py (4 result builders updated)
- `completeness_flag` injected into DCF, earnings, dividend, sector result dicts
- Sector uses `peers_with_data / peers_attempted` to compute flag
- Import: `from app.modules.analysis.history import get_completeness_flag`

### schemas.py
- Added `AnalysisHistoryItem` Pydantic model

### router.py
- Added `GET /analysis/history/{ticker}` endpoint
- Placed **before** `/{job_id}` catch-all (lines 487 vs 517) — critical for FastAPI route matching
- Supports `?analysis_type=dcf|earnings|dividend|sector` and `?limit=1-50`
- Tenant-scoped via `get_current_tenant_id` dependency

### Frontend fix (bonus)
- Fixed `next.config.ts` fallback: `localhost:8100` → `backend:8000`
- Patched compiled Next.js manifest files in the running container
- Login now works through frontend proxy at `investiq.com.br`

## Tests
- 33 tests in `test_phase15_history.py` — all passing
- TestCompletenessFlag: 12 tests
- TestAnalysisDiff: 8 tests
- TestGetAnalysisHistory: 7 tests (sync, SQLite)
- TestHistoryEndpoint: 3 tests (HTTP integration)

## E2E verified on VPS
- GET /analysis/history/PETR4 → 200, returned 2 results (completed + stale), newest first
- Login at investiq.com.br → working after proxy fix
