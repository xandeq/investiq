---
status: partial
phase: 20-swing-trade-page
source: [20-VERIFICATION.md]
started: 2026-04-11T00:00:00Z
updated: 2026-04-11T00:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Browser smoke test of /swing-trade page
expected: Log in → visit /swing-trade → 3 tabs render (Sinais da Carteira active by default, Radar Swing, Minhas Operações). "Atualizado em <timestamp>" visible in header. Unauth user gets redirected to /login?redirect=/swing-trade.
result: [pending]

### 2. [SEMANTIC] SC1 interpretation — VENDER badge scope
expected: Product owner confirms that VENDER is intentionally scoped to *registered operations* (OperationResponse.live_signal field, triggered when pnl_pct >= 10%), NOT to dividend-portfolio cards on Sinais da Carteira tab. Rationale: portfolio positions use weighted-average cost, not an entry price, so SELL cannot be computed per-position. Plan 20-01 task 20-01-04 explicitly made this decision.
result: [pending]
decision_required: accept_narrow | require_portfolio_sell_signal

### 3. [SEMANTIC] SC2 interpretation — Radar universe size/criterion
expected: Product owner confirms that the radar uses the curated RADAR_ACOES list (20 IBOV tickers selected by cap/sector in backend/app/modules/opportunity_detector/radar.py) unioned with user holdings, filtered to non-portfolio rows, sorted by discount, BUY-highlighted when DY>=5% and drop<=-12%. NOT a dynamic "top 30 by DY" ranking. Directionally correct but literally smaller and selected differently.
result: [pending]
decision_required: accept_curated_20 | require_top_30_dy_ranking

### 4. End-to-end operation creation flow
expected: Click "+ Nova Operação" → fill form (PETR4, 100, entry 32.50, today, target 37, stop 30, notes "test") → submit. Modal closes, new row appears in "Operações em Aberto" with status ABERTA. Preço Atual / P&L % / P&L R$ / Dias / Target progress bar populated from Redis quote.
result: [pending]

### 5. Close operation via "Fechar" button
expected: With at least one open operation, click "Fechar". window.prompt appears pre-filled with current_price. Accept. Row moves to "Operações Fechadas" (collapsible), status FECHADA, pnl_pct computed client-side from entry/exit.
result: [pending]

## Summary

total: 5
passed: 0
issues: 0
pending: 5
skipped: 0
blocked: 0

## Gaps
