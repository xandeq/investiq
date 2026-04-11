---
phase: 20-swing-trade-page
verified: 2026-04-10T00:00:00Z
status: human_needed
score: 6/6 must-haves verified (code-level); 2 semantic caveats require human sign-off
human_verification:
  - test: "Visit https://investiq.com.br/swing-trade while logged in and confirm the 3 tabs (Sinais da Carteira / Radar Swing / Minhas Operações) render; unauth users get redirected to /login"
    expected: "Three tabs visible, default tab 'Sinais da Carteira' active, 'Atualizado em <timestamp>' shown in header; logged-out request redirects to /login?redirect=/swing-trade"
    why_human: "Exercises Next.js middleware + auth cookies + React Query fetch in a browser; cannot be validated statically"
  - test: "Confirm Success Criterion 1 interpretation — VENDER badge scope"
    expected: "Product owner acknowledges that VENDER status is surfaced on the Operações tab (live_signal='sell' when open op is up >=10% from entry_price) and NOT on dividend-portfolio positions in the Sinais da Carteira tab"
    why_human: "SC1 reads '🔴 VENDER (alta >10% da entrada)' which could imply a portfolio-wide badge, but _classify_signal only returns buy/neutral. The SELL/STOP logic is instead implemented on registered operations via _enrich_operation (live_signal field). This is intentional per Plan 20-01 task 20-01-04 but narrows the signal to registered ops, not to portfolio holdings. Needs product confirmation."
  - test: "Confirm Success Criterion 2 interpretation — Radar universe composition"
    expected: "Product owner accepts that the radar is the curated RADAR_ACOES list (20 IBOV tickers, not 30) unioned with the user's held tickers, filtered to non-portfolio rows, with BUY highlighting for DY>=5% + discount<=-12%. No dynamic 'top 30 by DY' ranking exists."
    why_human: "SC2 says 'top 30 ações IBOV com maior DY'. RADAR_ACOES is 20 hand-curated tickers selected by cap/sector, not by DY ranking. The BUY classifier still enforces DY>=5% so the highlighted rows are dividend-friendly, but the universe size and selection criterion do not literally match SC2. Plan 20-01 explicitly chose the curated list — may be a documentation/spec drift rather than an implementation gap."
  - test: "Create a swing operation end-to-end via the UI and see it land on the table with live P&L"
    expected: "Click 'Nova Operação' → fill PETR4, qty 100, entry 32.50, target 37, stop 30 → submit → new row appears in 'Operações em Aberto' with status ABERTA, P&L computed against current Redis quote, 'Fechar' and ✕ buttons enabled"
    why_human: "Validates the full POST /swing-trade/operations chain (frontend form → apiClient → tenant-scoped backend insert → refetch → enriched read-side P&L). Requires real auth + live Redis cache."
  - test: "Close an open operation via the 'Fechar' button"
    expected: "Click 'Fechar' → window.prompt defaults to current_price → accept → row moves to 'Operações Fechadas' (collapsible), status FECHADA, pnl_pct computed client-side from entry/exit"
    why_human: "Window.prompt interaction, PATCH /operations/{id}/close round-trip, React Query invalidation, client-side P&L fallback — all runtime concerns."
---

# Phase 20: swing-trade-page Verification Report

**Phase Goal (ROADMAP.md):** "Usuário acessa /swing-trade e vê sinais de compra/venda para sua carteira de dividendos, radar de ações com desconto, e pode registrar/acompanhar operações swing manualmente."

