---
phase: 15-data-quality-advanced-features
plan: 01
subsystem: analysis, celery, cache
tags: [redis, celery-beat, invalidation, earnings, stale-analysis]

requires:
  - phase: 14-differentiators-sophistication
    provides: DCF, earnings, dividend, sector analysis jobs

provides:
  - sync cache invalidation for earnings releases
  - nightly celery beat task for filing-date polling
  - archival of superseded completed analyses on refresh
  - pytest coverage for phase 15 cache invalidation flow

key-files:
  created:
    - backend/tests/test_phase15_cache.py
  modified:
    - backend/app/modules/analysis/invalidation.py
    - backend/app/modules/analysis/tasks.py
    - backend/app/celery_app.py

key-decisions:
  - "on_earnings_release() is sync because Celery Beat and sync DB/Redis are the execution context"
  - "Redis invalidation must delete brapi:fundamentals:{TICKER}, matching data.py cache writes"
  - "Older completed jobs are marked stale after a fresh successful completion, but archival failure must not fail the new job"
  - "Nightly filing polling is capped at 50 recent tickers to limit BRAPI usage"

requirements-completed: [AI-13]

completed: 2026-04-03
---

# Phase 15 Plan 01 Summary

**Cache invalidation on earnings release is now wired end-to-end: sync invalidation helper, nightly Beat poller, stale-on-refresh archival, and targeted pytest coverage.**

## Accomplishments

- Fixed the invalidation bug in `invalidation.py`: the code now deletes `brapi:fundamentals:{TICKER}` instead of the wrong `analysis:cache:{ticker}` key.
- Converted `on_earnings_release()` from `async def` to `def`, matching the synchronous Celery/Redis/SQLAlchemy context already used by the module.
- Added `get_last_analysis_data_timestamp()` so the nightly poll can compare stored analysis freshness against the most recent filing date.
- Added `archive_previous_completed_jobs()` and hooked it into all 4 successful analysis completions (`dcf`, `earnings`, `dividend`, `sector`) so older completed rows become `stale`.
- Added `_fetch_latest_quarterly_filing_date()` plus the `analysis.check_earnings_releases` Celery task.
- Registered the Beat schedule entry `check-earnings-releases-nightly` at 22:00 Mon-Fri in `celery_app.py`.
- Added `backend/tests/test_phase15_cache.py` covering cache-key deletion, stale marking, latest timestamp lookup, nightly poll behavior, archival scoping, and quota deduction on refresh.

## Verification

- `cd D:/claude-code/investiq/backend && python -m pytest tests/test_phase15_cache.py -q`
  - Result: `11 passed`
- `cd D:/claude-code/investiq/backend && python -m pytest tests/test_phase13_dcf.py tests/test_phase13_earnings_dividend.py tests/test_phase14_quality.py tests/test_phase14_sector.py tests/test_phase15_cache.py -q`
  - Result: `115 passed`
- Attempted broader regression including `tests/test_phase12_foundation.py`, but the run exceeded the available timeout window twice, so that full result is still unverified in this session.

## Files

- `backend/app/modules/analysis/invalidation.py`
- `backend/app/modules/analysis/tasks.py`
- `backend/app/celery_app.py`
- `backend/tests/test_phase15_cache.py`

## Next Phase Readiness

- Phase 15 Plan 01 is complete.
- The next planned step is `15-02`: completeness flags plus analysis history endpoint.
- If a future session resumes from docs alone, resume at `.planning/phases/15-data-quality-advanced-features/15-02-PLAN.md`.

## Post-Deploy Stabilization (Codex, 2026-04-03)

### What Was Done

- Deployed the Phase 15 Plan 01 analysis changes to production using the existing VPS workflow (`docker cp` + container restart, no image rebuild).
- Confirmed production smoke + auth + analysis flow:
  - `https://investiq.com.br` → `200`
  - `https://api.investiq.com.br/health` → `200`
  - login with the real production account worked
  - `POST /analysis/dcf` completed successfully in production
  - older completed analysis for the same tenant+ticker became `stale` after a refresh
