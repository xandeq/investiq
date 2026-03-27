---
phase: 2
slug: portfolio-engine-market-data
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-14
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (already configured) |
| **Config file** | `backend/pytest.ini` — exists with `asyncio_mode = auto` |
| **Quick run command** | `pytest tests/ -x -q` |
| **Full suite command** | `pytest tests/ -v --tb=short` |
| **Estimated runtime** | ~45 seconds (SQLite in-memory + fakeredis) |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_cmp.py tests/test_portfolio_api.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** ~45 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 02-01 | 1 | DATA-01 | integration | `pytest tests/test_market_data_tasks.py::test_celery_broker_alive -x` | ❌ W0 | ⬜ pending |
| 2-01-02 | 02-01 | 1 | DATA-01 | integration | `pytest tests/test_market_data_tasks.py::test_refresh_quotes_writes_redis -x` | ❌ W0 | ⬜ pending |
| 2-02-01 | 02-02 | 1 | DATA-01 | integration | `pytest tests/test_market_data_tasks.py::test_brapi_client_writes_redis -x` | ❌ W0 | ⬜ pending |
| 2-02-02 | 02-02 | 1 | DATA-02 | integration | `pytest tests/test_portfolio_api.py::test_macro_from_redis -x` | ❌ W0 | ⬜ pending |
| 2-02-03 | 02-02 | 1 | DATA-03 | integration | `pytest tests/test_portfolio_api.py::test_fundamentals_from_redis -x` | ❌ W0 | ⬜ pending |
| 2-02-04 | 02-02 | 1 | DATA-04 | integration | `pytest tests/test_portfolio_api.py::test_historical_from_redis -x` | ❌ W0 | ⬜ pending |
| 2-03-01 | 02-03 | 2 | PORT-05 | unit | `pytest tests/test_cmp.py -x` | ❌ W0 | ⬜ pending |
| 2-03-02 | 02-03 | 2 | PORT-06 | unit | `pytest tests/test_cmp.py::test_desdobramento_preserves_total_cost -x` | ❌ W0 | ⬜ pending |
| 2-04-01 | 02-04 | 3 | PORT-01 | integration | `pytest tests/test_portfolio_api.py::test_create_buy_transaction -x` | ❌ W0 | ⬜ pending |
| 2-04-02 | 02-04 | 3 | PORT-02 | integration | `pytest tests/test_portfolio_api.py::test_fii_dividend_exempt -x` | ❌ W0 | ⬜ pending |
| 2-04-03 | 02-04 | 3 | PORT-03 | integration | `pytest tests/test_portfolio_api.py::test_renda_fixa_transaction -x` | ❌ W0 | ⬜ pending |
| 2-04-04 | 02-04 | 3 | PORT-04 | integration | `pytest tests/test_portfolio_api.py::test_bdr_etf_transaction -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_cmp.py` — pure unit tests for CMP engine (PORT-05, PORT-06)
  - test_cmp_initial_buy, test_cmp_buy_sequence, test_cmp_sell_does_not_change_cmp
  - test_cmp_partial_sell, test_desdobramento_preserves_total_cost
  - test_grupamento_preserves_total_cost, test_bonificacao_adjusts_cmp
  - test_corporate_event_before_sell
- [ ] `backend/tests/test_portfolio_api.py` — API integration tests (PORT-01–04, DATA-02–04)
- [ ] `backend/tests/test_market_data_tasks.py` — Celery task tests with mocked brapi.dev + fakeredis (DATA-01)
- [ ] `backend/tests/test_portfolio_positions.py` — position calculation with corporate event sequences
- [ ] New conftest fixtures: `fake_redis_async`, `fake_redis_sync`, `mock_brapi_client`
- [ ] Package install: `pip install python-bcb yfinance psycopg2-binary fakeredis pandas`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Celery beat runs on schedule (15-min market hours) | DATA-01 | Requires real wall-clock time + Docker | `docker compose logs celery-beat` — verify task appears every 15 min between 10h-17h BRT |
| brapi.dev Startup plan rate limits not exceeded | DATA-01 | Requires prod traffic simulation | Monitor brapi.dev dashboard after 24h load |
| Redis TTL expiry behavior under cold start | DATA-01 | Race condition at market open (9h45-10h15) | Manually flush Redis, trigger quote request, verify stale fallback response has `data_stale: true` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 45s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
