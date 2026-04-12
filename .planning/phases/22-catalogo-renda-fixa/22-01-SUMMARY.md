---
phase: 22-catalogo-renda-fixa
plan: "01"
subsystem: backend/renda-fixa
tags: [renda-fixa, macro-rates, redis, api, tdd]
dependency_graph:
  requires: []
  provides: [GET /renda-fixa/macro-rates, MacroRatesResponse, query_macro_rates]
  affects: [plan-22-02]
tech_stack:
  added: []
  patterns: [redis-sync-read, graceful-fallback, rate-limited-endpoint]
key_files:
  created:
    - backend/tests/test_renda_fixa_macro_rates.py
  modified:
    - backend/app/modules/screener_v2/schemas.py
    - backend/app/modules/screener_v2/service.py
    - backend/app/modules/screener_v2/router.py
decisions:
  - Used MacroRatesResponse in top-level schema import block (no circular import risk — schemas.py has no imports from service.py)
  - Followed exact tesouro_rates pattern: sync Redis.from_url with decode_responses=True, except-all fallback
  - No main.py changes needed — /renda-fixa prefix router was already registered
metrics:
  duration: "~4 minutes"
  completed: "2026-04-12"
  tasks_completed: 2
  files_changed: 4
---

# Phase 22 Plan 01: Macro Rates Endpoint Summary

MacroRatesResponse schema + query_macro_rates service + GET /renda-fixa/macro-rates endpoint reading CDI and IPCA from Redis with null fallback when unavailable.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Create test file (RED) | 01e6a91 | backend/tests/test_renda_fixa_macro_rates.py |
| 2 | Implement schema + service + router | bd56dd9 | schemas.py, service.py, router.py |

## Verification

- `GET /renda-fixa/macro-rates` returns 401 for unauthenticated requests
- `GET /renda-fixa/macro-rates` returns 200 with `{cdi: null, ipca: null}` in test env (Redis unavailable)
- 3 new tests pass (test_macro_rates_requires_auth, test_macro_rates_endpoint, test_macro_rates_redis_fallback)
- Full backend suite: 193+ passed, 1 pre-existing failure in test_market_data_adapters.py (unrelated to this plan)
- `git diff HEAD backend/app/main.py` shows no diff — no main.py changes needed

## Key Decisions

- **MacroRatesResponse top-level import:** Added directly to the existing `from app.modules.screener_v2.schemas import (...)` block in service.py — no circular import risk since schemas.py does not import from service.py
- **Redis read pattern:** Copied sync `redis.Redis.from_url` approach from `query_tesouro_rates` — consistent with existing pattern; except-all catches connection refused and returns null fallback
- **No main.py changes:** `/renda-fixa` prefix was already registered on the screener_v2 router via main.py line 126 — the new `/macro-rates` route is picked up automatically

## Deviations from Plan

None - plan executed exactly as written.

## Known Stubs

None. The endpoint returns real Redis data (or null fallback) — no hardcoded values flow to consumers.

## Self-Check: PASSED

- [x] `backend/tests/test_renda_fixa_macro_rates.py` — exists (created)
- [x] `backend/app/modules/screener_v2/schemas.py` — contains `class MacroRatesResponse`
- [x] `backend/app/modules/screener_v2/service.py` — contains `async def query_macro_rates`
- [x] `backend/app/modules/screener_v2/router.py` — contains `/macro-rates` route
- [x] Commits 01e6a91 and bd56dd9 — verified in git log
