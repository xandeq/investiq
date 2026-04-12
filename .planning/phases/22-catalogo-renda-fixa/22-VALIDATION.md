---
phase: 22
slug: catalogo-renda-fixa
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (backend), Playwright (E2E) |
| **Config file** | `backend/pytest.ini` (existing) |
| **Quick run command** | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_renda_fixa_macro_rates.py -x -q` |
| **Full suite command** | `cd D:/claude-code/investiq/backend && python -m pytest -x -q` |
| **Estimated runtime** | ~15 seconds (quick), ~60 seconds (full) |

---

## Sampling Rate

- **After every task commit:** Run `cd D:/claude-code/investiq/backend && python -m pytest tests/test_renda_fixa_macro_rates.py -x -q`
- **After every plan wave:** Run `cd D:/claude-code/investiq/backend && python -m pytest -x -q`
- **Before `/gsd:verify-work`:** Full backend suite green + Playwright `tools.spec.ts` green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 0 | RF-03 | unit | `pytest tests/test_renda_fixa_macro_rates.py -x -q` | ❌ W0 | ⬜ pending |
| 22-01-02 | 01 | 1 | RF-03 | unit | `pytest tests/test_renda_fixa_macro_rates.py::test_macro_rates_endpoint -x` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | RF-03 | unit | `pytest tests/test_renda_fixa_macro_rates.py::test_macro_rates_requires_auth -x` | ❌ W0 | ⬜ pending |
| 22-02-01 | 02 | 2 | RF-03 | E2E | `npx playwright test e2e/tools.spec.ts --grep "renda-fixa"` | ✅ existing | ⬜ pending |
| 22-02-02 | 02 | 2 | RF-01, RF-02 | E2E | `npx playwright test e2e/tools.spec.ts --grep "renda-fixa"` | ✅ existing | ⬜ pending |
| 22-02-03 | 02 | 2 | RF-03 | E2E | `npx playwright test e2e/tools.spec.ts --grep "renda-fixa"` | ✅ existing (extend) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_renda_fixa_macro_rates.py` — stub tests for RF-03 endpoint (auth, 200 response, Redis fallback)

*Note: No new conftest fixtures needed — existing `client`, `db_session`, `email_stub` fixtures are sufficient.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Beat indicator shows green/red correctly for CDI/IPCA | RF-03 | Visual rendering with live Redis data | Load /renda-fixa, check product rows show colored indicator vs CDI/IPCA for each holding period |
| Filter buttons update table without page reload | RF-03 | Frontend interaction | Click Tesouro/CDB/LCI/LCA buttons, verify table updates client-side |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
