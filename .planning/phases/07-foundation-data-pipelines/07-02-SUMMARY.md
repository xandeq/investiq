---
phase: 07-foundation-data-pipelines
plan: 02
type: summary
status: complete
duration: 1 session
subsystem: market_universe/tasks + celery_app
tags: [celery, beat, redis, brapi, cvm, anbima, tesouro, fii, screener]
dependency_graph:
  requires: [07-01 (models, TaxEngine, get_global_db)]
  provides: [screener_snapshots populated daily, fii_metadata populated weekly, tesouro:rates:* in Redis every 6h]
  affects: [Phase 8 screener endpoints read from these snapshots]
tech_stack:
  added: [requests, redis-py sync client, boto3 (ANBIMA SM), csv/zipfile stdlib]
  patterns: [pg_insert on_conflict_do_update, batch flush every 50 rows, exponential backoff retry, ANBIMA OAuth2 primary + CKAN CSV fallback]
key_files:
  created:
    - backend/app/modules/market_universe/tasks.py
    - backend/tests/test_market_universe_tasks.py
  modified:
    - backend/app/celery_app.py
decisions:
  - Partial failure tolerance: screener refresh skips failed tickers, never rolls back entire run
  - Batch commits every 50 tickers (not per-ticker, not entire run) to balance throughput and rollback surface
  - Redis namespace isolation — screener:universe:*, tesouro:rates:*, fii:metadata:* — never market:* (Phase 2 collision)
  - ANBIMA OAuth2 primary + CKAN CSV fallback for Tesouro rates
  - CVM ZIP parsed for "complemento" CSV (segmento + vacancy data), latin-1 encoding
metrics:
  duration: 1 session
  completed: 2026-03-22
  tasks: 2
  files: 3
---

# Phase 7 Plan 02: Three Celery Beat Pipelines — Summary

Three Celery beat tasks registered in `celery_app.py` for automatic data population of global tables and Redis namespaces used by Phase 8 screener endpoints.

## What Was Built

| Task | Schedule | Target |
|------|----------|--------|
| `refresh_screener_universe` | Daily Mon-Fri 7h BRT | `screener_snapshots` table + `screener:universe:*` Redis |
| `refresh_fii_metadata` | Weekly Mon 6h BRT | `fii_metadata` table + `fii:metadata:*` Redis |
| `refresh_tesouro_rates` | Every 6 hours | `tesouro:rates:*` Redis (no DB write) |

## Key Design Decisions

- **Partial failure tolerance**: screener refresh skips failed tickers (exponential backoff up to 3 retries per ticker: 60s, 120s on 429, 5s on other errors), never rolls back the entire run
- **Batch commits**: screener commits every 50 tickers (not per ticker, not entire run) — single bad ticker excluded before batch commit, previous snapshot retained
- **Redis namespace isolation**: `screener:universe:*`, `tesouro:rates:*`, `fii:metadata:*` — never `market:*` (Phase 2 collision)
- **ANBIMA primary + CKAN fallback**: Tesouro rates prefer ANBIMA OAuth2 API (credentials from `tools/anbima` AWS SM), fall back to CKAN CSV (today's rows only) on any failure. ANBIMA credentials not yet registered — fallback path exercised until registered
- **CVM ZIP parsing**: FII metadata downloads `inf_mensal_fii_{year}.zip`, finds the "complemento" CSV, parses with latin-1 encoding and semicolon delimiter; handles CVM field name variants across years

## Files Modified

- `backend/app/modules/market_universe/tasks.py` — created (all 3 tasks + helpers)
- `backend/app/celery_app.py` — added `app.modules.market_universe.tasks` to includes list + 3 beat_schedule entries
- `backend/tests/test_market_universe_tasks.py` — created (7 unit tests, all mocked — fakeredis + requests-mock)

## Verification

- All 3 task functions present in tasks.py (refresh_screener_universe, refresh_fii_metadata, refresh_tesouro_rates)
- All 3 registered in celery_app.py includes + beat_schedule (refresh-screener-universe-daily, refresh-fii-metadata-weekly, refresh-tesouro-rates-6h)
- Redis prefix constants defined: `screener:universe:`, `tesouro:rates:`, `fii:metadata:`
- `get_sync_db_session(tenant_id=None)` used throughout (no tenant injection)
- `pg_insert` with `on_conflict_do_update` for all DB upserts

## Deviations from Plan

None — plan executed exactly as written.

## Self-Check: PASSED
