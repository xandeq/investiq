---
phase: 39-telegram-notifications
plan: "01"
subsystem: backend
tags: [telegram, notifications, celery, fastapi, migration, profile]
dependency_graph:
  requires: []
  provides:
    - "users.telegram_chat_id column via migration 0038"
    - "GET /profile/telegram endpoint"
    - "PATCH /profile/telegram endpoint (pro-gated)"
    - "app.core.telegram.send_telegram_notification shared sender"
    - "telegram_bot.notify_users_for_signal Celery task"
    - "scan_and_store_signals fan-out dispatch hook"
  affects:
    - "backend/app/modules/signal_engine/tasks.py (scan_and_store_signals now dispatches fan-out)"
    - "backend/app/modules/telegram_bot/tasks.py (new Celery task added)"
tech_stack:
  added:
    - "app/core/telegram.py — shared HTTP sender using requests.post(timeout=10)"
    - "Pydantic v2 field_validator for telegram_chat_id format validation (^-?\\d{1,20}$)"
  patterns:
    - "Celery sync DB pattern via get_superuser_sync_db_session (no asyncpg in worker)"
    - "Pro-or-trial gate (_is_pro_or_trial helper) reused from ai-mode pattern"
    - "Fan-out wrapped in try/except so broker outage never breaks scan task"
    - "timezone-naive/aware normalization for SQLite+PostgreSQL compatibility"
key_files:
  created:
    - backend/alembic/versions/0038_add_telegram_chat_id.py
    - backend/app/core/telegram.py
    - backend/tests/test_telegram_notifications.py
  modified:
    - backend/app/modules/auth/models.py
    - backend/app/modules/profile/router.py
    - backend/app/modules/telegram_bot/tasks.py
    - backend/app/modules/signal_engine/tasks.py
decisions:
  - "Normalize trial_ends_at timezone before comparison to support both SQLite (naive) and PostgreSQL (aware) — prevents 500 error in tests"
  - "Patch app.core.db_sync.get_superuser_sync_db_session (not app.modules.telegram_bot.tasks.get_superuser_sync_db_session) because the function uses a local import inside the task body"
  - "Use side_effect=async_coroutine_fn (not return_value) when patching _run_scan_and_store, because asyncio.run() calls the function and then runs the coroutine"
  - "Disconnect (null telegram_chat_id) always allowed for any plan — pro gate only blocks non-null writes"
metrics:
  duration: "~25 minutes"
  completed: "2026-05-17"
  tasks_completed: 3
  files_modified: 7
---

# Phase 39 Plan 01: Backend Telegram Notification Infrastructure Summary

Backend infrastructure for per-user Telegram signal notifications: DB column, profile endpoints, shared sender module, Celery fan-out task, and signal engine hook.

## What Was Built

**Migration 0038** adds `telegram_chat_id VARCHAR(32) NULL` to the `users` table (commit `8f372c0`). `User.telegram_chat_id: Mapped[str | None]` added to the SQLAlchemy model immediately after `ai_mode`.

**`app/core/telegram.py`** provides `send_telegram_notification(chat_id, text) -> bool` — a shared sender that POSTs to `https://api.telegram.org/bot{TOKEN}/sendMessage` with `timeout=10` and `parse_mode=HTML`. Never raises; returns `False` on any failure (missing token, empty chat_id, HTTP error).

**Profile router** gains two new endpoints (commit `13a8e4e`):
- `GET /profile/telegram` — returns `{"telegram_chat_id": null}` or the saved value
- `PATCH /profile/telegram` — pro-gated for non-null values; null (disconnect) always allowed

**`telegram_bot/tasks.py`** gains `notify_users_for_signal` Celery task (name: `telegram_bot.notify_users_for_signal`), registered on `celery_app` (commit `9eeb6af`). The task:
1. Returns early if `signals=[]` or `TELEGRAM_BOT_TOKEN` not set
2. Queries users with `plan='pro'` OR active trial and non-null `telegram_chat_id` via `get_superuser_sync_db_session`
3. Calls `send_telegram_notification(chat_id, message)` for each eligible user
4. Returns `{"status": "ok", "notified": N}`

**`signal_engine/tasks.py`** hook (line 103–112 after edit): after `_send_telegram_signals(new_signals)`, dispatches `notify_users_for_signal.delay(new_signals)` in a try/except to prevent broker outage from crashing the scan.

## Signal hook point (for debugging)

```
scan_and_store_signals():
    new_signals = asyncio.run(_run_scan_and_store())  # line 101
    if new_signals:
        _send_telegram_signals(new_signals)            # line 103 — admin alert
        try:
            notify_users_for_signal.delay(new_signals) # line 106 — per-user fan-out (Phase 39)
        except ...:
            ...
```