**Verified:** 2026-04-10
**Status:** human_needed (6/6 code-level must-haves verified; 2 semantic caveats on Success Criteria 1 and 2 require product owner sign-off)
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth (from Success Criteria) | Status | Evidence |
|---|------------------------------|--------|----------|
| 1 | User sees dividend portfolio with BUY/SELL/NEUTRAL signal badges | PARTIAL | `SignalsSection.tsx` renders COMPRAR/VENDER/NEUTRO badges per `SwingSignalItem.signal`. `_classify_signal` in `service.py:66-73` returns only `buy`/`neutral` — SELL never surfaces on portfolio positions. SELL is only produced on registered operations via `_enrich_operation` (live_signal field). See human verification item #2. |
| 2 | Radar shows top 30 IBOV stocks by DY that are discounted | PARTIAL | `compute_signals` iterates `RADAR_ACOES` (20 curated tickers, not 30, not DY-ranked). BUY filter does enforce DY≥5% so the highlighted radar rows are dividend-friendly. `RadarSection.tsx` tabulates non-portfolio rows sorted by discount. See human verification item #3. |
| 3 | User registers swing operation manually (ticker, qty, entry, target, stop) | VERIFIED | `NewOperationModal.tsx` has ticker/qty/entry_price/entry_date/target_price/stop_price/notes fields with validation → POSTs to `/swing-trade/operations` via `createOperation()` in `api.ts`. Backend `create_operation` in `service.py:248` persists to `swing_trade_operations` table (migration 0023). Tests `test_create_and_list_operation` passes. |
| 4 | Open ops table shows P&L, days open, progress to target | VERIFIED | `OperationsSection.tsx` table columns: Ticker, Qtd, Entrada, Alvo, Stop, Preço Atual, P&L %, P&L R$, Dias, Progresso (bar), Ações. Backend `_enrich_operation` in `service.py:157` computes `current_price`, `pnl_brl`, `pnl_pct`, `days_open`, `target_progress_pct`, `live_signal` from Redis quote + DB row. |
| 5 | Page protected by auth (PROTECTED_PATHS) | VERIFIED | `frontend/middleware.ts:5` contains `"/swing-trade"` in PROTECTED_PATHS. Test `test_signals_unauth_returns_401` + `test_operations_list_unauth_returns_401` + `test_create_unauth_returns_401` pass. |
| 6 | Signals computed from Redis cache only (no new external calls) | VERIFIED | grep for `httpx\|brapi\|requests\.\|aiohttp\|yfinance\|coingecko` in `backend/app/modules/swing_trade/` returns only the docstring comment. `compute_signals` exclusively uses `MarketDataService.get_quote` / `.get_historical` / `.get_fundamentals` which read `market:quote:*` / `market:historical:*` / `market:fundamentals:*` Redis keys. |

**Score:** 6/6 code-level must-haves verified. 2 truths (SC1, SC2) have semantic interpretation caveats requiring human sign-off.

### Required Artifacts

