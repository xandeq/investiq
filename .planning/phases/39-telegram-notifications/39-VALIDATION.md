---
phase: 39
slug: telegram-notifications
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-17
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (backend) + Playwright (E2E frontend) |
| **Config file** | `backend/pytest.ini` / `frontend/playwright.config.ts` |
| **Quick run command** | `cd backend && python -m pytest tests/ -x -q --timeout=30` |
| **Full suite command** | `cd backend && python -m pytest tests/ -q && cd ../frontend && npx playwright test --reporter=line` |
| **Estimated runtime** | ~60 seconds (pytest) + ~120 seconds (playwright) |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/ -x -q --timeout=30`
- **After every plan wave:** Run full suite (pytest + playwright)
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds (pytest quick run)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 1 | TG-01 | unit | `python -m pytest tests/test_profile.py -k "telegram" -x -q` | ❌ W0 | ⬜ pending |
| 39-01-02 | 01 | 1 | TG-01 | unit | `python -m pytest tests/test_profile.py -k "telegram" -x -q` | ❌ W0 | ⬜ pending |
| 39-01-03 | 01 | 1 | TG-02 | unit | `python -m pytest tests/test_signal_engine.py -k "notify" -x -q` | ❌ W0 | ⬜ pending |
| 39-02-01 | 02 | 2 | TG-01 | e2e | `npx playwright test e2e/profile.spec.ts --reporter=line` | ✅ | ⬜ pending |
| 39-02-02 | 02 | 2 | TG-03 | e2e | `npx playwright test e2e/profile.spec.ts --reporter=line` | ✅ | ⬜ pending |
| 39-02-03 | 02 | 2 | TG-01/02/03 | e2e | `npx playwright test e2e/regression-phase39-telegram.spec.ts --reporter=line` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_profile.py` — add stubs for `test_patch_telegram_chat_id`, `test_patch_telegram_requires_pro`, `test_patch_telegram_disconnect`
- [ ] `backend/tests/test_signal_engine.py` — add stubs for `test_notify_users_for_signal_sends_to_pro_users`, `test_notify_users_skips_null_chat_id`
- [ ] `frontend/e2e/regression-phase39-telegram.spec.ts` — E2E regression spec stub

*Existing `tests/test_profile.py` and `e2e/profile.spec.ts` already exist — only new test functions needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Telegram message delivered to real chat | TG-02 | Requires live Telegram API + real chat_id | Set own chat_id in profile → trigger signal scan → check Telegram app |
| Disconnect removes notifications | TG-03 | Requires live bot | Clear chat_id → trigger scan → confirm no message arrives |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
