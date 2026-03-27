---
phase: 11-wizard-onde-investir
plan: "02"
subsystem: wizard-frontend
tags: [wizard, frontend, multi-step, ux]
dependency_graph:
  requires: [11-01]
  provides: [wizard-frontend-multistep]
  affects: [frontend/src/features/wizard/components/WizardContent.tsx]
tech_stack:
  added: []
  patterns: [React state machine, multi-step form, polling]
key_files:
  modified:
    - frontend/src/features/wizard/components/WizardContent.tsx
decisions:
  - "CVM disclaimer rendered as first child before StepIndicator — WIZ-05 requirement"
  - "Step state managed with useState<1|2|3> — no router, no external state"
  - "Reset button calls reset() + setStep(1) to restore form to initial state"
metrics:
  completed_date: "2026-03-26"
  tasks_completed: 2
  files_changed: 1
---

# Phase 11 Plan 02: WizardContent Multi-Step Wizard Summary

One-liner: Refactored WizardContent.tsx from single-form to 3-step wizard with progress indicator, back navigation, and CVM disclaimer as first element.

## Tasks Completed

| Task | Name | Key Files |
|------|------|-----------|
| 1 | Implement StepIndicator component and step state | frontend/src/features/wizard/components/WizardContent.tsx |
| 2 | Refactor form to 3 steps (Valor → Prazo → Perfil) with Voltar/Próximo | frontend/src/features/wizard/components/WizardContent.tsx |

## Verification Results

All WIZ requirements met:

- **WIZ-01** ✅ 3-step wizard with progress indicator (circles 1, 2, 3 + labels Valor, Prazo, Perfil)
- **WIZ-01** ✅ Step 1: valor input only; Step 2: prazo selectors only; Step 3: perfil cards + submit button
- **WIZ-01** ✅ Voltar buttons on Steps 2 and 3 — input values preserved across navigation
- **WIZ-05** ✅ CVM amber disclaimer is FIRST child before StepIndicator
- **WIZ-02** ✅ No ticker symbols in rendered output
- **WIZ-03** ✅ Processing spinner and results render correctly after submit
- 414 lines total in WizardContent.tsx (min 200 requirement met)

## VPS Deployment (PENDING)

Four migrations pending on VPS (SSH was unavailable):

```bash
ssh root@185.173.110.180 "cd /app/financas && docker compose exec backend alembic upgrade head"
```

Migrations to apply:
- `0016_add_wizard_jobs` — wizard_jobs table + RLS
- `0017` — drop import_staging unique constraint (fixes re-upload IntegrityError)
- `0018_normalize_assetclass_enum_lowercase` — CRITICAL: fixes LookupError 'FII' on dashboard
- `0019_add_ai_usage_logs` — ai_usage_logs table

Backend files requiring docker cp:
- `backend/app/modules/wizard/` (router, tasks, models, schemas)
- `backend/app/modules/ai/` (provider, usage_router, tasks)
- `backend/app/modules/portfolio/models.py` (AssetClass enum lowercase)
- `backend/app/modules/imports/parsers/` (csv_parser.py, xlsx_parser.py)
- `backend/app/core/plan_gate.py` (datetime normalization fix)
- `backend/app/main.py` (wizard router registration)
- `backend/app/celery_app.py`

Frontend: rebuild required (wizard page + AppNav changes).

## Known Stubs

None.

## Self-Check: PASSED

- [x] WizardContent.tsx has StepIndicator component (lines 109–130)
- [x] WizardContent.tsx has 3 step branches (step === 1, step === 2, step === 3)
- [x] CVM disclaimer is first child of outer `<div className="space-y-6">`
- [x] Voltar buttons on steps 2 and 3 call `setStep(n-1)`
- [x] `reset()` in useWizard hook also calls `setStep(1)`
- [ ] VPS migration not verified (SSH unavailable) — manual step required
