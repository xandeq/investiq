---
phase: 11-wizard-onde-investir
plan: "01"
subsystem: wizard-backend
tags: [testing, wizard, celery, datetime, validation]
dependency_graph:
  requires: []
  provides: [wizard-test-coverage, wizard-backend-validation]
  affects: [test-suite]
tech_stack:
  added: []
  patterns: [pytest-asyncio, fakeredis, SQLite in-memory tests, Celery mock dispatch]
key_files:
  created:
    - backend/tests/test_wizard.py
  modified:
    - backend/tests/conftest.py
    - backend/app/core/plan_gate.py
    - backend/app/main.py
decisions:
  - "Reverted ai/router.py datetime fix to preserve pre-existing test failure behavior (avoid changing 500->hang regression)"
  - "WizardJob inserted directly in delta test using result_json (JSON string) not result (dict)"
metrics:
  duration: "~15min"
  completed_date: "2026-03-24"
  tasks_completed: 2
  files_changed: 4
---

# Phase 11 Plan 01: Wizard Backend Tests Summary

One-liner: 14 pytest tests covering wizard validation logic (_parse_and_validate ticker/sum checks), prompt building (macro/portfolio context), and API endpoints (202/401/404/disclaimer/delta) all passing with SQLite in-memory DB.

## Tasks Completed

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | Register wizard models in conftest and mock Celery dispatch | 2acd52d | backend/tests/conftest.py |
| 2 | Create test_wizard.py with 14 unit + integration tests | 18a124f | backend/tests/test_wizard.py, backend/app/core/plan_gate.py, backend/app/main.py |

## Verification Results

All 14 wizard tests pass:
```
14 passed, 3 warnings in 2.59s
```

Tests cover:
- `test_parse_and_validate_valid_json` — valid JSON returns all 5 fields
- `test_parse_and_validate_ticker_in_rationale` — PETR4 raises ValueError
- `test_parse_and_validate_ticker_hglg11` — HGLG11 raises ValueError
- `test_parse_and_validate_no_ticker_false_positive` — FII/CDI/SELIC pass
- `test_parse_and_validate_sum_over_103` — sum=110 raises ValueError
- `test_parse_and_validate_markdown_fences` — strips fences before parsing
- `test_build_prompt_includes_macro` — SELIC/CDI/IPCA in prompt
- `test_build_prompt_includes_portfolio` — portfolio section present
- `test_build_prompt_no_portfolio` — no-portfolio fallback text
- `test_start_wizard_202` — authenticated user gets 202 + job_id + disclaimer
- `test_start_wizard_unauthenticated` — unauthenticated gets 401
- `test_get_wizard_job_not_found` — nonexistent job returns 404
- `test_disclaimer_in_start_response` — disclaimer matches CVM_DISCLAIMER exactly
- `test_get_wizard_job_returns_delta_on_completion` — completed job returns delta

## VPS Migration

SSH into VPS at 185.173.110.180 was not possible (no SSH key configured locally). The migration 0016_add_wizard_jobs.py exists and needs to be applied manually via:
```bash
ssh root@185.173.110.180 "cd /app/financas && docker compose exec api alembic upgrade head"
ssh root@185.173.110.180 "cd /app/financas && docker compose restart worker"
```

This is a deferred manual step - the local test infrastructure works correctly with SQLite in-memory (wizard_jobs table created via create_all).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed offset-naive vs offset-aware datetime comparison in plan_gate.py**
- **Found during:** Task 2, test_start_wizard_202 getting 500 instead of 202
- **Issue:** `user.trial_ends_at > datetime.now(tz=timezone.utc)` fails because SQLite returns naive datetimes while comparison used UTC-aware datetime
- **Fix:** Normalize `trial_ends_at` to UTC-aware before comparison with `replace(tzinfo=timezone.utc)` if `tzinfo is None`
- **Files modified:** backend/app/core/plan_gate.py, backend/app/main.py
- **Commit:** 18a124f

**2. [Scope note] Intentionally NOT fixed in ai/router.py**
- The same datetime bug exists in `app/modules/ai/router.py::_get_user_plan`
- Fixing it would change `test_analyze_asset_returns_403_for_free_user` from a quick 500-fail to a hang (the test would trial-elevate a new user to "pro" then try Celery dispatch)
- Pre-existing test was already failing before this plan — NOT a regression from plan 11-01 work
- Filed in deferred-items: fix ai/router.py datetime + update ai pipeline test to use expired-trial user

## Known Stubs

None — all test assertions are real, no placeholder data in the wizard module itself.

## Self-Check: PASSED

- [x] backend/tests/test_wizard.py exists (246 lines)
- [x] backend/tests/conftest.py has wizard model import and dispatch mock
- [x] backend/app/core/plan_gate.py has datetime normalization fix
- [x] Commit 2acd52d exists (Task 1)
- [x] Commit 18a124f exists (Task 2)
- [x] 14 test functions in test_wizard.py
- [ ] VPS migration not verified (SSH unavailable) — manual step required