- Located the Claude session context used outside the repo:
  - `.planning/*` remains the main source of project memory
  - Claude JSONL session log exists under `C:\Users\acq20\.claude\projects\d--claude-code-investiq\...jsonl`
- Fixed local regression and prod bug around market data:
  - `backend/app/modules/market_data/tasks.py` now writes `market:quote:IBOV` in the same normalized schema used by `MarketDataService`
  - `backend/app/modules/market_data/service.py` now tolerates the legacy `regularMarket*` quote payload, so `/portfolio/benchmarks` no longer 500s if Redis still contains the old IBOV shape
- Deployed the market-data hotfix (`service.py` + `tasks.py`) to production backend/worker and verified:
  - `GET https://api.investiq.com.br/portfolio/benchmarks` → `200`
  - manual `refresh_quotes()` on the worker completed
  - Redis `market:quote:IBOV` now contains normalized keys: `symbol`, `price`, `change`, `change_pct`, `fetched_at`, `data_stale`
- Stabilized local Playwright specs:
  - auth/dashboard specs now use stable selectors and visible text rather than brittle raw-body checks
  - screener spec now matches the current CTA copy (`Iniciar triagem agora`) and current visible content
  - wizard spec now uses `/wizard` only; `/onde-investir` is not the active route anymore

### Validation Completed

- Backend:
  - `python -m pytest tests/test_market_data_adapters.py tests/test_market_data_tasks.py tests/test_market_universe_tasks.py tests/test_portfolio_api.py -q`
  - Result: `39 passed`
- Playwright targeted:
  - `npx playwright test e2e/auth.spec.ts e2e/dashboard.spec.ts --reporter=line`
  - Result: `12 passed`
  - `npx playwright test e2e/portfolio.spec.ts --reporter=line`
  - Result: `8 passed` after the production benchmarks hotfix
  - `npx playwright test e2e/portfolio.spec.ts e2e/screener.spec.ts e2e/wizard.spec.ts --reporter=line`
  - Result before deploy: `21 passed`, `1 failed` (`portfolio/benchmarks` 500)
  - Result after deploy: reran `portfolio.spec.ts` and it passed fully

### Pending / Important For Claude

- `backend/app/modules/market_data/adapters/brapi.py` was fixed locally to fall back when BRAPI returns `MODULES_NOT_AVAILABLE`, but that adapter fix was **not redeployed yet** before this handoff.
- Evidence: after the last worker-side manual `refresh_quotes()` in production, fundamentals still logged 400s for some tickers such as `BBDC4`, `WEGE3`, `ABEV3`, and `BOVA11`. That means production is still using the old adapter behavior there.
- The local adapter/test changes that still need deployment are:
  - `backend/app/modules/market_data/adapters/brapi.py`
  - `backend/tests/test_market_data_adapters.py`
  - `backend/tests/test_market_universe_tasks.py`
- A final full Playwright run across all 73 selected E2E tests was started after the fixes, but the user intentionally interrupted the session before it finished. The last fully completed wide run before that interruption was:
  - `70 passed`, `3 failed` initially
  - then all three causes were addressed (`portfolio`, `screener`, `wizard`)
  - `portfolio.spec.ts` was rerun and passed after deploy
  - `screener.spec.ts` and `wizard.spec.ts` had already passed in the previous 22-test subset after local spec fixes

### Exact Stop Point

- Functional phase position: **Phase 15 / Plan 01 complete**
- Next roadmap step: **Phase 15 / Plan 02 not started**
- Operational stop point for the next session:
  1. deploy `backend/app/modules/market_data/adapters/brapi.py` to backend + worker
  2. rerun a production-side worker refresh to confirm the BRAPI fallback suppresses the repeated `MODULES_NOT_AVAILABLE` 400 noise
  3. rerun the broad Playwright suite once end-to-end to close the validation loop
  4. then start `15-02-PLAN.md`
