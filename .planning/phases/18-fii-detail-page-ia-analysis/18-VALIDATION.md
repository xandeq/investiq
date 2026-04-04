---
phase: 18
slug: fii-detail-page-ia-analysis
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-04
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `backend/pytest.ini` |
| **Quick run command** | `cd backend && python -m pytest tests/test_phase18_fii_detail.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && python -m pytest tests/test_phase18_fii_detail.py -x -q`
- **After every plan wave:** Run `cd backend && python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green + Playwright `e2e/fii-detail.spec.ts` passing
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 0 | SCRF-04 | unit | `pytest tests/test_phase18_fii_detail.py::test_fetch_fii_data_structure -x` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | SCRF-04 | integration | `pytest tests/test_phase18_fii_detail.py::test_post_fii_analysis_returns_202 -x` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | SCRF-04 | integration | `pytest tests/test_phase18_fii_detail.py::test_get_fii_analysis_job -x` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | SCRF-04 | unit | `pytest tests/test_phase18_fii_detail.py::test_dividends_monthly_format -x` | ❌ W0 | ⬜ pending |
| 18-02-01 | 02 | 2 | SCRF-04 | e2e | `cd frontend && npx playwright test e2e/fii-detail.spec.ts` | ❌ W0 | ⬜ pending |
| 18-02-02 | 02 | 2 | SCRF-04 | e2e | `cd frontend && npx playwright test e2e/fii-detail.spec.ts::fii-disclaimer` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_phase18_fii_detail.py` — unit + integration stubs for SCRF-04 (fetch_fii_data structure, POST /analysis/fii/{ticker}, GET /analysis/{job_id}, dividends_monthly format)
- [ ] `frontend/e2e/fii-detail.spec.ts` — smoke + CVM disclaimer regression tests

*All test files are new — Wave 0 must create them before implementation waves.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| BRAPI summaryProfile returns FII portfolio fields (num_imoveis, tipo_contrato, vacância) | SCRF-04 | External API — fields not guaranteed; requires live BRAPI call with real FII ticker | `curl "https://brapi.dev/api/quote/HGLG11?modules=summaryProfile" -H "Authorization: Bearer $BRAPI_TOKEN"` and verify fields present or "Dado não disponível" displayed |
| P/VP history chart renders with bookValue approximation | SCRF-04 | bookValue availability varies by ticker; visual check required | Load `/fii/HGLG11` and verify P/VP line chart appears or graceful "Dado não disponível" fallback |
| "Gerar Análise IA" button triggers spinner immediately | SCRF-04 | Async UX timing — requires real Celery worker | Click button, verify spinner appears within 500ms, narrative appears after completion |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
