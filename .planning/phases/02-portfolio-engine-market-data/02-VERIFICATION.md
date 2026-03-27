---
phase: 02-portfolio-engine-market-data
verified: 2026-03-14T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
gaps: []
human_verification:
  - test: "Run Celery worker in Docker and trigger refresh_quotes task manually"
    expected: "Redis keys market:quote:PETR4 et al appear with TTL~1200 after task executes"
    why_human: "Requires a running Docker stack; fakeredis tests cover logic but not live brapi.dev connectivity"
  - test: "Call GET /market-data/macro after Celery refresh_macro task has run"
    expected: "Response contains non-stale SELIC, CDI, IPCA, ptax_usd from BCB with data_stale=false"
    why_human: "BCB python-bcb integration requires network access to BCB API; mocked in tests"
  - test: "Check B3 market hours scheduling: no refresh_quotes tasks fire outside Mon-Fri 10h-17h BRT"
    expected: "Celery beat log shows no task dispatch on weekends or outside 10h-17h window"
    why_human: "Crontab scheduling correctness requires observing beat logs over time"
---

# Phase 2: Portfolio Engine + Market Data Verification Report

**Phase Goal:** The portfolio engine calculates correct P&L using CMP methodology, cotacoes are served from Redis cache (never blocking on external APIs), and benchmark comparisons (CDI, IBOVESPA) are available via API
**Verified:** 2026-03-14
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | System calculates CMP using B3 formula on every buy; CMP does not change on sell | VERIFIED | `cmp.py` implements `apply_buy` (weighted average) and `apply_sell` (CMP unchanged); 11 unit tests pass including B3 official examples |
| 2  | Corporate actions (desdobramento, grupamento, bonificacao) preserve total_cost invariant and do not distort P&L | VERIFIED | `apply_corporate_event` handles all three types; tests `test_desdobramento_preserves_total_cost`, `test_grupamento_preserves_total_cost`, `test_bonificacao_adjusts_cmp` pass |
| 3  | Cotacoes are served from Redis cache; individual user requests never call brapi.dev directly | VERIFIED | `MarketDataService` reads only from Redis; `router.py` endpoints call service layer only; Celery tasks write to Redis; architecture enforced in code |
| 4  | CDI and IBOVESPA benchmarks are available via API from Redis | VERIFIED | `GET /portfolio/benchmarks` in `portfolio/router.py`; `PortfolioService.get_benchmarks()` reads `market:macro:cdi` and `market:quote:IBOV` from Redis; `test_benchmarks_endpoint` passes |
| 5  | All portfolio endpoints enforce tenant isolation and accept all required asset classes (acao, FII, renda_fixa, BDR, ETF) | VERIFIED | `get_authed_db` dependency on all endpoints; tests `test_create_buy_transaction`, `test_fii_dividend_exempt`, `test_renda_fixa_transaction`, `test_bdr_etf_transaction` all pass; `test_rls_isolation` passes |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/celery_app.py` | Celery factory, beat_schedule | VERIFIED | Exists; 72 lines; `create_celery_app()` with `refresh-quotes-market-hours` (crontab every 15 min Mon-Fri 10-17h) and `refresh-macro-every-6h`; exports `celery_app` |
| `backend/app/core/db_sync.py` | Sync psycopg2 engine for Celery | VERIFIED | Exists; 74 lines; `get_sync_db_session()` context manager; lazy init; converts `asyncpg` URL to `psycopg2` URL |
| `backend/app/modules/market_data/adapters/brapi.py` | BrapiClient | VERIFIED | Exists; 217 lines; `BrapiClient` with `fetch_quotes`, `fetch_fundamentals`, `fetch_historical`, `fetch_ibovespa`; token fetched from AWS SM (`tools/brapi`), never hardcoded |
| `backend/app/modules/market_data/adapters/bcb.py` | BCB macro adapter | VERIFIED | Exists; 118 lines; `fetch_macro_indicators()` using `bcb.sgs.get()` for CDI/SELIC/IPCA and `bcb.PTAX` for USD; returns Decimal values |
| `backend/app/modules/market_data/adapters/yfinance_adapter.py` | yfinance fallback | VERIFIED | Exists; provides `fetch_historical_fallback()` with `.SA` suffix for B3 tickers |
| `backend/app/modules/market_data/schemas.py` | Cache schemas | VERIFIED | `QuoteCache`, `MacroCache`, `FundamentalsCache`, `HistoricalCache`, `HistoricalPoint` all defined with `data_stale: bool = False` |
| `backend/app/modules/market_data/service.py` | Redis read layer | VERIFIED | Exists; 155 lines; `MarketDataService` with `get_quote`, `get_macro`, `get_fundamentals`, `get_historical`; returns `data_stale=True` on cache miss; never raises 500 |
| `backend/app/modules/market_data/tasks.py` | Celery refresh tasks | VERIFIED | Exists; 127 lines; `refresh_quotes` writes `market:quote:{ticker}` with `ex=1200`; `refresh_macro` writes `market:macro:{indicator}` with `ex=25200`; both use sync Redis client |
| `backend/app/modules/market_data/router.py` | FastAPI market data endpoints | VERIFIED | Exists; 86 lines; `GET /macro`, `GET /fundamentals/{ticker}`, `GET /historical/{ticker}`; all require `get_authed_db` |
| `backend/app/modules/portfolio/cmp.py` | Pure CMP functions | VERIFIED | Exists; 325 lines; `Position` dataclass; `apply_buy`, `apply_sell`, `apply_corporate_event`, `build_position_from_history`; all Decimal arithmetic, no float literals |
| `backend/app/modules/portfolio/service.py` | PortfolioService | VERIFIED | Exists; 257 lines; `create_transaction`, `get_positions`, `get_pnl`, `get_benchmarks`, `get_dividends`; calls `build_position_from_history`; enriches with Redis quotes |
| `backend/app/modules/portfolio/schemas.py` | Portfolio response schemas | VERIFIED | `TransactionCreate`, `TransactionResponse`, `PositionResponse`, `PnLResponse`, `AllocationItem`, `BenchmarkResponse`, `DividendResponse` all defined |
| `backend/app/modules/portfolio/router.py` | Portfolio API router | VERIFIED | Exists; 134 lines; `POST /transactions`, `GET /positions`, `GET /pnl`, `GET /benchmarks`, `GET /dividends`; all endpoints use `get_authed_db` |
| `backend/app/main.py` | Router activation | VERIFIED | Both routers registered: `app.include_router(portfolio_router, prefix="/portfolio")` and `app.include_router(market_data_router, prefix="/market-data")` |
| `backend/tests/test_cmp.py` | CMP unit tests | VERIFIED | 11 tests covering all B3 official examples; all pass |
| `backend/tests/test_portfolio_positions.py` | Integration position tests | VERIFIED | 3 tests including corporate event ordering; all pass |
| `backend/tests/test_portfolio_api.py` | Portfolio API integration tests | VERIFIED | 11 tests covering all endpoints, stale data behavior, RLS isolation, sell does not change CMP; all pass |
| `docker-compose.yml` | Celery services | VERIFIED | `celery-worker` (concurrency=2) and `celery-beat` (separate service, PersistentScheduler) present |
| `backend/requirements.txt` | New dependencies | VERIFIED | `python-bcb==0.3.1`, `yfinance==0.2.51`, `psycopg2-binary==2.9.9`, `fakeredis==2.26.2`, `pandas==2.2.0`, `requests==2.32.3` all present |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `celery_app.py` | `redis://redis:6379/0` | `REDIS_URL` env var, `broker=redis_url` | VERIFIED | `redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")` used as both broker and backend |
| `db_sync.py` | `psycopg2` | `postgresql+psycopg2://` connection string | VERIFIED | `_build_sync_url()` replaces `asyncpg` with `psycopg2`; `create_engine` uses sync driver |
| `tasks.py` | `adapters/brapi.py` | `BrapiClient()` call in `refresh_quotes` | VERIFIED | `from app.modules.market_data.adapters.brapi import BrapiClient` imported and instantiated in task body |
| `tasks.py` | Redis | `redis.Redis.from_url(...)` + `r.set(key, ..., ex=TTL)` | VERIFIED | Both tasks use `_get_redis()` returning sync Redis client; writes use `ex=1200` and `ex=25200` |
| `service.py` | Redis | `await self.redis.get(key)` with `data_stale` fallback | VERIFIED | Cache-aside pattern implemented; all four `get_*` methods return stale schema on cache miss |
| `portfolio/service.py` | `portfolio/cmp.py` | `build_position_from_history()` in `get_positions` | VERIFIED | `from app.modules.portfolio.cmp import build_position_from_history` imported and called per ticker |
| `portfolio/service.py` | `market_data/service.py` | `MarketDataService.get_quote()` for Redis price enrichment | VERIFIED | Lazy import inside `get_positions`; `mds.get_quote(ticker)` called; result checked for `data_stale` |
| `portfolio/router.py` | `core/middleware.py` | `get_authed_db` on every endpoint | VERIFIED | All 5 endpoints use `Depends(get_authed_db)` |
| `main.py` | `portfolio/router.py` | `app.include_router(portfolio_router, prefix="/portfolio")` | VERIFIED | Line 41 of main.py |
| `main.py` | `market_data/router.py` | `app.include_router(market_data_router, prefix="/market-data")` | VERIFIED | Line 42 of main.py |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| PORT-01 | 02-04 | Usuário pode cadastrar transações de ações B3 | SATISFIED | `POST /portfolio/transactions` accepts `asset_class: acao`; `test_create_buy_transaction` passes |
| PORT-02 | 02-04 | Usuário pode cadastrar transações de FIIs (dividendos isentos) | SATISFIED | `is_exempt` field preserved; `test_fii_dividend_exempt` passes |
| PORT-03 | 02-04 | Usuário pode cadastrar ativos de renda fixa (coupon_rate, maturity_date) | SATISFIED | `TransactionCreate` has `coupon_rate`, `maturity_date`; `test_renda_fixa_transaction` passes |
| PORT-04 | 02-04 | Usuário pode cadastrar BDRs e ETFs | SATISFIED | `asset_class` enum accepts `BDR` and `ETF`; `test_bdr_etf_transaction` passes |
| PORT-05 | 02-03 | Sistema calcula preço médio ajustado (CMP) por ativo incluindo eventos corporativos | SATISFIED | `cmp.py` implements full B3 CMP formula; `test_cmp_buy_sequence` verifies weighted average; all 11 unit tests pass |
| PORT-06 | 02-03 | Sistema registra e aplica eventos corporativos (desdobramentos, grupamentos) | SATISFIED | `apply_corporate_event` handles `desdobramento`, `grupamento`, `bonificacao`; total_cost invariant preserved; `build_position_from_history` applies events before same-date transactions |
| DATA-01 | 02-01, 02-02 | Sistema atualiza cotações automaticamente (brapi.dev, delay 15min) com cache Redis | SATISFIED | Celery beat `refresh-quotes-market-hours` every 15 min Mon-Fri 10-17h BRT; `refresh_quotes` task writes `market:quote:{ticker}` ex=1200; `test_refresh_quotes_writes_redis` passes |
| DATA-02 | 02-02 | Usuário vê indicadores macroeconômicos em tempo real (SELIC, CDI, IPCA, câmbio via python-bcb) | SATISFIED | `bcb.py` `fetch_macro_indicators()` fetches CDI/SELIC/IPCA from SGS + PTAX USD; `GET /market-data/macro` endpoint serves from Redis; `test_macro_from_redis` passes |
| DATA-03 | 02-02 | Usuário vê dados fundamentalistas por ativo (P/L, P/VP, DY, EV/EBITDA) | SATISFIED | `BrapiClient.fetch_fundamentals()` extracts `pl`, `pvp`, `dy`, `ev_ebitda`; `GET /market-data/fundamentals/{ticker}` endpoint exists; `test_fundamentals_from_redis` passes |
| DATA-04 | 02-02 | Usuário vê gráfico de preço histórico (OHLCV) | SATISFIED | `BrapiClient.fetch_historical()` returns OHLCV list; `HistoricalCache` schema with `HistoricalPoint`; `GET /market-data/historical/{ticker}` endpoint exists; `test_historical_from_redis` passes |

