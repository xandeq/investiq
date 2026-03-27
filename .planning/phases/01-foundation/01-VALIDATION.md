---
phase: 1
slug: foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + anyio (async) |
| **Config file** | `backend/pytest.ini` — Wave 0 gap |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/ -x -q`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-* | 01-01 | 1 | EXT-01 | structural | manual-only — folder structure review | N/A | ⬜ pending |
| 1-02-01 | 01-02 | 2 | AUTH-01 | unit + integration | `pytest tests/test_auth.py::test_register -x` | ❌ W0 | ⬜ pending |
| 1-02-02 | 01-02 | 2 | AUTH-02 | integration | `pytest tests/test_auth.py::test_email_verification_flow -x` | ❌ W0 | ⬜ pending |
| 1-02-03 | 01-02 | 2 | AUTH-03 | integration | `pytest tests/test_auth.py::test_login_cookies -x` | ❌ W0 | ⬜ pending |
| 1-02-04 | 01-02 | 2 | AUTH-04 | integration | `pytest tests/test_auth.py::test_password_reset -x` | ❌ W0 | ⬜ pending |
| 1-02-05 | 01-02 | 2 | EXT-03 | unit | `pytest tests/test_auth.py::test_email_adapter_swappable -x` | ❌ W0 | ⬜ pending |
| 1-03-* | 01-03 | 3 | AUTH-05 | integration (RLS) | `pytest tests/test_rls.py -x` | ❌ W0 | ⬜ pending |
| 1-04-* | 01-04 | 4 | EXT-02 | unit | `pytest tests/test_schema.py::test_plan_enum -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/pytest.ini` — pytest config with `anyio_mode = "auto"`
- [ ] `backend/tests/conftest.py` — async DB fixture using `app_user` role (not superuser), test DB setup/teardown
- [ ] `backend/tests/test_auth.py` — stubs for AUTH-01, AUTH-02, AUTH-03, AUTH-04, EXT-03
- [ ] `backend/tests/test_rls.py` — stubs for AUTH-05 (tenant isolation assertions)
- [ ] `backend/tests/test_schema.py` — stubs for EXT-02 (plan enum), EXT-03 (schema validation)
- [ ] Framework install: `pip install pytest anyio pytest-anyio httpx asgi-lifespan`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Adding `app/modules/portfolio/` requires zero changes in `app/core/` or `app/modules/auth/` | EXT-01 | Structural check — import boundary review | After Phase 1 complete: add empty `app/modules/portfolio/__init__.py`, verify no changes needed in `app/core/` or `app/modules/auth/`; review import graph |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
