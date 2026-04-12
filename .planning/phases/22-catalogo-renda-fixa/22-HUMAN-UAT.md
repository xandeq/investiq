---
status: partial
phase: 22-catalogo-renda-fixa
source: [22-VERIFICATION.md]
started: 2026-04-12T19:37:45Z
updated: 2026-04-12T19:37:45Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. Filter bar visual layout and interactivity
expected: Filter bar above catalog with 5 type buttons (Todos, Tesouro, CDB, LCI, LCA), prazo mínimo input, 4 prazo sort buttons (6m, 1a, 2a, 5a). Clicking "CDB" hides Tesouro section, shows only CDB rows. Prazo sort button re-sorts table by net_pct for that period. Active button highlighted blue/indigo.
result: [pending]

### 2. Beat indicator colors at runtime
expected: With Redis populated (CDI/IPCA in cache), LCI/LCA rows with higher rates show green "✓ CDI", lower CDB rows show amber "~ IPCA" or gray "— abaixo". No flash of wrong colors before macroRates loads.
result: [pending]

### 3. LCI/LCA "Isento" badge unchanged
expected: "Isento" text in green in IR column for all prazo cells of LCI/LCA rows. No IR percentage shown.
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
