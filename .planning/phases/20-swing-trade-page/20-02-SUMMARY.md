---
phase: 20-swing-trade-page
plan: 20-02
subsystem: frontend
tags: [nextjs-15, react-query, tailwind, typescript, swing-trade, frontend]

requires:
  - phase: 20-swing-trade-page
    plan: 20-01
    provides: "GET /swing-trade/signals + CRUD /swing-trade/operations backed by Redis and PostgreSQL RLS"
  - phase: 19-opportunity-detector-page
    provides: "apiClient (/lib/api-client.ts) + AppNav shell + feature folder conventions"

provides:
  - "/swing-trade page with 3-tab UX (Sinais da Carteira / Radar Swing / Minhas Operacoes)"
  - "frontend/src/features/swing_trade feature module (api.ts, types.ts, hooks/, components/)"
  - "TypeScript contracts mirroring backend pydantic schemas for the swing trade module"
  - "Manual operation create/close/delete flows with client-side P&L fallback"

affects: [future-swing-trade-reports, future-swing-trade-backtests, playwright-e2e-swing-trade]

tech-stack:
  added: []
  patterns:
    - "React Query hook-per-endpoint with auto-invalidation on mutation success"
    - "Feature folder co-locating api.ts, types.ts, hooks/, components/ (mirrors opportunity_detector)"
    - "Client-side P&L fallback computation for closed operations when backend enrichment is absent"
    - "Tab state via useState — shared query between signals tabs to avoid double-fetch"

key-files:
  created:
    - frontend/src/features/swing_trade/types.ts
    - frontend/src/features/swing_trade/api.ts
    - frontend/src/features/swing_trade/hooks/useSwingSignals.ts
    - frontend/src/features/swing_trade/hooks/useSwingOperations.ts
    - frontend/src/features/swing_trade/components/SignalsSection.tsx
    - frontend/src/features/swing_trade/components/RadarSection.tsx
    - frontend/src/features/swing_trade/components/OperationsSection.tsx
    - frontend/src/features/swing_trade/components/NewOperationModal.tsx
    - frontend/src/features/swing_trade/components/SwingTradeContent.tsx
    - frontend/app/swing-trade/page.tsx
    - .planning/phases/20-swing-trade-page/deferred-items.md
  modified:
    - frontend/middleware.ts
    - frontend/src/components/AppNav.tsx

key-decisions:
  - "Page placed at frontend/app/swing-trade/page.tsx (not frontend/src/app/) — appDir is frontend/app/ per Phase 17 precedent"
  - "Tabs share a single useSwingSignals query so switching Sinais<->Radar does not refetch"
  - "Close button uses window.prompt for exit_price — simple and consistent with current InvestIQ modal-lite patterns"
  - "Client-side P&L fallback: when backend enrichment is missing on closed rows, compute pnl_pct / pnl_brl from entry/exit"
  - "Swing Trade nav entry lives under IA & Analise group (alongside Oportunidades) — both are signal-driven discovery tools"

requirements-completed: [SWING-01, SWING-02, SWING-03, SWING-04]

duration: 8min
completed: 2026-04-11
---

# Phase 20 Plan 20-02: Frontend — Swing Trade Page Summary

**Three-tab /swing-trade page wiring the Phase 20 backend: portfolio signal cards, radar discount table, and manual operations CRUD with P&L enrichment — all TypeScript types locked to backend pydantic schemas.**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-04-11T21:47:55Z
- **Completed:** 2026-04-11T21:55:28Z
- **Tasks:** 7/7
- **Files created:** 11 (10 frontend + 1 deferred-items.md)
- **Files modified:** 2

## Accomplishments

