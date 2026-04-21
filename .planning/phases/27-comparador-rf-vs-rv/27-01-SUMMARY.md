---
phase: 27-comparador-rf-vs-rv
plan: "01"
subsystem: screener_v2 / macro-rates API
tags: [backend, frontend, macro-rates, selic, renda-fixa, comparador]
dependency_graph:
  requires: []
  provides:
    - MacroRatesResponse.selic field (backend + frontend)
    - GET /renda-fixa/macro-rates returns { cdi, ipca, selic }
  affects:
    - Phase 27 Plans 02-03 (comparador endpoint + frontend page)
    - useMacroRates() hook consumers
tech_stack:
  added: []
  patterns:
    - Pydantic schema extension (add field, keep existing)
    - Redis key read pattern (market:macro:selic already populated by refresh_macro beat)
    - TypeScript structural typing (additive interface extension)
key_files:
  created: []
  modified:
    - backend/app/modules/screener_v2/schemas.py
    - backend/app/modules/screener_v2/service.py
    - backend/tests/test_renda_fixa_macro_rates.py
    - frontend/src/features/screener_v2/types.ts
decisions:
  - "Redis key market:macro:selic already populated by refresh_macro Celery beat — only API layer needed updating"
  - "No router changes required — FastAPI picks up new Pydantic field automatically"
  - "TypeScript structural typing: existing RendaFixaContent consumer reads only cdi/ipca, new selic field does not break it"
metrics:
  duration: "141s"
  completed: "2026-04-18T23:14:06Z"
  tasks_completed: 2
  files_modified: 4
---

# Phase 27 Plan 01: Extend macro-rates to Include SELIC Summary

Extend `GET /renda-fixa/macro-rates` to return `{ cdi, ipca, selic }` by adding `selic: Decimal | None` to the Pydantic schema, reading `market:macro:selic` from Redis in the service, and mirroring the shape in the frontend TypeScript type.

## Tasks Completed

| Task | Name | Commit | Files |
|------|------|--------|-------|
| 1 | Add selic field to MacroRatesResponse + read Redis in service | e082d69 | schemas.py, service.py, tests/test_renda_fixa_macro_rates.py |
| 2 | Add selic to frontend MacroRatesResponse TypeScript type | 1ac0f10 | frontend/src/features/screener_v2/types.ts |

## What Was Built

### Backend Changes

**`backend/app/modules/screener_v2/schemas.py` (line 217):**
```python
selic: Decimal | None = Field(None, description="SELIC annual rate as percentage, e.g. 14.75")
```

**`backend/app/modules/screener_v2/service.py` (lines 454, 458, 462):**
- Read `selic_raw = r.get("market:macro:selic")` inside the try block
- Pass `selic=_safe_decimal(selic_raw)` to `MacroRatesResponse`
- Fallback branch now explicitly returns `MacroRatesResponse(cdi=None, ipca=None, selic=None)`

### Frontend Changes

**`frontend/src/features/screener_v2/types.ts` (line 113):**
```typescript
selic: string | null;  // Annual SELIC rate as percentage string, e.g. "14.75"
```

## Redis Key Contract Confirmed

`market:macro:selic` is written by `refresh_macro` Celery beat task (every 7h) in `backend/app/modules/market_data/tasks.py`. The key was already populated in production before this plan — only the API layer was missing the field.

## Test Coverage

| Test | Before | After |
|------|--------|-------|
| test_macro_rates_requires_auth | unchanged | unchanged |
| test_macro_rates_endpoint | asserted cdi, ipca | extended: asserts cdi, ipca, selic |
| test_macro_rates_redis_fallback | asserted cdi=None, ipca=None | extended: asserts selic=None too |
| test_macro_rates_selic_included_in_response | did not exist | NEW: asserts set(data.keys()) >= {"cdi","ipca","selic"} |

Total: 2 tests extended, 1 new test added. All 4 pass.

## Deviations from Plan

None — plan executed exactly as written.

## Known Stubs

None — selic field is fully wired end-to-end (Redis key populated by existing Celery beat, API reads and returns it, frontend type reflects the shape).
