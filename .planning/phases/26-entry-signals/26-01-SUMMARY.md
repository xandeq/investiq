---
phase: 26-entry-signals
plan: 01
subsystem: advisor
tags: [entry-signals, swing-trade, celery, redis, react-query]
dependency_graph:
  requires: [23-01, 25-01]
  provides: [GET /advisor/signals/portfolio, GET /advisor/signals/universe, Celery beat task refresh_universe_entry_signals_batch]
  affects: [advisor router, advisor service, advisor tasks, AdvisorContent.tsx]
tech_stack:
  added: [redis.asyncio, useEntrySignals hook]
  patterns: [SwingSignalItem→EntrySignal mapping, ScreenerSnapshot→EntrySignal batch, fakeredis mock in tests]
key_files:
  created:
    - backend/tests/test_advisor_entry_signals.py
    - frontend/src/features/advisor/hooks/useEntrySignals.ts
  modified:
    - backend/app/modules/advisor/schemas.py
    - backend/app/modules/advisor/service.py
    - backend/app/modules/advisor/router.py
    - backend/app/modules/advisor/tasks.py
    - backend/app/celery_app.py
    - frontend/src/features/advisor/api.ts
    - frontend/src/features/advisor/types.ts
    - frontend/src/features/ai/components/AdvisorContent.tsx
decisions:
  - "Used compute_signals() from swing_trade (not the non-existent calculate_rsi_ma) — correctly reuses existing market-data-cached signal pipeline"
  - "Used redis.asyncio for portfolio signals (async context); sync Redis for universe cache read"
  - "Universe Celery batch reads ScreenerSnapshot (NO LLM) — deterministic, cost-free nightly refresh"
  - "Fixed portfolio_id NOT NULL constraint in test fixtures — required field on Transaction model"
  - "Pre-existing test_dashboard_api failure unrelated to Phase 26 changes — deferred to owner"
metrics:
  duration_seconds: 639
  completed_date: "2026-04-18"
  tasks_completed: 3
  files_modified: 8
---

# Phase 26 Plan 01: Entry Signals — Backend Endpoints + Frontend Section Summary

On-demand portfolio signals (cached 5min) via swing_trade compute_signals() mapping + daily universe batch from ScreenerSnapshot top-100, with dual-table frontend section (Atualizado agora / Diário badges).

## What Was Built

### Backend

**EntrySignal schema** (`backend/app/modules/advisor/schemas.py`):
- `ticker`, `suggested_amount_brl` (str), `target_upside_pct` (float), `timeframe_days` (int), `stop_loss_pct` (float), `rsi` (float|None), `ma_signal` (str|None), `generated_at` (datetime)

**Service functions** (`backend/app/modules/advisor/service.py`):
- `get_portfolio_entry_signals()`: fetches user tickers → calls `compute_signals()` (async Redis) → maps `SwingSignalItem` → `EntrySignal` → caches 5min in Redis
- `get_universe_entry_signals()`: reads `entry_signals:universe` Redis key, returns [] if cache empty

**Endpoints** (`backend/app/modules/advisor/router.py`):
- `GET /advisor/signals/portfolio` — rate 10/min, calls portfolio service
- `GET /advisor/signals/universe` — rate 30/min, calls universe cache read

**Celery task** (`backend/app/modules/advisor/tasks.py`):
- `refresh_universe_entry_signals_batch` — reads ScreenerSnapshot top-100, filters buy candidates (variacao_12m < -10% OR dy > 6%), maps to EntrySignal, stores in Redis 24h TTL

**Beat schedule** (`backend/app/celery_app.py`):
- `refresh-universe-entry-signals-daily`: daily at 02h BRT

### Frontend

**Types** (`frontend/src/features/advisor/types.ts`):
- `EntrySignal` interface added

**API functions** (`frontend/src/features/advisor/api.ts`):
- `getPortfolioEntrySignals()` and `getUniverseEntrySignals()` using `apiClient`

**Hooks** (`frontend/src/features/advisor/hooks/useEntrySignals.ts`):
- `usePortfolioEntrySignals(enabled?)` — 4min stale/refetch, enabled when portfolio exists
- `useUniverseEntrySignals(enabled?)` — 1h stale

**Component** (`frontend/src/features/ai/components/AdvisorContent.tsx`):
- `EntrySignalsSection` with two sub-tables: portfolio (green "Atualizado agora" badge) + universe (blue "Diário" badge)
- `SignalTable` renders: Ticker (→/stock/[ticker]), Valor Sugerido, Alvo %, Stop %, Sinal badge
- Integrated in `AdvisorMain` after Smart Screener section

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Used correct compute_signals() instead of non-existent calculate_rsi_ma()**
- **Found during:** Task 2 implementation
- **Issue:** Plan referenced `calculate_rsi_ma()` and `generate_recommendation()` which don't exist with those signatures; actual function is `compute_signals()` from `swing_trade/service.py`
- **Fix:** Implemented using `compute_signals(redis_client, tickers)` → `SwingSignalsResponse.portfolio_signals` → `EntrySignal` mapping
- **Files modified:** `backend/app/modules/advisor/service.py`
- **Commit:** cfd9e56

**2. [Rule 1 - Bug] Fixed Transaction portfolio_id NOT NULL constraint in test fixtures**
- **Found during:** Task 1/2 testing
- **Issue:** `Transaction` model requires `portfolio_id` (NOT NULL); test fixtures missing this field
- **Fix:** Added `portfolio_id=user_id` to both Transaction objects in `test_portfolio_signals_with_positions`
- **Files modified:** `backend/tests/test_advisor_entry_signals.py`
- **Commit:** cfd9e56

**3. [Rule 2 - Missing functionality] Universe Celery task uses ScreenerSnapshot (NO LLM)**
- **Found during:** Task 2 implementation
- **Issue:** Plan suggested calling `generate_recommendation()` (LLM) — expensive and not batch-safe
- **Fix:** Batch task reads ScreenerSnapshot top-100 by market_cap, applies simple filter (variacao_12m < -10% OR dy > 6%), maps deterministically to EntrySignal — no AI calls
- **Files modified:** `backend/app/modules/advisor/tasks.py`
- **Commit:** cfd9e56

### Pre-existing Issues (Deferred)

- `test_dashboard_api.py::test_dashboard_summary_returns_allocation` was already failing before Phase 26 changes — out of scope, logged here for owner awareness.

## Known Stubs

- `suggested_amount_brl`: hardcoded "1000.00" default for all signals (portfolio and universe). No position-size context is available without a separate cost-basis calculation. Future plan should compute from portfolio allocation (e.g., 10% of total_cost). Flag: non-critical for MVP — the signal is valid, only the suggested amount is placeholder.
- `rsi`: always `None` in portfolio signals — `compute_signals()` doesn't compute RSI (it uses 30d high discount). Future plan would add a separate technical analysis step.

## Self-Check: PASSED

- All 10 key files: FOUND
- All 3 task commits: FOUND (e57ae7c, cfd9e56, cbdabba)
- 5 backend tests: PASSED
- TypeScript: compiles without errors
