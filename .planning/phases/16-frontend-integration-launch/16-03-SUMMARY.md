---
phase: 16
plan: "03"
subsystem: frontend/e2e
tags: [playwright, e2e, testing, stock-detail]
key-files:
  created:
    - frontend/e2e/stock-detail.spec.ts
decisions:
  - Tests written targeting production URL (https://investiq.com.br/stock/PETR4); 2 smoke tests expected to fail until Phase 16 deploy
metrics:
  completed_date: "2026-04-03"
  tasks: 1
  files: 1
---

# Phase 16 Plan 03: Stock Detail E2E Tests — Summary

**One-liner:** Playwright E2E spec with 8 tests covering smoke, regression, mobile (375px), and integration scenarios for the `/stock/[ticker]` page.

## What Was Built

Created `frontend/e2e/stock-detail.spec.ts` with 8 tests across 4 describe groups:

| Group | Tests | Description |
|-------|-------|-------------|
| Smoke | 3 | Unauthenticated redirect, authenticated load OK, no JS errors |
| Regression | 3 | Disclaimer visible, analysis headings present, PETR4 in h1 |
| Mobile | 1 | Disclaimer visible at 375px viewport |
| Integration | 1 | Spinner→content/error flow, no crash (120s timeout) |

## Key Patterns Applied

- Exact import pattern from `ai-features.spec.ts`: `import { test, expect } from '@playwright/test'` + `import { login, pageIsOk } from './helpers'`
- Disclaimer matched via `page.getByText(/recomenda.*investimento/i)` (regex, case-insensitive)
- JS error test filters `ResizeObserver` before asserting `criticalErrors.length === 0`
- Mobile group uses `test.use({ viewport: { width: 375, height: 812 } })`
- Integration group sets `test.setTimeout(120_000)` inside the test body
- Smoke tests use default timeout (no explicit `test.setTimeout`)

## Test Run Results

Smoke tests run against production (`https://investiq.com.br`):
- `unauthenticated user is redirected to login` — FAILED (404: route not yet deployed)
- `authenticated user: /stock/PETR4 loads without error` — FAILED (404: route not yet deployed)
- `no critical JS errors on page load` — PASSED

The 2 failures are expected: the `/stock/[ticker]` page is part of Phase 16 which has not been deployed to production yet. Once Phase 16-01 and 16-02 are deployed, all 8 tests should pass.

## Deviations from Plan

None — spec created exactly as specified.

## Self-Check: PASSED

- `frontend/e2e/stock-detail.spec.ts` exists and has 8 tests
- File follows exact import and structural patterns from `ai-features.spec.ts`