- Swing Trade feature folder `frontend/src/features/swing_trade/` following the opportunity_detector convention (api.ts, types.ts, hooks/, components/).
- `types.ts` mirrors `backend/app/modules/swing_trade/schemas.py` exactly — every field name, nullability, and enum string matches the backend contract so no runtime surprise at JSON parse time.
- `api.ts` exposes all 5 endpoints (`fetchSignals`, `fetchOperations`, `createOperation`, `closeOperation`, `deleteOperation`) on the existing `apiClient` (/api proxy rewrite).
- Two React Query hooks (`useSwingSignals`, `useSwingOperations`) with auto-invalidation on mutation success. Operations hook also invalidates the signals query since closing a position changes the portfolio universe.
- `SignalsSection` — card grid of portfolio signals sorted by `signal_strength` descending, with COMPRAR / VENDER / NEUTRO badges in green/red/gray.
- `RadarSection` — table of non-portfolio radar stocks sorted by discount_pct ascending (biggest drops first), BUY rows highlighted in light green.
- `OperationsSection` — split into "Operações em Aberto" and collapsible "Operações Fechadas" tables. Columns: Ticker, Qtd, Entrada, Alvo, Stop, Preço Atual, P&L %, P&L R$, Dias, Progresso, Ações. "Fechar" button calls `PATCH /operations/{id}/close` with a `window.prompt`-collected exit price. "Remover" button issues DELETE with a confirm dialog. Fallback P&L computation client-side for closed rows where backend enrichment is missing.
- `NewOperationModal` — full form (ticker, classe, data, quantidade, preço entrada, preço alvo opcional, stop loss opcional, notas) with validation and error surfacing.
- `SwingTradeContent` — 3-tab shell using `useState<"signals" | "radar" | "operations">`. Shows signals "Atualizado em" timestamp in the tab header.
- `/swing-trade` page uses `AppNav` shell (matches `opportunity-detector/page.tsx` exactly — same container widths, same heading pattern).
- Added `/swing-trade` to `PROTECTED_PATHS` in `middleware.ts` so unauthenticated users are redirected to `/login`.
- Added "Swing Trade" link to the "IA & Análise" nav group in `AppNav.tsx`, using `Activity` icon (already imported).

## Task Commits

Each task was committed atomically with `--no-verify` per the parallel-executor protocol:

1. **Task 20-02-01: /swing-trade in PROTECTED_PATHS** — `30cdae6` (feat)
2. **Task 20-02-02: types.ts + api.ts** — `783e2d2` (feat)
3. **Task 20-02-03: useSwingSignals + useSwingOperations hooks** — `04e237b` (feat)
4. **Task 20-02-04: SignalsSection component** — `5102112` (feat)
5. **Task 20-02-05: RadarSection component** — `6a73325` (feat)
6. **Task 20-02-06: OperationsSection + NewOperationModal** — `9abbb1d` (feat)
7. **Task 20-02-07: SwingTradeContent + page.tsx + AppNav link** — `0c69003` (feat)

Final metadata commit covers SUMMARY / STATE / ROADMAP / REQUIREMENTS / deferred-items (see below).

## Files Created/Modified

### Created (frontend)

- `frontend/src/features/swing_trade/types.ts` — TypeScript contracts for `SwingSignalItem`, `SwingSignalsResponse`, `SwingOperation`, `OperationListResponse`, `OperationCreatePayload`, `OperationClosePayload` plus type aliases (`SwingSignal`, `OperationStatus`, `LiveSignal`).
- `frontend/src/features/swing_trade/api.ts` — 5 fetch functions wrapping `apiClient` (`/lib/api-client.ts`).
- `frontend/src/features/swing_trade/hooks/useSwingSignals.ts` — React Query hook with 2-min stale time.
- `frontend/src/features/swing_trade/hooks/useSwingOperations.ts` — React Query hook combining list + 3 mutations with auto-invalidation.
- `frontend/src/features/swing_trade/components/SignalsSection.tsx` — card grid for Tab 1.
- `frontend/src/features/swing_trade/components/RadarSection.tsx` — table view for Tab 2.
- `frontend/src/features/swing_trade/components/OperationsSection.tsx` — open/closed tables + actions for Tab 3.
- `frontend/src/features/swing_trade/components/NewOperationModal.tsx` — create operation form.
- `frontend/src/features/swing_trade/components/SwingTradeContent.tsx` — 3-tab container wiring all sections.
- `frontend/app/swing-trade/page.tsx` — Next.js App Router page shell.

