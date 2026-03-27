---
phase: 02-portfolio-engine-market-data
plan: "02-03"
subsystem: portfolio-engine
tags: [cmp, custo-medio-ponderado, tdd, pure-functions, decimal, b3, corporate-events]
dependency_graph:
  requires: ["02-01"]
  provides: ["cmp-engine", "Position", "apply_buy", "apply_sell", "apply_corporate_event", "build_position_from_history"]
  affects: ["02-04-portfolio-service"]
tech_stack:
  added: []
  patterns: ["pure-function-domain-core", "tdd-red-green-refactor", "decimal-arithmetic-invariants", "duck-typed-inputs"]
key_files:
  created:
    - backend/app/modules/portfolio/cmp.py
    - backend/tests/test_cmp.py
    - backend/tests/test_portfolio_positions.py
  modified: []
decisions:
  - "CMP engine implemented as pure functions with no framework coupling — enables exhaustive unit testing before DB wiring in Plan 02-04"
  - "apply_corporate_event accepts string action_type (not enum) — duck-typed for test convenience; callers pass CorporateActionType.value"
  - "build_position_from_history uses duck-typed inputs (no SQLAlchemy) — service layer provides real models; tests use simple dataclasses"
  - "total_cost stored on Position dataclass — redundant with qty×cmp but makes desdobramento/grupamento invariant verifiable in O(1)"
  - "8 decimal places (ROUND_HALF_UP) chosen — sufficient for B3 CVM precision, matches Brazilian IR declaration requirements"
metrics:
  duration_minutes: 4
  completed_date: "2026-03-14"
  tasks_completed: 2
  files_created: 3
  files_modified: 0
  tests_added: 14
  tests_passing: 14
requirements_satisfied: [PORT-05, PORT-06]
---

# Phase 2 Plan 3: CMP Engine — Preço Médio Ponderado Summary

**One-liner:** Pure-function CMP engine with full Decimal arithmetic implementing B3/CVM custo médio ponderado — desdobramento, grupamento, bonificação, and build_position_from_history all passing 14 TDD tests including all B3 official examples.

## What Was Built

The CMP (Custo Médio Ponderado) calculation engine: the legally mandated cost basis methodology for Brazilian investment accounts per Instrução CVM 8/1979. All arithmetic uses Python `Decimal` with 8 decimal places (ROUND_HALF_UP) — no float literals anywhere.

### Files Created

**`backend/app/modules/portfolio/cmp.py`** (324 lines)
- `Position` dataclass: `ticker`, `quantity`, `cmp`, `total_cost`, `asset_class`
- `apply_buy(position, qty, unit_price, brokerage_fee=None) -> Position`: B3 weighted average formula; brokerage fee absorbed into effective_price
- `apply_sell(position, qty, sale_price) -> tuple[Position, Decimal]`: CMP unchanged, returns `(new_pos, realized_pnl)`; raises `ValueError` on oversell
- `apply_corporate_event(position, action_type, factor, issue_price=None) -> Position`: desdobramento (split), grupamento (reverse split), bonificação
- `build_position_from_history(ticker, asset_class, transactions, corporate_actions) -> Position`: chronological replay; corporate actions before same-date transactions (B3 ex-date rule)

**`backend/tests/test_cmp.py`** (11 unit tests)
- All B3 official examples: Buy 100@10, Buy 50@12 → CMP=10.6667; Sell 80@15 → P&L=346.67
- Desdobramento factor=2: qty×2=140, CMP÷2=5.3333, total_cost unchanged
- Grupamento factor=2: qty÷2=50, CMP×2=20, total_cost unchanged
- Bonificação 10% at R$8: qty=110, CMP=(100×10+10×8)/110=9.8182, total_cost=1080
- ValueError on sell more than held

**`backend/tests/test_portfolio_positions.py`** (3 integration tests)
- `test_position_after_split_then_sell`: 200 shares → split ×3 → sell 150 → qty=450, CMP=3.33
- `test_multiple_buys_then_grupamento`: 3 buys, reverse split ×4 → qty=100, CMP=60
- `test_build_position_from_history_ordering`: same-date corporate event + transaction → corporate applied first

## Test Results

```
14 passed, 0 failed
tests/test_cmp.py         11 passed
tests/test_portfolio_positions.py  3 passed
Full regression suite: 85 passed, 7 skipped
```

## Success Criteria Verification

- [x] `pytest tests/test_cmp.py -v` shows all 11 tests passing
- [x] `pytest tests/test_portfolio_positions.py -v` shows all 3 tests passing
- [x] B3 official examples verified: Buy 100@10+50@12=CMP 10.6667; Sell 80@15 P&L=346.67; Split 1:2 qty=140 cmp=5.3333
- [x] `grep -n "float(" cmp.py` returns no results — AST-verified no float literals
- [x] `apply_corporate_event` handles desdobramento, grupamento, bonificacao
- [x] `apply_sell` raises `ValueError` when qty > held
- [x] `build_position_from_history` applies corporate events before same-date transactions

## Deviations from Plan

None — plan executed exactly as written.

The plan provided the full implementation body inline. The TDD RED/GREEN/REFACTOR phases were executed strictly: tests committed first (RED — ImportError confirmed), then implementation (GREEN — all 14 pass), refactor was inline (docstrings and inline B3 formula comments added during implementation, no post-refactor commit needed as no logic changed).

## Self-Check: PASSED

Files exist:
- FOUND: backend/app/modules/portfolio/cmp.py
- FOUND: backend/tests/test_cmp.py
- FOUND: backend/tests/test_portfolio_positions.py

Commits:
- a98dbbe: test(02-03): add failing tests for CMP engine (RED phase)
- de195fa: feat(02-03): implement CMP engine — pure Decimal arithmetic (GREEN+REFACTOR)
