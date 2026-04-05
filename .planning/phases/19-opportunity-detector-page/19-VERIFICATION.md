---
phase: 19-opportunity-detector-page
verified: 2026-04-05T09:30:00Z
status: passed
score: 11/11 must-haves verified
re_verification: false
---

# Phase 19: Opportunity Detector Page — Verification Report

**Phase Goal:** Usuário vê na página /opportunity-detector as oportunidades detectadas pelo backend (as mesmas enviadas ao Telegram chat_id 721438452), com histórico, filtros e possibilidade de marcar como acompanhada.
**Verified:** 2026-04-05T09:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from ROADMAP.md Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User accesses /opportunity-detector and sees opportunity list (ticker, tipo, descrição, score, timestamp) | VERIFIED | `page.tsx` renders `OpportunityDetectorContent`; component displays ticker, asset_type, drop_pct, current_price, risk_level, detected_at in a table |
| 2 | User can filter by asset type and by period | VERIFIED | Filter bar has asset_type select (Todos/Ações/Crypto/Renda Fixa) and days select (7/30/90/365), both wired to `useOpportunityHistory` hook which passes them as API query params |
| 3 | Each opportunity shows the same data sent to Telegram (mesma informação) | VERIFIED | `telegram_message` field stored in DB by `save_opportunity_to_db(report.alert_message())` and shown in expandable row detail in a `font-mono` block |
| 4 | Page is protected by auth (PROTECTED_PATHS) | VERIFIED | `middleware.ts` line 5: `PROTECTED_PATHS` includes `/opportunity-detector`; unauthenticated requests redirect to `/login` |
| 5 | Backend exposes GET /opportunity-detector/history persisting detected opportunities | VERIFIED | Router registered at prefix `/opportunity-detector` in `main.py`; endpoint queries `detected_opportunities` table; `save_opportunity_to_db()` called first in `dispatch_opportunity()` before Telegram dispatch |
| 6 | User can mark an opportunity as followed (follow toggle) | VERIFIED | `FollowButton` component calls `markAsFollowed(row.id)` via `useMutation`, on success invalidates `["opportunity-history"]` query; backend PATCH `/{id}/follow` toggles `followed` boolean |

**Score:** 6/6 success criteria verified

### Required Artifacts (Plan 01 — Backend)

| Artifact | Status | Details |
|----------|--------|---------|
| `backend/app/modules/opportunity_detector/models.py` | VERIFIED | `DetectedOpportunity` class with all 17 fields, `__tablename__ = "detected_opportunities"`, no `tenant_id`, UUID default |
| `backend/alembic/versions/0022_add_detected_opportunities.py` | VERIFIED | `revision = "0022_add_detected_opportunities"`, `down_revision = "0021_add_fii_score_columns"` — chain verified (0021 revision matches); creates table + 3 indexes |
| `backend/app/modules/opportunity_detector/schemas.py` | VERIFIED | `OpportunityRowSchema` (17 fields, `model_config = {"from_attributes": True}`) and `OpportunityHistoryResponse` (`total: int`, `results: list[OpportunityRowSchema]`) |
| `backend/app/modules/opportunity_detector/router.py` | VERIFIED | `GET /history` with `asset_type`/`days` filters, `PATCH /{opportunity_id}/follow`; both use `get_global_db`, `get_current_user`, `@limiter.limit("30/minute")`; imports verified |
| `backend/tests/test_opportunity_detector_history.py` | VERIFIED | 12 real tests (22 runs with asyncio+trio), 0 `@pytest.mark.skip` decorators, all pass: `22 passed` |

### Required Artifacts (Plan 02 — Frontend)