| Artifact | Level 1 (Exists) | Level 2 (Substantive) | Level 3 (Wired) | Status |
|----------|------------------|-----------------------|-----------------|--------|
| `backend/app/modules/swing_trade/models.py` | YES | YES — `SwingTradeOperation` with tenant_id/status/deleted_at | Imported by service + registered in tests/conftest.py | VERIFIED |
| `backend/app/modules/swing_trade/schemas.py` | YES | YES — 6 Pydantic v2 models, Decimal, from_attributes | Imported by router + service | VERIFIED |
| `backend/app/modules/swing_trade/service.py` | YES | YES — compute_signals + CRUD + _classify_signal + _enrich_operation | Imported by router | VERIFIED |
| `backend/app/modules/swing_trade/router.py` | YES | YES — 5 `@router.` decorators at lines 61/91/122/145/172 | main.py imports + includes at prefix `/swing-trade` | VERIFIED |
| `backend/alembic/versions/0023_add_swing_trade_operations.py` | YES | YES — creates table + 2 indexes + dialect-gated RLS | down_revision chains from 0022 | VERIFIED |
| `backend/app/main.py` (router registration) | YES | `line 41: from app.modules.swing_trade.router import router as swing_trade_router` + `line 140: app.include_router(swing_trade_router, prefix="/swing-trade", tags=["swing-trade"])` | Live at runtime | VERIFIED |
| `frontend/middleware.ts` (PROTECTED_PATHS) | YES | `line 5` contains `"/swing-trade"` | Active on every request matcher | VERIFIED |
| `frontend/app/swing-trade/page.tsx` | YES | YES — imports AppNav + SwingTradeContent; metadata set | Next.js appDir route at `/swing-trade` | VERIFIED |
| `frontend/src/features/swing_trade/types.ts` | YES | YES — mirrors backend schemas (6 interfaces + 3 aliases) | Imported by api.ts + hooks + components | VERIFIED |
| `frontend/src/features/swing_trade/api.ts` | YES | YES — 5 fetch functions using apiClient | Imported by hooks | VERIFIED |
| `frontend/src/features/swing_trade/hooks/useSwingSignals.ts` | YES | YES — React Query, 2-min staleTime | Used by SwingTradeContent | VERIFIED |
| `frontend/src/features/swing_trade/hooks/useSwingOperations.ts` | YES | YES — query + 3 mutations with cross-invalidation | Used by SwingTradeContent | VERIFIED |
| `frontend/src/features/swing_trade/components/SignalsSection.tsx` | YES | YES — card grid w/ COMPRAR/VENDER/NEUTRO badge + discount + DY | Rendered by SwingTradeContent | VERIFIED |
| `frontend/src/features/swing_trade/components/RadarSection.tsx` | YES | YES — 8-column table, BUY row highlighted green-50 | Rendered by SwingTradeContent | VERIFIED |
| `frontend/src/features/swing_trade/components/OperationsSection.tsx` | YES | YES — open/closed tables + P&L + Fechar/✕ + modal trigger | Rendered by SwingTradeContent | VERIFIED |
| `frontend/src/features/swing_trade/components/NewOperationModal.tsx` | YES | YES — full form w/ ticker/qty/entry/target/stop/notes validation | Used by OperationsSection | VERIFIED |
| `frontend/src/features/swing_trade/components/SwingTradeContent.tsx` | YES | YES — 3 tabs + shared signals query + operations query | Imported by page.tsx | VERIFIED |
| `frontend/src/components/AppNav.tsx` (nav link) | YES | line 85 adds "Swing Trade" link; line 79 adds `/swing-trade` to activePrefixes | Renders on every authed page | VERIFIED |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|----|--------|---------|
| `/swing-trade` page | `SwingTradeContent` | `import SwingTradeContent from "@/features/swing_trade/components/SwingTradeContent"` | WIRED | page.tsx:3 |
| `SwingTradeContent` | `GET /swing-trade/signals` | `useSwingSignals → fetchSignals → apiClient("/swing-trade/signals")` | WIRED | api.ts:15 |
| `SwingTradeContent` | `GET /swing-trade/operations` | `useSwingOperations → fetchOperations → apiClient("/swing-trade/operations")` | WIRED | api.ts:26 |
| `NewOperationModal` submit | `POST /swing-trade/operations` | `onSubmit → useSwingOperations.createOp → createOperation → apiClient` | WIRED | OperationsSection.tsx:282-311, api.ts:36 |
| `OperationsSection` Fechar button | `PATCH /swing-trade/operations/{id}/close` | `handleCloseOp → window.prompt → onClose → closeOp → closeOperation → apiClient` | WIRED | OperationsSection.tsx:293-311, api.ts:50 |
| `OperationsSection` ✕ button | `DELETE /swing-trade/operations/{id}` | `handleDeleteOp → confirm → onDelete → deleteOp → deleteOperation → apiClient` | WIRED | OperationsSection.tsx:313-328, api.ts:61 |
| `get_signals` endpoint | Redis (MarketDataService) | `compute_signals → MarketDataService.get_quote/get_historical/get_fundamentals → Redis GET market:*` | WIRED | service.py:91-149 |
| `get_signals` endpoint | PortfolioService | `PortfolioService().get_positions(db, tenant_id, redis)` | WIRED | router.py:75-77 |
| `main.py` | `swing_trade_router` | `from app.modules.swing_trade.router import router as swing_trade_router` + `app.include_router(..., prefix="/swing-trade")` | WIRED | main.py:41, 140 |
| middleware | `/swing-trade` auth redirect | `PROTECTED_PATHS.some(p => pathname.startsWith(p))` + cookie check | WIRED | middleware.ts:5, 16, 26 |
| service BUY rule | `discount_pct <= -12.0 AND dy >= 5.0` | `_classify_signal(discount_pct, dy)` constants `BUY_DISCOUNT_THRESHOLD_PCT = -12.0` + `BUY_DY_FLOOR_PCT = 5.0` | WIRED | service.py:46-73 |
| service SELL/STOP rule | `pnl_pct >= 10 → sell; current <= stop → stop` | `_enrich_operation` sets `resp.live_signal` | WIRED | service.py:191-198 |

### Automated Check Results

