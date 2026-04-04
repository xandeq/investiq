---
phase: 17-fii-screener-table
verified: 2026-04-04T00:00:00Z
status: passed
score: 9/9 must-haves verified
re_verification: false
---

# Phase 17: FII Screener Table Verification Report

**Phase Goal:** Usuário vê tabela de FIIs ranqueados por score composto e consegue filtrar por segmento e DY mínimo em segundos.
**Verified:** 2026-04-04
**Status:** passed
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | GET /fii-screener/ranked returns all FIIs ordered by composite score descending | VERIFIED | `router.py:62` — `FIIMetadata.score.desc().nullslast()` |
| 2 | Score formula: DY*0.5 + P/VP_inverted*0.3 + liquidity*0.2 | VERIFIED | `tasks.py:820` — `Decimal(str(dy_rank * 0.5 + pvp_rank_inv * 0.3 + liq_rank * 0.2))` |
| 3 | Response includes segmento field for client-side segment filtering | VERIFIED | `router.py:81` — `segmento=fii.segmento`; `schemas.py:22` — `segmento: str \| None` |
| 4 | Response includes dy_12m field for client-side DY minimum filtering | VERIFIED | `router.py:82` — `dy_12m=str(fii.dy_12m) if fii.dy_12m is not None else None` |
| 5 | calculate_fii_scores Celery beat task registered at 08:00 BRT daily | VERIFIED | `celery_app.py:116-118` — key `"calculate-fii-scores-daily"` with `crontab(minute=0, hour=8)` |
| 6 | FIIs with NULL metrics receive NULL score and appear at bottom | VERIFIED | `tasks.py` NULL guard in score formula; `router.py:62` — `.nullslast()` ordering |
| 7 | User sees table with columns: Rank, Ticker, Segmento, DY 12m, P/VP, Liquidez, Score | VERIFIED | `FIIScoredScreenerContent.tsx:201-209` — all 7 `<th>` headers rendered |
| 8 | Segment dropdown and DY min input filter table instantly (client-side useMemo) | VERIFIED | `FIIScoredScreenerContent.tsx:104-116` — `useMemo` over `data.results` with both filters |
| 9 | Ticker cells link to /fii/[ticker] | VERIFIED | `FIIScoredScreenerContent.tsx:74-76` — `<Link href={\`/fii/${row.ticker}\`}>` |

**Score:** 9/9 truths verified

---

## Required Artifacts

### Plan 01 (Backend)

