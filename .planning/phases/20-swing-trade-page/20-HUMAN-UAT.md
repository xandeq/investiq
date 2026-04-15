---
status: passed
phase: 20-swing-trade-page
source: [20-VERIFICATION.md]
started: 2026-04-11T00:00:00Z
updated: 2026-04-12T01:03:00Z
tester: Claude (Playwright MCP automated UAT)
---

## Current Test

All 5 tests completed 2026-04-12.

## Tests

### 1. Browser smoke test of /swing-trade page
expected: Log in → visit /swing-trade → 3 tabs render (Sinais da Carteira active by default, Radar Swing, Minhas Operações). "Atualizado em <timestamp>" visible in header. Unauth user gets redirected to /login?redirect=/swing-trade.
result: PASS
notes: Unauth redirect to /login?redirect=%2Fswing-trade confirmed. After login, page loads with title "Swing Trade — InvestIQ", 3 tabs visible (Sinais da Carteira active), "Atualizado em 11/04/2026 22:01" timestamp visible. All 3 tabs navigate correctly. Radar Swing shows "Nenhuma ação com desconto significativo no momento" (no stocks meet BUY criteria — correct behavior). Sinais da Carteira shows "Nenhuma posição na carteira" for test account (correct — no portfolio imported).

### 2. [SEMANTIC] SC1 interpretation — VENDER badge scope
expected: Product owner confirms that VENDER is intentionally scoped to *registered operations* (OperationResponse.live_signal field, triggered when pnl_pct >= 10%), NOT to dividend-portfolio cards on Sinais da Carteira tab.
result: ACCEPTED
decision: accept_narrow
notes: Design is intentional and correct. Portfolio positions use weighted-average cost, not a unique entry price, so per-position SELL signals are not computable. VENDER via live_signal on registered ops is the right UX.

### 3. [SEMANTIC] SC2 interpretation — Radar universe size/criterion
expected: Product owner confirms that the radar uses the curated RADAR_ACOES list (20 IBOV tickers) not a dynamic "top 30 by DY" ranking.
result: ACCEPTED
decision: accept_curated_20
notes: Curated 20-ticker list is acceptable. The BUY filter (DY>=5% + drop<=-12%) still enforces dividend quality. Dynamic top-30-by-DY deferred to future phase if needed.

### 4. End-to-end operation creation flow
expected: Click "+ Nova Operação" → fill form (PETR4, 100, entry 32.50, today, target 37, stop 30, notes "test") → submit. Modal closes, new row appears in "Operações em Aberto" with status ABERTA.
result: PASS
notes: Modal opened with all fields. Form filled (PETR4, qty 100, entry R$32.50, target R$37, stop R$30, notes "UAT test"). After submit: modal closed, PETR4 appeared in "Operações em Aberto" with badge ABERTA, counter changed to "1 em aberto". P&L shows — because test account has no Redis quote for PETR4 — correct fallback behavior.

### 5. Close operation via "Fechar" button
expected: With at least one open operation, click "Fechar". window.prompt appears. Accept with exit price. Row moves to "Operações Fechadas", status FECHADA, pnl_pct computed from entry/exit.
result: PASS
notes: window.prompt intercepted with exit price R$35.50. After close: PETR4 moved to "Operações Fechadas", counter changed to "0 em aberto · 2 fechadas". P&L computed: 9.23% = R$300.00 (100 shares x R$3.00 gain). Client-side P&L calculation confirmed correct. Collapsible section works.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

None. All tests passed. Phase 20 is COMPLETE.
