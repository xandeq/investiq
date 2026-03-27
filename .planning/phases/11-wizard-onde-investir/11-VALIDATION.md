---
phase: 11
slug: wizard-onde-investir
status: active
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-24
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest with asyncio_mode=auto |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd /app && python -m pytest tests/test_wizard.py -x -q` |
| **Full suite command** | `cd /app && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd /app && python -m pytest tests/test_wizard.py -x -q`
- **After every plan wave:** Run `cd /app && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 0 | WIZ-03 | integration | `pytest tests/test_wizard.py::test_start_wizard_202 -x` | no W0 | pending |
| 11-01-02 | 01 | 0 | WIZ-02 | unit | `pytest tests/test_wizard.py::test_ticker_detected_raises -x` | no W0 | pending |
| 11-01-03 | 01 | 0 | WIZ-02 | unit | `pytest tests/test_wizard.py::test_valid_json_passes -x` | no W0 | pending |
| 11-01-04 | 01 | 0 | WIZ-04 | unit | `pytest tests/test_wizard.py::test_prompt_includes_macro -x` | no W0 | pending |
| 11-01-05 | 01 | 0 | WIZ-05 | unit | `pytest tests/test_wizard.py::test_disclaimer_in_response -x` | no W0 | pending |
| 11-01-06 | 01 | 0 | WIZ-03 | integration | `pytest tests/test_wizard.py::test_get_wizard_job -x` | no W0 | pending |
| 11-01-07 | 01 | 0 | WIZ-03 | integration | `pytest tests/test_wizard.py::test_get_wizard_job_returns_delta_on_completion -x` | no W0 | pending |
| 11-02-01 | 02 | 1 | WIZ-01 | manual | Visual inspection — multi-step UI | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_wizard.py` — unit + integration tests for WIZ-02, WIZ-03, WIZ-04, WIZ-05
- [ ] No new conftest needed — existing `tests/conftest.py` has `register_verify_and_login` and async fixtures

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Multi-step wizard renders steps 1-3 with progress indicator and back-navigation | WIZ-01 | Frontend UI behavior — no headless test runner configured | Navigate to /wizard, verify step indicator shows 3 steps, fill step 1 and advance, use Voltar button to go back, verify inputs are retained |
| CVM disclaimer renders before form and before results | WIZ-05 | Visual order verification | On /wizard, verify amber box is first element — above step indicator, above form, above results |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Exception: WIZ-01** — accepted as manual-only. No headless frontend test runner available; visual verification documented in Manual-Only table above.

**Approval:** signed-off (2026-03-24)
