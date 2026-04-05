---
phase: 19
slug: opportunity-detector-page
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | `backend/pytest.ini` / `backend/pyproject.toml` |
| **Quick run command** | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_opportunity_detector_history.py -x -q` |
| **Full suite command** | `cd D:/claude-code/investiq/backend && python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_opportunity_detector_history.py -x -q`
- **After every plan wave:** Run `python -m pytest -x -q` (full suite, must stay 257+ passing)
- **Before `/gsd:verify-work`:** Full suite must be green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-W0 | 01 | 0 | OPDET-01a/b/c/d/e/f | stub | `pytest tests/test_opportunity_detector_history.py -x` | ❌ W0 | ⬜ pending |
| 19-01-01 | 01 | 1 | OPDET-01a | unit | `pytest tests/test_opportunity_detector_history.py::TestSaveOpportunityToDB -x` | ❌ W0 | ⬜ pending |
| 19-01-02 | 01 | 1 | OPDET-01b | integration | `pytest tests/test_opportunity_detector_history.py::TestHistoryEndpoint -x` | ❌ W0 | ⬜ pending |
| 19-01-03 | 01 | 1 | OPDET-01c | integration | `pytest tests/test_opportunity_detector_history.py::TestHistoryFilters -x` | ❌ W0 | ⬜ pending |
| 19-01-04 | 01 | 1 | OPDET-01d | integration | `pytest tests/test_opportunity_detector_history.py::TestHistoryDaysFilter -x` | ❌ W0 | ⬜ pending |
| 19-01-05 | 01 | 1 | OPDET-01e | integration | `pytest tests/test_opportunity_detector_history.py::TestFollowEndpoint -x` | ❌ W0 | ⬜ pending |
| 19-01-06 | 01 | 1 | OPDET-01f | integration | `pytest tests/test_opportunity_detector_history.py::TestAuthRequired -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_opportunity_detector_history.py` — stubs for OPDET-01a through OPDET-01f (new file)
- [ ] `backend/app/modules/opportunity_detector/models.py` — `DetectedOpportunity` SQLAlchemy model
- [ ] `backend/app/modules/opportunity_detector/schemas.py` — Pydantic schemas
- [ ] `backend/app/modules/opportunity_detector/router.py` — new FastAPI router
- [ ] `backend/alembic/versions/0022_add_detected_opportunities.py` — migration

---

## Requirements Coverage

| Req ID | Sub-behavior | Test Class | Status |
|--------|--------------|------------|--------|
| OPDET-01a | `save_opportunity_to_db` persists all fields | `TestSaveOpportunityToDB` | ⬜ |
| OPDET-01b | GET /history returns list sorted by detected_at desc | `TestHistoryEndpoint` | ⬜ |
| OPDET-01c | GET /history?asset_type=acao filters correctly | `TestHistoryFilters` | ⬜ |
| OPDET-01d | GET /history?days=7 returns only last 7 days | `TestHistoryDaysFilter` | ⬜ |
| OPDET-01e | PATCH /{id}/follow toggles `followed` flag | `TestFollowEndpoint` | ⬜ |
| OPDET-01f | Unauthenticated request returns 401 | `TestAuthRequired` | ⬜ |