| Check | Command | Result |
|-------|---------|--------|
| Backend tests (Phase 20) | `python -m pytest tests/test_phase20_swing_trade.py -q` | **32 passed**, 3 pre-existing warnings |
| TypeScript compile (swing_trade scope) | `npx tsc --noEmit 2>&1 \| grep -E "swing_trade\|swing-trade"` | **no swing_trade type errors** (pre-existing watchlist error logged in deferred-items.md is unrelated) |
| Endpoint count | grep `@router\.` in router.py | 5 endpoints: GET /signals, GET /operations, POST /operations, PATCH /operations/{id}/close, DELETE /operations/{id} |
| Redis-only service | grep `httpx\|brapi\|requests\.\|aiohttp\|yfinance\|coingecko` in swing_trade/ | Only 1 hit — docstring comment at service.py:5 (no live calls) |
| Router registration | grep `swing_trade` in main.py | line 41 (import), line 140 (include_router prefix=/swing-trade) |
| middleware.ts contains /swing-trade | grep in middleware.ts | PROTECTED_PATHS line 5 |
| page.tsx exists | `test -f frontend/app/swing-trade/page.tsx` | exists |
| BUY rule: drop >=12% AND DY >=5% | inspection service.py:46-73 | CONFIRMED (unknown-DY allowed — documented decision) |
| SELL rule: gain >=10% from entry | inspection service.py:195-196 | CONFIRMED (scope: registered operations only, via live_signal — not portfolio positions) |
| No brapi calls in compute_signals | inspection service.py:76-149 | CONFIRMED — only MarketDataService Redis reads |

### Requirements Coverage

REQ IDs SWING-01..SWING-04 are declared in plan frontmatter (20-01-PLAN.md:15, 20-02-PLAN.md:19) and ROADMAP.md:100 but are NOT present in `.planning/REQUIREMENTS.md`. Mapping inferred from Success Criteria 1–4:

| Requirement | Source Plan | Inferred Description | Status | Evidence |
|-------------|-------------|----------------------|--------|----------|
| SWING-01 | 20-01, 20-02 | Dividend portfolio signal badges (COMPRAR/VENDER/NEUTRO) | PARTIAL | Code delivers COMPRAR + NEUTRO on portfolio; VENDER only on registered operations via live_signal field. See SC1 caveat — requires product sign-off. |
| SWING-02 | 20-01, 20-02 | Radar of discounted dividend IBOV stocks | PARTIAL | Code delivers radar over 20 curated IBOV tickers (RADAR_ACOES) filtered by BUY rule (DY≥5% AND discount≤-12%), not "top 30 by DY". See SC2 caveat — requires product sign-off. |
| SWING-03 | 20-01, 20-02 | Register manual swing operation (ticker, qty, entry, target, stop) | SATISFIED | NewOperationModal + POST /swing-trade/operations + SwingTradeOperation model + tests passing |
| SWING-04 | 20-01, 20-02 | Operations table with live P&L, days open, progress | SATISFIED | OperationsSection table + _enrich_operation + live_signal (sell/stop/hold) + tests passing |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TODO/FIXME/PLACEHOLDER markers in any Phase 20 file | Info | Clean |
| OperationsSection.tsx | 293-303 | `window.prompt` for close exit_price | Info | Documented decision in 20-02-SUMMARY; matches codebase's lightweight interaction style |
| SwingTradeContent.tsx | 103 | `closePending={false}` hardcoded | Warning | UI button will not visually disable during close mutation; cosmetic only, not a goal blocker |
| service.py | 72 | BUY allowed when DY is unknown (`dy is None or float(dy) >= 5.0`) | Info | Deliberate — documented in 20-01-SUMMARY key-decisions ("Unknown DY = allow BUY") |
| service.py | 66 | `_classify_signal` never returns "sell" | Warning | Portfolio cards will never show VENDER badge — intentional (SELL scope is registered ops only), but narrows SC1 literal reading |

No blocker anti-patterns. No stubs. No placeholder returns. No empty implementations.

---

## Human Verification Required

### 1. Browser smoke test of `/swing-trade` page

**Test:** Log in to https://investiq.com.br, visit `/swing-trade`. Inspect all 3 tabs.
**Expected:** Sinais da Carteira renders cards with portfolio positions + badges + discount %. Radar Swing renders table of non-portfolio stocks. Minhas Operações shows empty state + "+ Nova Operação" button. Unauth user gets redirected to `/login?redirect=/swing-trade`.
**Why human:** Runtime JS, middleware cookie check, React Query fetch — cannot be validated statically.

