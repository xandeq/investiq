# InvestIQ Roadmap

## Active Milestone: Cash Parking Advisor

Goal: allow the user to ask where to park idle cash using DIAX cash-flow projection plus deterministic net-return ranking across Tesouro Selic, CDB DI, Fundo DI, and Poupanca.

## Status

- Phase 1 DIAX endpoint: complete per Claude memory, commit `a04535e` in DIAX.
- Phase 2 InvestIQ IOFEngine: complete 2026-05-06.
- Phase 3 InvestIQ backend advisor module: complete 2026-05-06.
- Phase 4 InvestIQ frontend `/caixa` and Action Inbox UI: complete 2026-05-06.

## Next Build Order

1. Merge `feat/cash-parking-advisor`.
2. Perform manual smoke with DIAX config and seeded cash-flow projection.
3. Start Fase 23 alertas confiáveis.
4. Then start Fase 25 chart with benchmark, leaving Fase 24 optimization deferred.

## Deferred Risk Items

- Poupanca anniversary logic is conservative in v1 and should be refined with real deposit anniversary dates later.
- Fundo DI come-cotas behavior is not explicitly modeled yet; surface as a future warning/refinement in frontend copy if needed.
- Redis CDI/Selic stale-data detection is not yet implemented for this feature.
