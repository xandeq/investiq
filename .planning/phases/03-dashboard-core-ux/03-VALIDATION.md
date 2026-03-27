---
phase: 3
slug: dashboard-core-ux
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Backend Framework** | pytest (existing, `backend/tests/`) |
| **Frontend Framework** | None yet — Wave 0 installs Jest + React Testing Library |
| **Backend config file** | `backend/pytest.ini` |
| **Frontend config file** | Wave 0 installs `jest.config.ts` |
| **Backend quick run** | `cd backend && pytest tests/test_dashboard.py -x -q` |
| **Backend full suite** | `cd backend && pytest tests/ -x -q` |
| **Frontend quick run** | `cd frontend && npx jest --testPathPattern=dashboard` |
| **Estimated backend runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_dashboard.py -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full backend suite must be green (96+ passing)
- **Max feedback latency:** 10 seconds (backend); 30 seconds (frontend Jest)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-W0 | 01 | 0 | VIEW-01 | unit stub | `pytest tests/test_dashboard_api.py -x -q` | ❌ W0 | ⬜ pending |
| 03-01-T1 | 01 | 1 | VIEW-01..04 | install + config | `cd frontend && npm run build` | ⬜ | ⬜ pending |
| 03-02-W0 | 02 | 0 | VIEW-01,02 | unit stubs | `pytest tests/test_dashboard_api.py -x -q` | ❌ W0 | ⬜ pending |
| 03-02-T1 | 02 | 1 | VIEW-01,02 | integration | `pytest tests/test_dashboard_api.py::test_dashboard_summary -x -q` | ❌ W0 | ⬜ pending |
| 03-02-T2 | 02 | 1 | VIEW-01,02 | integration | `pytest tests/test_dashboard_api.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-T1 | 03 | 2 | VIEW-03,04 | integration | `pytest tests/test_dashboard_api.py -x -q` | ❌ W0 | ⬜ pending |
| 03-03-T2 | 03 | 2 | VIEW-03,04 | manual | See Manual-Only Verifications | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_dashboard_api.py` — stubs for VIEW-01..04 dashboard summary endpoint tests
- [ ] `backend/app/modules/dashboard/__init__.py` — empty module stub (for import)
- [ ] Wave 0 confirms existing 96 tests still pass (no regressions)

*Frontend test infrastructure (Jest + React Testing Library) installed in Plan 03-01 Task 1.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Allocation pie chart renders with real data | VIEW-01 | Visual rendering — no DOM assertion covers chart | Start dev server, log in, verify donut chart shows asset classes with percentages |
| Portfolio timeseries area chart renders | VIEW-01 | Visual — TradingView Lightweight Charts renders to canvas | Verify area chart appears with data points, axis labels visible |
| P&L cells show green/red color coding | VIEW-02 | CSS color — hard to assert in Jest without visual regression | Check positive P&L = green text, negative = red text |
| Dashboard loads on mobile (375px) | VIEW-01 | Responsive layout | Open browser DevTools → iPhone SE viewport, verify no overflow |
| Benchmark chart shows CDI + IBOVESPA lines | VIEW-03 | Visual multi-series | Verify two named lines appear on rentabilidade chart |
| Dividendos filter by year works | VIEW-04 | Interactive filter state | Change year dropdown, verify table updates without page reload |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s backend / 30s frontend
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