### 2. [SEMANTIC] SC1 interpretation — VENDER badge scope

**Test:** Confirm with product owner that VENDER is intentionally scoped to *registered operations* (not dividend portfolio positions).
**Expected:** Product owner acknowledges that SC1's "🔴 VENDER (alta >10% da entrada)" is satisfied by the `live_signal` field on `OperationResponse` (set by `_enrich_operation` when `pnl_pct >= 10`), displayed in the Operações tab, not as a badge on Sinais da Carteira cards.
**Why human:** Portfolio positions don't have a unique "entry price" — only a weighted average cost. Plan 20-01 task 20-01-04 explicitly scopes SELL to registered operations. This is a deliberate design choice that narrows the literal reading of SC1. Needs product confirmation.

### 3. [SEMANTIC] SC2 interpretation — Radar universe size/criterion

**Test:** Confirm with product owner that the radar is the curated `RADAR_ACOES` list (20 IBOV tickers) unioned with user holdings, not a dynamic "top 30 by DY" ranking.
**Expected:** Product owner accepts the curated list as a reasonable proxy for "top IBOV dividend names" given the BUY filter (DY>=5%) highlights dividend-friendly opportunities.
**Why human:** SC2 literally says "top 30 ações IBOV com maior DY". The implementation uses 20 curated tickers (cap/sector-selected, not DY-ranked). BUY classifier still enforces DY>=5%, so the net effect is directionally correct but the universe size and selection criterion don't match the literal SC2. Plan 20-01 consciously chose the curated list to avoid duplicating lists and to keep the universe stable. Needs product confirmation or follow-up plan to expand to 30 + DY-sort.

### 4. End-to-end operation creation flow

**Test:** Click "+ Nova Operação" → fill form (PETR4, 100, 32.50, today, target 37, stop 30, "test") → submit.
**Expected:** Modal closes, new row appears in "Operações em Aberto" with status ABERTA. Preço Atual / P&L % / P&L R$ / Dias populated from Redis quote. Target progress bar renders.
**Why human:** Requires real JWT cookie, real Redis cache populated with PETR4 quote, and React Query invalidation round-trip.

### 5. Close operation via "Fechar" button

**Test:** With at least one open op, click "Fechar". A `window.prompt` appears pre-filled with current_price. Accept.
**Expected:** Row moves to "Operações Fechadas" (collapsible), status FECHADA, pnl_pct computed client-side from entry/exit.
**Why human:** window.prompt interaction, PATCH round-trip, cache invalidation, client-side fallback P&L — all runtime.

---

## Gaps Summary

No blocking gaps. All 18 required artifacts exist, are substantive, and are wired into the application. All 32 backend tests pass. TypeScript compiles clean for swing_trade code.

Two Success Criteria (SC1 and SC2) have **semantic interpretation caveats**:

- **SC1 (VENDER badge on portfolio):** The code scopes the SELL signal to *registered operations* (via `live_signal` field), not to dividend portfolio positions. The portfolio cards will only ever show COMPRAR or NEUTRO badges. This is a deliberate design decision (plan 20-01 task 20-01-04) because portfolio positions use weighted-average cost, not an "entry_price" — but it does narrow the literal reading of SC1.

- **SC2 (top 30 IBOV by DY):** The radar universe is a hand-curated list of 20 tickers (`RADAR_ACOES`), unioned with user holdings, sorted by discount, and filtered by BUY classifier (DY>=5% + drop<=-12%). Not a dynamic "top 30 by DY" ranking. Directionally correct but literally smaller and selected by a different criterion.

Both caveats require product-owner sign-off before the phase can be declared fully "passed". Recommendation:

- If product accepts these interpretations → mark phase as **passed** and update ROADMAP.md Success Criteria 1+2 to document the narrower semantics.
- If product wants the literal SC1/SC2 → open follow-up plan to (a) compute portfolio-position "VENDER" based on some entry-price proxy and (b) expand the radar to 30 tickers ranked dynamically by DY.

---

*Verified: 2026-04-10*
*Verifier: Claude (gsd-verifier)*
