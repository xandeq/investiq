---
phase: 21
slug: screener-de-acoes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (backend) + Playwright (E2E) |
| **Config file** | `backend/pytest.ini` (existing) |
| **Quick run command** | `cd backend && python -m pytest tests/test_screener_universe.py -x -q` |
| **Full suite command** | `cd backend && python -m pytest -x -q` |
| **Estimated runtime** | ~30 seconds (backend unit), ~3 min (full suite + E2E) |

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | Migration 0024 | unit | `cd backend && alembic upgrade head && alembic current` | ❌ W0 | ⬜ pending |
| 21-01-02 | 01 | 1 | brapi 52WeekChange | unit | `cd backend && python -m pytest tests/test_brapi_adapter.py -x -q` | ✅ exists | ⬜ pending |
| 21-01-03 | 01 | 1 | Celery upsert variacao_12m | unit | `cd backend && python -m pytest tests/test_market_universe_tasks.py -x -q` | ✅ exists | ⬜ pending |
| 21-02-01 | 02 | 1 | GET /screener/universe endpoint | unit | `cd backend && python -m pytest tests/test_screener_universe.py -x -q` | ❌ W0 | ⬜ pending |
| 21-02-02 | 02 | 1 | SCRA-01 schema | unit | `cd backend && python -m pytest tests/test_screener_universe.py::test_response_schema -x -q` | ❌ W0 | ⬜ pending |
| 21-03-01 | 03 | 2 | Frontend builds | build | `cd frontend && npm run build 2>&1 | tail -5` | ✅ exists | ⬜ pending |
| 21-03-02 | 03 | 2 | useMemo filters | manual | Load /acoes/screener, apply DY>5%, count rows before/after | N/A | ⬜ pending |
| 21-04-01 | 04 | 2 | SCRA-03 ticker link | E2E | `npx playwright test tests/e2e/acoes_screener.spec.ts -g "ticker link"` | ❌ W0 | ⬜ pending |
| 21-04-02 | 04 | 2 | SCRA-04 pagination | E2E | `npx playwright test tests/e2e/acoes_screener.spec.ts -g "pagination"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_screener_universe.py` — stubs for GET /screener/universe (response shape, auth required, returns list)
- [ ] `tests/e2e/acoes_screener.spec.ts` — Playwright stub: navigate to /acoes/screener, assert table visible, ticker link → /stock/PETR4, pagination

*Existing infrastructure covers backend unit test infrastructure (pytest, conftest.py, async test DB).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Filtros atualizam instantaneamente (sem reload) | SCRA-02 | Browser interaction required | Load /acoes/screener → apply DY filter → verify table updates without page reload |
| Var. 12m% exibe cor correta | SCRA-01 | Visual assertion | Positive values show green, negative show red |
| Market cap tier buttons filtragem | SCRA-02 | Multi-state interaction | Click Small → verify only tickers with market_cap < 2B shown |
| Coluna ordenável (click header) | SCRA-01 | Click-to-sort interaction | Click "DY 12m" header → verify ascending sort → click again → descending |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