## Telegram API Contract

- URL: `https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage`
- Method: POST, JSON body `{chat_id, text, parse_mode: "HTML"}`
- Timeout: 10 seconds
- Error behavior: logs WARNING, returns `False` (never raises)
- Message format: HTML with `<b>` tickers linked to `https://investiq.com.br/stock/{ticker}`

## Test Coverage

12 tests added in `backend/tests/test_telegram_notifications.py`:

| # | Test | Requirement |
|---|------|-------------|
| 1 | `test_get_telegram_returns_null_when_not_set` | TG-01 |
| 2 | `test_patch_telegram_saves_chat_id_for_pro_user` | TG-01 |
| 3 | `test_patch_telegram_disconnect_with_null` | TG-03 |
| 4 | `test_patch_telegram_free_user_returns_403` | TG-01 gate |
| 5 | `test_patch_telegram_free_user_can_disconnect` | TG-03 |
| 6 | `test_patch_telegram_trial_user_allowed` | TG-01 trial elevation |
| 7 | `test_patch_telegram_rejects_invalid_format` | TG-01 validation |
| 8 | `test_notify_users_for_signal_sends_to_pro_with_chat_id` | TG-02 |
| 9 | `test_notify_users_for_signal_skips_empty_signals` | TG-02 |
| 10 | `test_notify_users_for_signal_continues_on_send_failure` | TG-02 resilience |
| 11 | `test_scan_and_store_signals_dispatches_fanout` | TG-02 dispatch |
| 12 | `test_scan_and_store_signals_no_dispatch_on_empty` | TG-02 dispatch guard |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fix timezone-aware/naive datetime comparison**
- **Found during:** Task 2, test 6 (trial user allowed)
- **Issue:** `_is_pro_or_trial` compared `user.trial_ends_at` (timezone-naive from SQLite) with `datetime.now(tz=timezone.utc)` (timezone-aware), causing `TypeError: can't compare offset-naive and offset-aware datetimes`
- **Fix:** Normalize `trial_ends_at` to UTC-aware with `.replace(tzinfo=timezone.utc)` when `tzinfo is None`
- **Files modified:** `backend/app/modules/profile/router.py`
- **Commit:** `13a8e4e`

**2. [Rule 1 - Bug] Fix mock patch path for `get_superuser_sync_db_session`**
- **Found during:** Task 2/3 tests 8-10
- **Issue:** Plan specified patching `app.modules.telegram_bot.tasks.get_superuser_sync_db_session` but the function is imported inside the task body (local import), so the attribute doesn't exist at module level — patch raises `AttributeError`
- **Fix:** Patch `app.core.db_sync.get_superuser_sync_db_session` (the source), not the import reference
- **Files modified:** `backend/tests/test_telegram_notifications.py`
- **Commit:** `13a8e4e`

**3. [Rule 1 - Bug] Fix `asyncio.run()` mock pattern for `_run_scan_and_store`**
- **Found during:** Task 3, test 11
- **Issue:** Plan's example used `mock.return_value = _fake_scan()` — but `scan_and_store_signals` calls `asyncio.run(_run_scan_and_store())`, so the mock must be called first (yielding a coroutine) which asyncio.run then executes. Setting `return_value` to a coroutine causes `asyncio.run()` to receive the mock return value directly instead
- **Fix:** Use `side_effect=_fake_coroutine_fn` so each call to the patched function returns a fresh awaitable coroutine
- **Files modified:** `backend/tests/test_telegram_notifications.py`
- **Commit:** `9eeb6af`

## Known Stubs

None. All 6 plan truths are implemented and verified by tests.

## Commits

| Hash | Description |
|------|-------------|
| `8f372c0` | Migration 0038 + User.telegram_chat_id column |
| `13a8e4e` | Shared sender + profile endpoints + 10 tests |
| `9eeb6af` | Celery fan-out task + signal_engine hook + 2 more tests |

## Self-Check: PASSED

All files exist:
- FOUND: backend/alembic/versions/0038_add_telegram_chat_id.py
- FOUND: backend/app/core/telegram.py
- FOUND: backend/app/modules/profile/router.py
- FOUND: backend/app/modules/telegram_bot/tasks.py
- FOUND: backend/app/modules/signal_engine/tasks.py
- FOUND: backend/tests/test_telegram_notifications.py

All commits exist:
- FOUND: 8f372c0 (Migration 0038 + model column)
- FOUND: 13a8e4e (Shared sender + profile endpoints + 10 tests)
- FOUND: 9eeb6af (Celery fan-out + signal_engine hook + 2 tests)

Test verification: 12/12 passed
