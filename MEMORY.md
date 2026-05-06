# InvestIQ Memory

## Current Active Work

Cash Parking Advisor is active on branch `feat/cash-parking-advisor`.

The canonical design and implementation plan remain:

- `docs/plans/2026-04-29-cash-parking-feature-design.md`
- `docs/plans/2026-04-30-cash-parking-feature-implementation.md`

## 2026-05-06 Update

InvestIQ Cash Parking Advisor is feature-complete on this branch:

- Added `IOFEngine` in `backend/app/modules/market_universe/iof_engine.py`.
- Behavior: `rate_for_days(holding_days)` returns IOF as a fraction of yield, e.g. `Decimal("0.96")` for day 1 and `Decimal("0.00")` for day 30+.
- Non-positive holding periods raise `ValueError`.
- Tests are in `backend/tests/test_iof_engine.py` and cover all table entries plus boundaries.
- Added `backend/app/modules/cash_flow_advisor/`:
  - `client.py`: DIAX pull client, `X-Integration-Key`, 1h Redis cache.
  - `schemas.py`: DIAX projection and cash-parking response models.
  - `service.py`: deterministic ranking across Tesouro Selic, CDB DI 100/102/110%, Fundo DI 95%, and Poupanca.
  - `router.py`: `GET /advisor/cash-parking`.
- Added Action Inbox integration:
  - New `InboxCardKind`: `cash_parking`.
  - `_cash_parking_to_cards()` emits at most one card linking to `/caixa`.
  - Source degrades silently when DIAX is unconfigured, unavailable, macro rates are missing, or available cash is below R$1k.
- Added frontend:
  - `/caixa` page in `frontend/app/caixa/page.tsx`.
  - `frontend/src/features/cash_flow_advisor/` API/hook/components.
  - App navigation entry under Mercado.
  - Action Inbox frontend support for `cash_parking`.

## Architecture Notes

- IOF is intentionally separate from `TaxEngine`; `TaxEngine` remains the IR regressivo engine backed by DB `tax_config`, while `IOFEngine` is statutory fixed table logic.
- No module-level DB state or external calls were introduced.
- Phase 2 has no DIAX runtime dependency and is safe to use in Phase 3 service calculations.
- The new `/advisor/cash-parking` route must remain registered before `advisor_router`; otherwise `/advisor/{job_id}` shadows it.
- Poupanca anniversary behavior is conservative in v1: no yield when the window is under a 30-day anniversary cycle.

## Remaining Work

- Merge the feature branch after confirming no unrelated dirty files are included.
- Operational smoke: configure `DIAX_BASE_URL` and `DIAX_INTEGRATION_KEY`, seed DIAX cash flow, open `/caixa`, and verify ranked rows reflect the next outflow.
- Next product work: Fase 23 alertas confiáveis.
