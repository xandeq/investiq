---
phase: 17
slug: fii-screener-table
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (asyncio_mode = auto) |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_phase17_fii_screener.py -x -q` |
| **Full suite command** | `cd D:/claude-code/investiq/backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/test_phase17_fii_screener.py -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Req ID | Behavior | Test Type | Automated Command | File Exists | Status |
|--------|----------|-----------|-------------------|-------------|--------|
| SCRF-01 | Score formula produces correct composite score from dy/pvp/liquidity percentile ranks | unit | `pytest tests/test_phase17_fii_screener.py::test_score_formula -x` | ❌ Wave 0 | ⬜ pending |
| SCRF-01 | `calculate_fii_scores` Celery task registered in beat_schedule | unit | `pytest tests/test_phase17_fii_screener.py::test_score_beat_schedule_registered -x` | ❌ Wave 0 | ⬜ pending |
| SCRF-01 | `GET /fii-screener/ranked` returns rows ordered by score desc | integration | `pytest tests/test_phase17_fii_screener.py::test_ranked_endpoint_ordered_by_score -x` | ❌ Wave 0 | ⬜ pending |
| SCRF-01 | `GET /fii-screener/ranked` returns 401 for unauthenticated | integration | `pytest tests/test_phase17_fii_screener.py::test_ranked_endpoint_requires_auth -x` | ❌ Wave 0 | ⬜ pending |
| SCRF-02 | Segment filter in response schema (`segmento` field present) | unit | `pytest tests/test_phase17_fii_screener.py::test_segmento_field_in_response -x` | ❌ Wave 0 | ⬜ pending |
| SCRF-03 | DY filter (client-side) — `dy_12m` field present in response | unit | `pytest tests/test_phase17_fii_screener.py::test_dy_12m_field_in_response -x` | ❌ Wave 0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_phase17_fii_screener.py` — stubs for all 6 test cases above
- No new conftest.py needed — existing `conftest.py` (client, db_session, email_stub) is sufficient

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Client-side segment dropdown filters instantly (no reload) | SCRF-02 | Browser interaction required | Open /fii/screener, select "Logística" from dropdown, verify table updates without page reload |
| DY slider filters correctly (>= threshold) | SCRF-03 | Browser interaction + visual | Drag slider to 8%, verify all visible rows show DY ≥ 8% |
| Ticker click navigates to /fii/[ticker] | SCRF-01 | Navigation behavior | Click a ticker in table, verify URL changes to /fii/[ticker] |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