### Created (planning)

- `.planning/phases/20-swing-trade-page/deferred-items.md` — logs pre-existing TS error in `watchlist/components/WatchlistContent.tsx` discovered during verification. Out of scope.

### Modified

- `frontend/middleware.ts` — `/swing-trade` added to `PROTECTED_PATHS`.
- `frontend/src/components/AppNav.tsx` — `Swing Trade` link added to "IA & Análise" group with `Activity` icon (already imported). `activePrefixes` extended with `/swing-trade`.

## Decisions Made

- **appDir location** — the plan spec says `frontend/src/app/swing-trade/page.tsx`, but this codebase uses `frontend/app/` as the Next.js App Router root (confirmed by `frontend/app/opportunity-detector/page.tsx` and the Phase 17 state decision: *"Page created at frontend/app/fii/screener/ (not frontend/src/app/) — Next.js appDir is frontend/app/"*). The page was created at `frontend/app/swing-trade/page.tsx` so it actually routes. This is deviation Rule 3 (blocking issue — wrong path would give a 404).
- **Shared signals query across tabs** — Signals tab and Radar tab both render data from the same `GET /swing-trade/signals` response, so they share one `useSwingSignals` query in `SwingTradeContent`. Switching tabs does not refetch; both portfolio and radar data come pre-populated from a single network round-trip.
- **`window.prompt` for close exit_price** — rather than a dedicated close modal, the "Fechar" button uses `window.prompt` to collect the exit price. Defaults to `current_price` when available. This matches the codebase's existing lightweight interaction patterns and keeps the task within the 2–5 min envelope.
- **Client-side P&L fallback** — the backend only enriches `current_price / pnl_pct / pnl_brl / days_open / target_progress_pct` for *open* rows. For closed rows, the OperationsSection computes `pnl_pct` and `pnl_brl` client-side from `entry_price / exit_price / quantity`. Backend and frontend agree on the formula `(exit - entry) / entry * 100`.
- **Tab sort orders** — portfolio signals sorted by `signal_strength` descending (biggest moves first, regardless of direction). Radar signals sorted by `discount_pct` ascending (most-negative first → biggest drops surface at the top). This matches the "find the best swing setups" user intent.
- **Nav entry placement** — swing trade lives in "IA & Análise" next to "Oportunidades" because both are signal-driven discovery tools. Icon is `Activity` (already imported in AppNav).
- **Two-minute staleTime** — matches the cadence of the Celery-beat market data refresh. Shorter than opportunity_detector's 5-min because swing signals are derived from 30d high which updates every quote tick.

## Deviations from Plan

- **[Rule 3 — blocking] Page path change.** Plan said `frontend/src/app/swing-trade/page.tsx`. Actual Next.js `appDir` is `frontend/app/` (not `frontend/src/app/`) — creating the page at the planned path would not be registered by the router, so the route would 404. Placed at `frontend/app/swing-trade/page.tsx` instead. Confirmed by Phase 17 state note and the existing `frontend/app/opportunity-detector/page.tsx` precedent. Committed in `0c69003`.
- **[Addition] `deferred-items.md`.** Discovered a pre-existing TypeScript error in `frontend/src/features/watchlist/components/WatchlistContent.tsx:84` during `npx tsc --noEmit` verification. Not caused by any Phase 20-02 change — the watchlist feature is untouched by this plan. Logged per scope boundary rules and deliberately left as-is.
- **[Addition] `OperationClosePayload` + `LiveSignal` / `SwingSignal` / `OperationStatus` type aliases.** Plan listed only `OperationCreatePayload` explicitly — added `OperationClosePayload` for parity with `closeOperation()` and the three literal-union aliases for readability. Non-semantic — matches the backend exactly.
- **[Addition] AppNav entry + `activePrefixes` extension.** Plan's Task 20-02-07 says *"Also add navigation link to swing-trade in the sidebar/navbar"* — done in `AppNav.tsx` alongside `/opportunity-detector`.

