---
phase: 7
slug: foundation-data-pipelines
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | backend/pytest.ini or pyproject.toml |
| **Quick run command** | `cd backend && python -m pytest tests/test_phase7/ -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/test_phase7/ -v` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_phase7/ -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/test_phase7/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 7-01-01 | 01 | 1 | SCRA-04 | unit | `pytest tests/test_phase7/test_global_db.py -x -q` | ❌ W0 | ⬜ pending |
| 7-01-02 | 01 | 1 | SCRA-04 | migration | `alembic upgrade head && alembic check` | ❌ W0 | ⬜ pending |
| 7-02-01 | 02 | 1 | SCRA-04 | unit | `pytest tests/test_phase7/test_tax_engine.py -x -q` | ❌ W0 | ⬜ pending |
| 7-03-01 | 03 | 2 | SCRA-04 | unit | `pytest tests/test_phase7/test_celery_tasks.py::test_screener_task -x -q` | ❌ W0 | ⬜ pending |
| 7-03-02 | 03 | 2 | SCRA-04 | unit | `pytest tests/test_phase7/test_celery_tasks.py::test_fii_task -x -q` | ❌ W0 | ⬜ pending |
| 7-03-03 | 03 | 2 | SCRA-04 | unit | `pytest tests/test_phase7/test_celery_tasks.py::test_tesouro_task -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_phase7/__init__.py` — package init
- [ ] `tests/test_phase7/test_global_db.py` — stubs for global DB dependency tests
- [ ] `tests/test_phase7/test_tax_engine.py` — stubs for TaxEngine 4-tier IR tests + LCI/LCA exemption
- [ ] `tests/test_phase7/test_celery_tasks.py` — stubs for all 3 Celery beat task tests
- [ ] `tests/test_phase7/conftest.py` — shared fixtures (mock brapi, mock CVM, mock ANBIMA/CKAN)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CVM FII CSV column names | SCRA-04 | Column names unknown until ZIP downloaded | Download ZIP, inspect CSV headers, record `segmento` and `vacancia_financeira` column names (Wave 0 step) |
| brapi.dev full universe page count | SCRA-04 | Depends on live API response | Call `/quote/list?page=1` and check `totalPages` field |
| Redis namespace isolation in staging | SCRA-04 | Requires running Redis instance | Run `redis-cli keys 'tesouro:*'` and `redis-cli keys 'market:*'` — confirm no overlap |
| Celery beat schedule triggers correctly | SCRA-04 | Requires running Celery beat worker | Check `celery inspect scheduled` output for all 3 tasks |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
