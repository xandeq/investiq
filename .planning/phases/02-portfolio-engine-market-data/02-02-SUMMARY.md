---
phase: 02-portfolio-engine-market-data
plan: "02-02"
subsystem: market-data
tags: [brapi, bcb, redis, celery, market-data, cache-aside]
dependency_graph:
  requires: [02-01]
  provides: [market-data-adapters, market-data-service, market-data-tasks, market-data-router]
  affects: [portfolio-engine, frontend-market-data-display]
tech_stack:
  added: [python-bcb==0.3.4, requests (already present)]
  patterns: [cache-aside, celery-tasks, async-redis-reads, sync-redis-writes, aws-secrets-manager]
key_files:
  created:
    - backend/app/modules/market_data/__init__.py
    - backend/app/modules/market_data/schemas.py
    - backend/app/modules/market_data/adapters/__init__.py
    - backend/app/modules/market_data/adapters/brapi.py
    - backend/app/modules/market_data/adapters/bcb.py
    - backend/app/modules/market_data/adapters/yfinance_adapter.py
    - backend/app/modules/market_data/service.py
    - backend/app/modules/market_data/tasks.py
    - backend/app/modules/market_data/router.py
    - backend/tests/test_market_data_adapters.py
  modified:
    - backend/tests/test_market_data_tasks.py
decisions:
  - "python-bcb API uses bcb.sgs.get() dict pattern, not SGS() class — import style differs from RESEARCH.md docs"
  - "PTAX USD fetched via bcb.PTAX CotacaoDolarDia endpoint (tries last 5 days to handle weekends/holidays)"
  - "BrapiClient token resolution: constructor arg → BRAPI_TOKEN env → AWS SM tools/brapi → empty (free tier dev mode)"
  - "Module import check requires asyncpg mock outside Docker — pre-existing constraint, not a new issue"
metrics:
  duration_minutes: 18
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 10
  files_modified: 1
  tests_added: 19
  tests_passing: 71
---

# Phase 02 Plan 02: Market Data Service Summary

**One-liner:** brapi.dev + python-bcb adapters with Redis cache-aside, Celery refresh tasks, and FastAPI read endpoints — all market data served from Redis, never from external APIs on user request.

## What Was Built

Complete `app/modules/market_data/` module:

### Adapters (external data sources)
- **`adapters/brapi.py`** — `BrapiClient` with `fetch_quotes`, `fetch_fundamentals`, `fetch_historical`, `fetch_ibovespa`. Token fetched from AWS Secrets Manager (`tools/brapi`, key `BRAPI_TOKEN`) at startup — never hardcoded. 200ms inter-request sleep, retry on 429/5xx.
- **`adapters/bcb.py`** — `fetch_macro_indicators()` using `bcb.sgs.get()` for CDI (series 12), SELIC (series 11), IPCA (series 433) + `bcb.PTAX` for BRL/USD rate. Returns `Decimal(str(float))` for precision safety.
- **`adapters/yfinance_adapter.py`** — `fetch_historical_fallback()` using yfinance with automatic `.SA` suffix for B3 tickers.

### Cache Schemas
- **`schemas.py`** — `QuoteCache`, `MacroCache`, `FundamentalsCache`, `HistoricalCache`, `HistoricalPoint` Pydantic models. All `Decimal` fields, all with `data_stale: bool = False` flag.

### Service (Redis read layer)
- **`service.py`** — `MarketDataService` with async Redis reads. Cache-aside: returns `data_stale=True` with zero/empty values on cache miss. Never raises 500 — always returns a valid schema.

### Tasks (Celery write layer)
- **`tasks.py`** — `refresh_quotes` (writes `market:quote:{TICKER}`, ex=1200) and `refresh_macro` (writes `market:macro:{indicator}`, ex=25200). Both use `BrapiClient`/`fetch_macro_indicators` + sync `redis.Redis.from_url`.

