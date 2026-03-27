---
gsd_state_version: 1.0
milestone: v1.1
milestone_name: — Onde Investir
status: unknown
last_updated: "2026-03-24T12:05:08.174Z"
progress:
  total_phases: 6
  completed_phases: 5
  total_plans: 18
  completed_plans: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-03-21)

**Core value:** O usuário controla toda sua carteira em um lugar só, com análise financeira de nível institucional integrada
**Current focus:** Phase 11 — wizard-onde-investir

## Current Position

Phase: 11 (wizard-onde-investir) — EXECUTING
Plan: 2 of 2

## v1.0 Status Reference

| Phase | Status |
|-------|--------|
| 1. Foundation | Complete (2026-03-14) |
| 2. Portfolio Engine + Market Data | Complete (2026-03-14) |
| 3. Dashboard + Core UX | Checkpoint (human-verify) |
| 4. AI Analysis Engine | Not started |
| 5. Import + Broker Integration | Complete (2026-03-15) |
| 6. Monetization | Not started |

## Accumulated Context

- Stack: FastAPI + SQLAlchemy async + Next.js 15 + PostgreSQL + Redis + Celery
- Deploy: docker cp → docker compose restart (nao docker build — apt-get falha na rede do VPS)
- VPS: 185.173.110.180, path: /app/financas/
- BRAPI token disponivel (gratuito, 15k req/mes) — cotacoes B3
- Milestone v1.0 phases 1, 2, 5 completos; 3, 4, 6 pendentes (monetizacao e dashboard)

### v1.1 Architecture Decisions

- `get_global_db` FastAPI dependency required for all screener/catalog tables — must NOT use tenant-scoped `get_db`
- Redis namespaces: `screener:universe:{TICKER}`, `tesouro:rates:{BOND_CODE}`, `fii:metadata:{TICKER}` — never use `market:*` prefix for v1.1 data
- TaxEngine IR rates must be DB config (not constants) — LCI/LCA exemption reform pending in 2026
- Tesouro Direto: old JSON endpoint 404 since Aug 2025 — use ANBIMA API (register at developers.anbima.com.br) or CKAN CSV fallback
- CDB/LCI/LCA rates: no public live API exists — `fixed_income_catalog` table with curated reference ranges, UI must say "taxas de referencia de mercado"
- Screener universe rebuild: ~900 tickers via brapi.dev with 200ms sleep — Celery beat only, never per-request
- AI wizard output: asset class percentages only — ticker validation post-processing required (reject uppercase 4-6 char strings)
- CVM Res. 19/2021 disclaimer must appear BEFORE results render, not as footnote

### Open Questions (resolve in Phase 7)

- ANBIMA API auth model (OAuth2 client credentials?) — confirm at developers.anbima.com.br before writing Tesouro fetch task
- brapi.dev rate limit behavior under 900-ticker daily rebuild — monitor first production run
- Allocation model parameters (expected returns per profile per asset class) — requires sign-off from Alexandre before Phase 10

## Decisions

- **07-01:** Global tables use GRANT instead of RLS — app_user has direct access since no per-tenant data in screener_snapshots, fii_metadata, fixed_income_catalog, tax_config
- **07-01:** TaxEngine accepts pre-loaded rows (not session) — enables pure unit testing; instantiate per-request, not as module-level singleton, so rate changes take effect after restart
- [Phase 11-wizard-onde-investir]: SQLite returns naive datetimes for DateTime(timezone=True) columns -- normalize with replace(tzinfo=utc) before comparison in plan_gate.py and main.py

## Performance Metrics

- Sessions: 2
- Plans executed: 1 (07-01)
- Phases complete: 0/5 (07 in progress)

| Phase | Plan | Duration | Tasks | Files |
|-------|------|----------|-------|-------|
| 07-foundation-data-pipelines | 01 | 8min | 2 | 8 |
| 07-foundation-data-pipelines | 02 | 1 session | 2 | 3 |
| Phase 11-wizard-onde-investir P01 | 15min | 2 tasks | 4 files |