| Artifact | Status | Details |
|----------|--------|---------|
| `frontend/app/opportunity-detector/page.tsx` | VERIFIED | Server component (no `"use client"`), exports `metadata`, renders `AppNav` + `OpportunityDetectorContent`, `max-w-7xl` container |
| `frontend/src/features/opportunity_detector/types.ts` | VERIFIED | `OpportunityRow` (17 fields, `asset_type` as union, `detected_at: string`), `OpportunityHistoryResponse` |
| `frontend/src/features/opportunity_detector/api.ts` | VERIFIED | `getOpportunityHistory` with `URLSearchParams` building, `markAsFollowed` with PATCH; both use `apiClient` |
| `frontend/src/features/opportunity_detector/hooks/useOpportunityHistory.ts` | VERIFIED | `useQuery` with `queryKey: ["opportunity-history", filters]`, `staleTime: 300000` |
| `frontend/src/features/opportunity_detector/components/OpportunityDetectorContent.tsx` | VERIFIED | `"use client"`, `RISK_COLORS` map (baixo/medio/alto/evitar), filter bar, table with 8 columns, loading skeleton (`animate-pulse`), error state (`bg-red-50`), empty state ("Nenhuma oportunidade detectada"), `telegram_message` in expandable detail, renda_fixa PITFALL 5 handled |
| `frontend/middleware.ts` | VERIFIED | `PROTECTED_PATHS` contains `/opportunity-detector` and `/fii` (6 entries total) |
| `frontend/e2e/opportunity-detector.spec.ts` | VERIFIED | 4 `test.skip` stubs (intentional — marked as future implementation) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `alert_engine.py` | `models.py` | `save_opportunity_to_db()` called in `dispatch_opportunity()` | WIRED | Line 218: `results["db"] = save_opportunity_to_db(report)` — first call in function body, before Telegram |
| `main.py` | `router.py` | `app.include_router(opportunity_detector_router, prefix="/opportunity-detector")` | WIRED | Lines 40 and 137 in `main.py` confirmed |
| `router.py` | `db.py` | `Depends(get_global_db)` on both endpoints | WIRED | Both `get_opportunity_history` and `mark_as_followed` use `global_db: AsyncSession = Depends(get_global_db)` |
| `api.ts` | `/opportunity-detector/history` | `apiClient` fetch | WIRED | `apiClient('/opportunity-detector/history...')` in `getOpportunityHistory` |
| `useOpportunityHistory.ts` | `api.ts` | `useQuery` calling `getOpportunityHistory` | WIRED | `queryFn: () => getOpportunityHistory(filters)` |
| `middleware.ts` | `/login` | redirect when no `access_token` cookie | WIRED | `PROTECTED_PATHS` includes `/opportunity-detector`; redirect to `/login?redirect=pathname` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| OPDET-01 | Plans 01 and 02 | Página /opportunity-detector com histórico, filtros e follow | SATISFIED | All 5 success criteria verified: list at /opportunity-detector, asset_type+days filters, Telegram message parity, auth protection, backend persistence endpoint |

### Anti-Patterns Scan

Files scanned: all 12 key files created/modified in this phase.

| File | Pattern | Severity | Verdict |
|------|---------|----------|---------|
| `frontend/e2e/opportunity-detector.spec.ts` | `test.skip` | Info | Intentional — documented in plan as stub for future E2E hardening phase |
| All other files | — | — | No TODO/FIXME/placeholder comments; no empty return stubs; no hardcoded empty data flowing to render |

No blockers or warnings found. The `test.skip` stubs in the e2e file are documented intent, not implementation gaps.

### Human Verification Required

#### 1. Visual appearance and table layout at /opportunity-detector

**Test:** Log in to InvestIQ, navigate to /opportunity-detector
**Expected:** Page renders with AppNav, filter bar (Tipo de Ativo + Período dropdowns), table with headers (Data, Ticker, Tipo, Queda, Preço, Risco, Oportun.?, Ação), loading skeleton while fetching
**Why human:** Visual layout and responsiveness cannot be verified programmatically

#### 2. Follow toggle interaction

**Test:** If any opportunity exists in DB, click the star (☆) button on a row
**Expected:** Star turns filled (★), row state updates without page reload
**Why human:** React state mutation interaction and optimistic update behavior requires a live browser

#### 3. Expandable row detail with telegram_message

**Test:** Click on any opportunity row
**Expected:** Expanded section appears below with Causa, Racional de Risco, Mensagem Telegram (mono block), optional Aporte sugerido / Upside alvo fields
**Why human:** Interactive DOM expansion requires browser

#### 4. Renda fixa PITFALL 5

**Test:** If any `renda_fixa` opportunity exists, observe the Queda column
**Expected:** Shows `cause_explanation` text (e.g., "Mudança na taxa Selic") rather than a percentage
**Why human:** Requires live data of type renda_fixa to observe

### Gaps Summary

No gaps. All must-haves verified at all three levels (exists, substantive, wired).

**Backend (Plan 01):**
- DetectedOpportunity model: 17 fields, correct types, no tenant_id
- Migration 0022: correct DDL, chained from 0021, 3 indexes
- `save_opportunity_to_db()`: sync session, all 17 fields mapped, exception-safe, called BEFORE Telegram in `dispatch_opportunity()`
- API endpoints: filters work, auth enforced, GET uses global_db, PATCH toggles and returns 404 on miss
- Tests: 22 real assertions passing (12 tests x 2 anyio backends), no skipped tests

**Frontend (Plan 02):**
- Page shell: server component, metadata, AppNav, delegates to client component
- Client component: all filters wired to API params, risk badges colored, follow mutation with cache invalidation, expandable rows with telegram_message, renda_fixa special case handled
- Auth: /opportunity-detector in PROTECTED_PATHS, redirect to /login

---

_Verified: 2026-04-05T09:30:00Z_
_Verifier: Claude (gsd-verifier)_