### Router (FastAPI endpoints)
- **`router.py`** — `GET /market-data/macro`, `GET /market-data/fundamentals/{ticker}`, `GET /market-data/historical/{ticker}`. All require JWT auth via `get_authed_db`.

## Tests

19 tests added across 2 test files. 71 total tests passing, 7 skipped (PostgreSQL RLS tests).

| Test | Coverage |
|------|----------|
| `test_brapi_client_fetch_quotes_returns_list` | BrapiClient mock HTTP fetch |
| `test_brapi_client_fetch_fundamentals_returns_dict` | Fundamentals extraction |
| `test_brapi_client_fetch_historical_returns_ohlcv` | Historical OHLCV format |
| `test_brapi_client_fetch_ibovespa` | IBOV quote |
| `test_fetch_macro_indicators_returns_required_keys` | BCB macro mock |
| `test_quote/macro/fundamentals/historical_cache_schema` | Pydantic validation |
| `test_refresh_quotes_writes_redis` | Task → fakeredis key + TTL=1200 |
| `test_brapi_client_writes_redis` | VALE3 key written |
| `test_refresh_macro_writes_redis` | Macro keys + TTL=25200 |
| `test_macro_from_redis` | Service reads assembled macro |
| `test_macro_from_redis_stale_when_empty` | data_stale=True on miss |
| `test_fundamentals_from_redis` | Service reads fundamentals |
| `test_fundamentals_stale_when_cache_empty` | Stale on miss |
| `test_historical_from_redis` | Service reads OHLCV |
| `test_quote_stale_when_cache_empty` | Quote stale on miss |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] python-bcb import pattern differs from plan spec**
- **Found during:** Task 1
- **Issue:** Plan specified `from python_bcb import SGS` but the actual package imports as `import bcb.sgs as sgs` with `sgs.get({...})` dict API
- **Fix:** Used `bcb.sgs.get()` and `bcb.PTAX` per actual package API (version 0.3.4)
- **Files modified:** `backend/app/modules/market_data/adapters/bcb.py`

**2. [Rule 2 - Missing] python-bcb not in requirements**
- **Found during:** Task 1 setup
- **Issue:** `python-bcb` not installed — ModuleNotFoundError
- **Fix:** `pip install python-bcb` — installed version 0.3.4
- **Note:** Should be added to `requirements.txt` / Docker image for production

## Redis Key Convention (Implemented)

| Key Pattern | TTL | Written By | Read By |
|-------------|-----|-----------|---------|
| `market:quote:{TICKER}` | 1200s (20min) | `refresh_quotes` | `service.get_quote()` |
| `market:macro:{indicator}` | 25200s (7h) | `refresh_macro` | `service.get_macro()` |
| `market:fundamentals:{TICKER}` | 86400s (24h) | Future task | `service.get_fundamentals()` |
| `market:historical:{TICKER}` | 86400s (24h) | Future task | `service.get_historical()` |

## Commits

| Hash | Message |
|------|---------|
| `98526b1` | feat(02-02): brapi.dev adapter, bcb macro adapter, cache schemas |
| `238eb65` | feat(02-02): Redis service layer, Celery tasks, market data router |

## Self-Check: PASSED

All created files confirmed on disk. Both task commits verified in git log.

- FOUND: backend/app/modules/market_data/__init__.py
- FOUND: backend/app/modules/market_data/schemas.py
- FOUND: backend/app/modules/market_data/adapters/brapi.py
- FOUND: backend/app/modules/market_data/adapters/bcb.py
- FOUND: backend/app/modules/market_data/service.py
- FOUND: backend/app/modules/market_data/tasks.py
- FOUND: backend/app/modules/market_data/router.py
- FOUND: backend/tests/test_market_data_tasks.py
- FOUND commit: 98526b1 (Task 1)
- FOUND commit: 238eb65 (Task 2)
- 71 tests passing, 7 skipped (PostgreSQL-only)