| Artifact | Provided | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/0021_add_fii_score_columns.py` | Migration adding 8 score columns to fii_metadata | VERIFIED | Correct revision chain: `0020_add_analysis_tables`. All 8 columns present. Full downgrade. |
| `backend/app/modules/fii_screener/router.py` | GET /fii-screener/ranked endpoint | VERIFIED | 104 lines. Real query, NULLS LAST ordering, auth-gated, rate-limited 30/min. |
| `backend/app/modules/fii_screener/schemas.py` | FIIScoredRow, FIIScoredResponse Pydantic models | VERIFIED | Both classes defined with all required fields including `score_available: bool`. |
| `backend/tests/test_phase17_fii_screener.py` | All Phase 17 backend tests | VERIFIED | 293 lines, 9+ test functions including integration tests. |

### Plan 02 (Frontend)

| Artifact | Provided | Status | Details |
|----------|----------|--------|---------|
| `frontend/src/features/fii_screener/types.ts` | FIIScoredRow, FIIScoredResponse interfaces | VERIFIED | Both exported interfaces with all required fields. |
| `frontend/src/features/fii_screener/api.ts` | getFIIScreenerRanked function | VERIFIED | Calls `/fii-screener/ranked` via `apiClient`. |
| `frontend/src/features/fii_screener/hooks/useFIIScreener.ts` | useFIIScoredScreener React Query hook | VERIFIED | `queryKey: ["fii-screener-ranked"]`, `staleTime: 1000 * 60 * 60`. |
| `frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx` | Main screener table component | VERIFIED | 247 lines (> 100 min). Full table, both filters, loading skeleton, error, empty state, score-not-available banner. |
| `frontend/app/fii/screener/page.tsx` | Next.js static route at /fii/screener | VERIFIED | Imports and renders `FIIScoredScreenerContent`. Page at correct path (frontend/app/, not src/app/). |

---

## Key Link Verification

### Plan 01 Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `fii_screener/router.py` | `market_universe/models.py` | `select(FIIMetadata).order_by(score.desc())` | WIRED | `router.py:55-65` — `select(FIIMetadata, ...).order_by(FIIMetadata.score.desc().nullslast())` |
| `celery_app.py` | `market_universe/tasks.py` | beat_schedule entry for calculate_fii_scores | WIRED | `celery_app.py:116-119` — key "calculate-fii-scores-daily" with correct task path |
| `main.py` | `fii_screener/router.py` | include_router with /fii-screener prefix | WIRED | `main.py:39,134` — import and `include_router(fii_screener_router, prefix="/fii-screener")` |

### Plan 02 Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `fii_screener/api.ts` | `/fii-screener/ranked` | apiClient GET call | WIRED | `api.ts:5` — `apiClient<FIIScoredResponse>("/fii-screener/ranked")` |
| `FIIScoredScreenerContent.tsx` | `hooks/useFIIScreener.ts` | useFIIScoredScreener hook | WIRED | `FIIScoredScreenerContent.tsx:4,100` — import and destructured call |
| `AppNav.tsx` | `/fii/screener` | NavItem href | WIRED | `AppNav.tsx:67` — `{ href: "/fii/screener", label: "FII Screener", icon: ScanSearch }` |

---

## Requirements Coverage

| Requirement | Source Plans | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| SCRF-01 | 17-01, 17-02 | Tabela de FIIs ranqueados por score composto (DY 12m, P/VP, liquidez diária) | SATISFIED | Backend computes score nightly; frontend renders 7-column ranked table |
| SCRF-02 | 17-01, 17-02 | Filtrar FIIs por segmento | SATISFIED | `FIIScoredScreenerContent.tsx:101,107` — segment dropdown with instant useMemo filter |
| SCRF-03 | 17-01, 17-02 | Filtrar FIIs por DY mínimo dos últimos 12 meses | SATISFIED | `FIIScoredScreenerContent.tsx:102,108-113` — DY min input with `rowDy * 100 < minDy` comparison |

**Note:** SCRF-04 (FII detail page) is correctly deferred to Phase 18. It is not claimed by any Phase 17 plan and is not a gap here.

---

## Anti-Patterns Found

None. Checked for: TODO/FIXME comments, placeholder returns, empty stub implementations, hardcoded empty data flowing to rendering. The two matches found (`placeholder="Ex: 8"` as an HTML attribute, and `return []` as a loading guard before data arrives) are legitimate and not stubs.

---

## Human Verification Required

### 1. Segment filter matches actual CVM data labels

**Test:** Log in to InvestIQ at /fii/screener after `calculate_fii_scores` has run once. Open the Segmento dropdown and select "Logistica". Check whether any FIIs appear or all rows are filtered out.
**Expected:** At least some FIIs show up when selecting real CVM segment labels (e.g., "Logistica", "Papel", "Shopping").
**Why human:** The segment strings in `SEGMENTOS` constant are hardcoded in the frontend. If CVM data uses different casing or labels (e.g., "Logística" with accent vs "Logistica" without), the filter returns zero results. This is a runtime data-matching concern that cannot be verified from static code inspection.

### 2. Score-not-available banner shown before first Celery run

**Test:** On a fresh deployment (before the 08:00 BRT task runs), navigate to /fii/screener.
**Expected:** Yellow banner reads "Scores sendo calculados — disponíveis amanhã após o processamento noturno dos dados."
**Why human:** Requires a runtime state where `score_available === false` — not reproducible from static analysis.

### 3. DY filter conversion accuracy

**Test:** Type "8" into the DY min input. Confirm that only FIIs with DY 12m >= 8% appear.
**Expected:** The conversion `rowDy * 100 < minDy` correctly treats `dy_12m=0.09` as 9%. FIIs with `dy_12m < 0.08` are excluded.
**Why human:** Requires actual production data to confirm backend stores DY as a decimal fraction (0.09 = 9%) rather than already as a percentage (9.0 = 9%).

---

## Summary

Phase 17 goal is fully achieved. All 9 observable truths are verified against the actual codebase:

- **Backend (Plan 01):** Migration 0021 adds 8 score columns. `_percentile_ranks()` helper and `calculate_fii_scores` Celery task are substantive and use sync DB session correctly. Beat schedule registered at `crontab(minute=0, hour=8)`. GET `/fii-screener/ranked` endpoint queries FIIMetadata with NULLS LAST ordering, requires auth, and is rate-limited. Router is registered in `main.py`.

- **Frontend (Plan 02):** All 4 feature files exist under `frontend/src/features/fii_screener/`. Page is at the correct App Router path `frontend/app/fii/screener/page.tsx` (not `src/app/`). AppNav has the FII Screener link and `/fii` in `activePrefixes`. Component is 247 lines with real filtering logic via `useMemo`, ticker links to `/fii/[ticker]`, and handles all required states (loading, error, empty, score-not-available).

- **Requirements:** SCRF-01, SCRF-02, and SCRF-03 are all satisfied. SCRF-04 is correctly deferred to Phase 18.

Three items are flagged for human verification: segment label matching against actual CVM data, the score-not-available runtime state, and DY decimal conversion accuracy. None of these represent code defects — they are runtime data concerns.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
