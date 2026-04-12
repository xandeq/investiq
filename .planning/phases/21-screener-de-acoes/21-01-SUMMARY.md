---
phase: 21-screener-de-acoes
plan: "01"
subsystem: backend/data-pipeline
tags: [screener, brapi, celery, migration, postgresql]
dependency_graph:
  requires: []
  provides: [variacao_12m_pct-column, brapi-52week-extraction, celery-upsert-variacao]
  affects: [screener_snapshots-table, refresh_screener_universe-task]
tech_stack:
  added: []
  patterns: [alembic-add-column, sqlalchemy-mapped-column, celery-pg-insert-upsert]
key_files:
  created:
    - backend/alembic/versions/0024_add_variacao_12m_pct.py
  modified:
    - backend/app/modules/market_universe/models.py
    - backend/app/modules/market_data/adapters/brapi.py
    - backend/app/modules/market_universe/tasks.py
decisions:
  - "Used Numeric(10,6) for variacao_12m_pct to match existing precision pattern (dy column)"
  - "No dialect gate needed in migration — op.add_column works on both SQLite and PostgreSQL"
metrics:
  duration: "62s"
  completed_date: "2026-04-12"
  tasks_completed: 2
  files_modified: 4
requirements:
  - SCRA-01
---

# Phase 21 Plan 01: Add variacao_12m_pct to Screener Data Pipeline Summary

Added 52-week price change % (variacao_12m_pct) to the screener data pipeline via Alembic migration, ScreenerSnapshot model field, brapi adapter 52WeekChange extraction, and Celery upsert conflict clause.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Migration 0024 + ScreenerSnapshot model update | f723dda | backend/alembic/versions/0024_add_variacao_12m_pct.py, backend/app/modules/market_universe/models.py |
| 2 | BrapiClient 52WeekChange extraction + Celery task upsert | 775a19a | backend/app/modules/market_data/adapters/brapi.py, backend/app/modules/market_universe/tasks.py |

## What Was Built

### Migration 0024
- `backend/alembic/versions/0024_add_variacao_12m_pct.py`
- `revision = "0024_add_variacao_12m_pct"`, `down_revision = "0023_add_swing_trade_operations"`
- `upgrade()`: `op.add_column("screener_snapshots", sa.Column("variacao_12m_pct", sa.Numeric(10, 6), nullable=True))`
- `downgrade()`: `op.drop_column("screener_snapshots", "variacao_12m_pct")`

### ScreenerSnapshot Model
- Added `variacao_12m_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)` after `ev_ebitda`

### BrapiClient
- Added `"variacao_12m": _extract(key_stats, "52WeekChange")` to `_parse_response()` return dict
- Updated `fetch_fundamentals` docstring to include `variacao_12m` in return keys

### Celery Task (refresh_screener_universe)
- Row dict: `"variacao_12m_pct": _safe_decimal(fund.get("variacao_12m")) if fund else None`
- `_flush_batch` set_ clause: `"variacao_12m_pct": stmt.excluded.variacao_12m_pct`

## Verification

- `ScreenerSnapshot.variacao_12m_pct` — column descriptor prints (not error)
- `grep -n "variacao_12m" brapi.py` — shows extraction line at line 167
- `grep -n "variacao_12m_pct" tasks.py` — shows row dict (line 291) and set_() (line 242)
- `python -m pytest tests/test_market_universe_tasks.py -x -q` — **7 passed, 0 failed**

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None. The migration, model, adapter extraction, and upsert are all fully wired. The data will populate on the next `refresh_screener_universe` Celery beat run.

## Self-Check: PASSED

- [x] `backend/alembic/versions/0024_add_variacao_12m_pct.py` — EXISTS
- [x] `backend/app/modules/market_universe/models.py` contains `variacao_12m_pct` — CONFIRMED
- [x] `backend/app/modules/market_data/adapters/brapi.py` contains `variacao_12m` — CONFIRMED
- [x] `backend/app/modules/market_universe/tasks.py` contains `variacao_12m_pct` in both row and set_() — CONFIRMED
- [x] Commit f723dda — EXISTS
- [x] Commit 775a19a — EXISTS
- [x] All 7 test_market_universe_tasks tests pass — CONFIRMED
