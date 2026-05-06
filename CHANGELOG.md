# Changelog

## 2026-05-06

### Added

- Added `IOFEngine` for Cash Parking Advisor Phase 2.
- Added pytest coverage for all 30 IOF regressivo rates, 30+ day zero-rate behavior, and invalid non-positive holding periods.
- Added Cash Parking Advisor backend module:
  - DIAX pull client with `X-Integration-Key` and 1h Redis cache.
  - Deterministic ranking service with IR + IOF + Poupanca handling.
  - `GET /advisor/cash-parking`.
  - Action Inbox `cash_parking` card source.
- Added Cash Parking Advisor frontend:
  - `/caixa` page.
  - TanStack Query hook and API client.
  - Recommendation hero and ranked table.
  - App navigation and Action Inbox support for `cash_parking`.

### Verified

- `python -m pytest backend/tests/test_iof_engine.py -q` -> 35 passed.
- `python -m pytest backend/tests/test_market_universe_tasks.py backend/tests/test_renda_fixa_macro_rates.py -q` -> 11 passed.
- `python -m pytest backend/tests/test_iof_engine.py backend/tests/test_cash_flow_advisor_client.py backend/tests/test_cash_flow_advisor_service.py backend/tests/test_cash_flow_advisor_router.py backend/tests/test_advisor_inbox.py backend/tests/test_advisor_health.py -q` -> 56 passed.
- `npx tsc --noEmit` still fails on pre-existing non-Cash-Parking generic table typing issues; filtered output shows no Cash Parking frontend errors.