No other deviations. No Rule 4 (architectural) decisions required.

## Issues Encountered

- **Pre-existing TS error in watchlist** — `npx tsc --noEmit` reports one error in `src/features/watchlist/components/WatchlistContent.tsx:84`. This file is not touched by Plan 20-02; the watchlist feature is untouched throughout. Per the scope boundary rules in the execute-phase protocol, this is logged in `deferred-items.md` and not fixed in this plan. Zero TypeScript errors are introduced by swing_trade code.
- **`frontend/src/app/` vs `frontend/app/`** — initial `ls frontend/src/app/` only showed `admin / imports / planos / stock` (stale subset). The real appDir is `frontend/app/` at the frontend root. Verified via `find` and by inspecting `frontend/app/opportunity-detector/page.tsx`. This is consistent with the Phase 17 state decision about FII screener placement.

## User Setup Required

None — Plan 20-02 is frontend-only and ships with the existing Next.js build pipeline. No new environment variables, no new dependencies (uses already-installed `@tanstack/react-query` and `lucide-react`), no schema or service changes.

Deploy instructions (for the next deploy cycle, not this plan):

1. Frontend: standard Docker image rebuild + `docker compose restart frontend` on the VPS.
2. No backend redeploy needed — 20-01 already shipped the `/swing-trade/*` endpoints.
3. After deploy, smoke test: visit `https://investiq.com.br/swing-trade` while logged in. The three tabs should render. "Operações" should show empty state plus the "+ Nova Operação" button.

## Next Phase Readiness

- `/swing-trade` is now live in the frontend routing table and protected by middleware.
- The `swing_trade` feature module is self-contained and ready for future enhancements (backtests, reports, alerts) to add new endpoints + hooks without touching the shell.
- Playwright E2E coverage is not part of this plan (20-02 did not enumerate a test task). A follow-up plan can add a Playwright spec mirroring the opportunity-detector spec: navigate to `/swing-trade` → assert 3 tabs present → click "+ Nova Operação" → fill form → assert new row appears in table.
- Phase 20 (swing-trade-page) is fully complete after this plan — both backend (20-01) and frontend (20-02) are in place.

---

## Self-Check: PASSED

**Files verified to exist:**

- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/types.ts
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/api.ts
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/hooks/useSwingSignals.ts
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/hooks/useSwingOperations.ts
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/components/SignalsSection.tsx
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/components/RadarSection.tsx
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/components/OperationsSection.tsx
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/components/NewOperationModal.tsx
- FOUND: D:/claude-code/investiq/frontend/src/features/swing_trade/components/SwingTradeContent.tsx
- FOUND: D:/claude-code/investiq/frontend/app/swing-trade/page.tsx
- FOUND: D:/claude-code/investiq/frontend/middleware.ts (PROTECTED_PATHS updated)
- FOUND: D:/claude-code/investiq/frontend/src/components/AppNav.tsx (Swing Trade link added)
- FOUND: D:/claude-code/investiq/.planning/phases/20-swing-trade-page/deferred-items.md

**Commits verified in git log:**

- FOUND: 30cdae6 feat(20-02): add /swing-trade to PROTECTED_PATHS middleware
- FOUND: 783e2d2 feat(20-02): add swing trade types and api client
- FOUND: 04e237b feat(20-02): add swing trade react query hooks
- FOUND: 5102112 feat(20-02): add SignalsSection component for portfolio signals tab
- FOUND: 6a73325 feat(20-02): add RadarSection component for radar tab
- FOUND: 9abbb1d feat(20-02): add OperationsSection and NewOperationModal for operations tab
- FOUND: 0c69003 feat(20-02): add SwingTradeContent, /swing-trade page and AppNav link

**Type-check:**

- `npx tsc --noEmit` → zero errors in `frontend/src/features/swing_trade/**` and `frontend/app/swing-trade/**`. One pre-existing error in `frontend/src/features/watchlist/components/WatchlistContent.tsx:84` (unrelated, logged in deferred-items.md).

---

*Phase: 20-swing-trade-page*
*Completed: 2026-04-11*