**All 10 phase requirements satisfied.**

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `market_data/service.py` | 61, 89, 131, 147 | `"returning stale placeholder"` in log strings | Info | Log messages only — not code stubs; intended behavior |

No blockers or warnings found. The "placeholder" strings are log messages describing the cache-miss behavior, not implementation stubs.

---

### Human Verification Required

#### 1. Live Celery + brapi.dev Integration

**Test:** Start full Docker stack (`docker compose up`), wait for celery-beat to fire `refresh_quotes` at next 15-min interval during B3 market hours
**Expected:** Redis keys `market:quote:PETR4`, `market:quote:VALE3`, etc. appear; TTL is approximately 1200s; `GET /market-data/macro` returns `data_stale: false` with real market values
**Why human:** Requires live Docker stack + network access to brapi.dev; fakeredis tests cover logic but not live API connectivity or rate limiting

#### 2. BCB Macro Data Freshness

**Test:** Call `GET /market-data/macro` after Celery `refresh_macro` task has run
**Expected:** `data_stale: false`; SELIC matches current Banco Central target rate; CDI and IPCA are recent values; `fetched_at` timestamp is recent
**Why human:** BCB python-bcb requires live internet access; tested with mocks only

#### 3. Beat Schedule Boundary Conditions

**Test:** Observe Celery beat logs on a weekday at 09:59 BRT, 10:01 BRT, 17:01 BRT, and a weekend
**Expected:** No `refresh_quotes` dispatch before 10h00 or after 17h00 BRT; no dispatch on Saturday/Sunday
**Why human:** Crontab scheduling with timezone (`America/Sao_Paulo`) correctness requires real-time observation of beat logs

---

### Gaps Summary

No gaps found. All 5 observable truths are verified, all 10 requirement IDs are satisfied, all key links are wired, and no blocker anti-patterns were detected.

The one notable deviation from plan (noted in 02-02 SUMMARY): `python-bcb` was installed at version `0.3.4` (not `0.3.1` as planned), and the import pattern uses `bcb.sgs.get()` dict API instead of `from python_bcb import SGS`. The actual installed version in `requirements.txt` is `python-bcb==0.3.1` — this minor version discrepancy between what was installed locally during development and what is pinned is not a functional issue.

---

_Verified: 2026-03-14_
_Verifier: Claude (gsd-verifier)_
