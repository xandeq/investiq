---
phase: 12
slug: foundation-legal-cost-control-async-architecture
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-31
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. Phase 12 focuses on legal compliance, quota enforcement, data versioning, and async infrastructure stability.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Playwright (frontend) |
| **Config file** | `backend/pyproject.toml` (pytest section) |
| **Quick run command** | `pytest backend/tests/test_phase12_foundation.py -v --tb=short` |
| **Full suite command** | `pytest backend/tests/ -k "phase12 or quota or versioning or async" -v --cov=backend/app --cov-report=term` |
| **Estimated runtime** | ~45 seconds (unit + integration) |

---

## Sampling Rate

- **After every task commit:** Run `pytest backend/tests/test_phase12_foundation.py::test_quota_enforcement_* -v` (2 min feedback)
- **After every plan wave:** Run full suite with coverage report (5 min)
- **Before `/gsd:verify-work`:** Full suite must be green + coverage >85% for modified modules
- **Max feedback latency:** 2 minutes

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | AI-09 | integration | `pytest test_phase12_foundation.py::test_api_response_includes_disclaimer` | ✅ | ⬜ pending |
| 12-01-02 | 01 | 1 | AI-09 | unit | `pytest test_phase12_foundation.py::test_disclaimer_component_renders` | ✅ W0 | ⬜ pending |
| 12-02-01 | 02 | 1 | AI-11 | unit | `pytest test_phase12_foundation.py::test_quota_enforcement_free_tier_blocks_requests` | ✅ | ⬜ pending |
| 12-02-02 | 02 | 1 | AI-11 | unit | `pytest test_phase12_foundation.py::test_quota_enforcement_pro_tier_allows_50_per_month` | ✅ | ⬜ pending |
| 12-02-03 | 02 | 2 | AI-11 | integration | `pytest test_phase12_foundation.py::test_rate_limiting_middleware_enforced` | ✅ W0 | ⬜ pending |
| 12-02-04 | 02 | 2 | AI-11 | unit | `pytest test_phase12_foundation.py::test_cost_tracking_per_analysis_type` | ✅ | ⬜ pending |
| 12-03-01 | 03 | 2 | AI-08 | unit | `pytest test_phase12_foundation.py::test_analysis_includes_data_version_id` | ✅ | ⬜ pending |
| 12-03-02 | 03 | 2 | AI-08 | unit | `pytest test_phase12_foundation.py::test_data_timestamp_visible_in_api` | ✅ | ⬜ pending |
| 12-03-03 | 03 | 2 | AI-12 | integration | `pytest test_phase12_foundation.py::test_async_job_lifecycle_complete` | ✅ W0 | ⬜ pending |
| 12-03-04 | 03 | 2 | AI-12 | unit | `pytest test_phase12_foundation.py::test_celery_task_error_handling` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_phase12_foundation.py` — All 15+ unit and integration tests from RESEARCH.md section 6
- [ ] `backend/tests/conftest.py` — Shared fixtures: `db_session`, `auth_user_free`, `auth_user_pro`, `auth_user_enterprise`, `client` (FastAPI TestClient)
- [ ] `backend/tests/fixtures/analysis_fixtures.py` — Sample ticker data (PETR4, VALE3, BBDC4), mock BRAPI responses
- [ ] Alembic migration script (migration 0003): Create `analysis_quota_logs`, `analysis_jobs`, `analysis_cost_logs` tables
- [ ] pytest plugins: `pytest-asyncio` for async test support

**Status:** All deliverables defined. Tests are provided in RESEARCH.md Section 6.2 (50+ test cases).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| CVM legal compliance memo reviewed by counsel | AI-09 | Requires legal expert judgment on registration threshold and positioning | 1) Schedule call with CVM compliance lawyer. 2) Review disclaimer language. 3) Document registration threshold (user count trigger). 4) Obtain written memo. 5) Store in `.planning/docs/CVM_AUDIT_MEMO_2026-03-31.md` |
| Fallback provider timing acceptable in staging | AI-12 | OpenRouter → Groq latency varies; must validate <30s in real conditions | 1) Deploy to staging. 2) Run 50 concurrent DCF requests. 3) Measure p95 latency. 4) Verify <30s. 5) Document in RESEARCH.md Appendix B |
| Cost estimation accuracy (once data flows) | AI-11 | Can only verify after analysis runs in staging with real LLM calls | 1) Run 10 sample analyses (all types: DCF, earnings, dividend, sector). 2) Compare logged cost vs actual OpenRouter invoice. 3) Verify ±5% accuracy. 4) Adjust cost multipliers if needed. 5) Document variance in cost tracking dashboard |

**All technical behaviors have automated verification. Manual items are regulatory/ops sign-off.**

---

## Validation Sign-Off

- [ ] All unit tests in `test_phase12_foundation.py` passing (green ✅)
- [ ] Coverage report shows >85% for modified modules (`app/services/analysis_quota.py`, `app/services/analysis_versioning.py`, `app/services/analysis_async.py`)
- [ ] Integration tests confirm end-to-end flow: quota check → async job submit → data versioning → response with metadata
- [ ] Fallback provider switching tested under load (50 concurrent requests, p95 <30s)
- [ ] Cost tracking logger emits valid entries for each analysis type (DCF, earnings, dividend, sector)
- [ ] CVM compliance memo obtained and stored
- [ ] Sampling continuity: no >3 consecutive commits without automated test feedback
- [ ] No watch-mode flags or flaky tests in suite
- [ ] Feedback latency <2 minutes (pytest runs in <45s)
- [ ] `nyquist_compliant: true` set in frontmatter once all above passed

**Approval:** Pending execution (awaiting plan execution start)
