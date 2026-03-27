---
phase: 04-ai-analysis-engine
plan: 01
subsystem: backend/ai
tags: [ai, celery, openai, skills, cvm-compliance]
requires: [03-03]
provides: [ai-provider, ai-skills, celery-tasks]
affects: [backend/app/modules/ai]
tech_stack_added: [httpx-async-llm-calls, boto3-sm-pattern]
tech_stack_patterns: [provider-fallback, celery-asyncio-bridge, skill-adapter-pattern]
key_files_created:
  - backend/app/modules/ai/__init__.py
  - backend/app/modules/ai/provider.py
  - backend/app/modules/ai/skills/__init__.py
  - backend/app/modules/ai/skills/dcf.py
  - backend/app/modules/ai/skills/valuation.py
  - backend/app/modules/ai/skills/earnings.py
  - backend/app/modules/ai/skills/macro.py
  - backend/app/modules/ai/tasks.py
  - backend/tests/test_ai_skills.py
key_files_modified:
  - backend/app/celery_app.py
decisions:
  - "Provider fallback: OpenAI gpt-4o-mini → OpenRouter deepseek/deepseek-chat on 402/429"
  - "asyncio.run() bridges Celery sync tasks to async skill functions — never asyncpg in workers"
  - "Skills return dict with DISCLAIMER_TEXT constant — CVM Res. 19/2021 compliance"
  - "AWS SM keys cached in module-level vars after first fetch — no per-call latency"
metrics:
  completed_date: "2026-03-15"
  tasks_completed: 4
  files_created: 9
  files_modified: 1
---

# Phase 4 Plan 01: AI Skills Adapters Summary

## One-liner

Four async skill adapters (DCF, valuation, earnings, macro) as Celery tasks using OpenAI with OpenRouter fallback via AWS Secrets Manager.

## What Was Built

### AI Provider Client (`provider.py`)

`call_llm(prompt, system, model)` fetches OpenAI key from AWS SM (`tools/openai`) on first call and caches it. On HTTP 402/429 or `insufficient_quota`, automatically falls back to OpenRouter (`tools/openrouter`, model `deepseek/deepseek-chat`). Raises `AIProviderError` only if both providers fail. All keys fetched via subprocess AWS CLI (same pattern as rest of codebase).

### Four Skill Adapters (`skills/`)

- `dcf.py` — `run_dcf(ticker, fundamentals, macro)`: P/L, P/VP, DY, EV/EBITDA vs SELIC/CDI/IPCA
- `valuation.py` — `run_valuation(ticker, fundamentals)`: relative valuation vs sector norms
- `earnings.py` — `run_earnings(ticker, fundamentals)`: earnings quality + payout from DY
- `macro.py` — `run_macro_impact(macro, allocation)`: SELIC/IPCA/PTAX impact on portfolio mix

All four return `{ticker?, analysis, methodology, disclaimer}` where `disclaimer = DISCLAIMER_TEXT` from `skills/__init__.py`.

### Celery Tasks (`tasks.py`)

- `ai.run_asset_analysis(job_id, ticker, tenant_id)` — runs DCF + valuation + earnings via `asyncio.run()`, writes result to DB via `get_sync_db_session()`
- `ai.run_macro_analysis(job_id, tenant_id, allocation)` — runs macro skill, writes result to DB
- `_update_job_status()` helper handles both success and failure DB writes silently

### Tests (`test_ai_skills.py`)

10 tests covering: required keys in return dict, exact CVM disclaimer text match, empty fundamentals handling, empty allocation handling.

## Deviations from Plan

None — plan executed exactly as written. The `celery_app.py` already had `app.modules.ai.tasks` in the include list from a prior setup.

## Self-Check: PASSED

- All `app/modules/ai/` files exist
- `app/modules/ai/tasks.py` — both tasks defined
- `test_ai_skills.py` — file exists with all required tests
- Commit `3c20dbf` exists in git log
