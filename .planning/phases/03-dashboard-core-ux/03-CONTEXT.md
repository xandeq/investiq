# Phase 3: Dashboard + Core UX — Context

**Gathered:** 2026-03-14
**Status:** Ready for planning
**Source:** PRD Express Path (user spec + roadmap)

<domain>
## Phase Boundary

Phase 3 delivers the complete user-facing frontend: carteira consolidada, P&L por ativo, rentabilidade vs benchmark, histórico de dividendos, and macro indicators. Accessible on mobile and desktop.

**What this phase builds:**
- Backend: `app/modules/dashboard/` — new module with `GET /dashboard/summary` aggregation endpoint
- Frontend: `src/features/dashboard/` + `src/features/portfolio/` — complete dashboard and portfolio views
- Install missing frontend deps: TanStack Query, chart library (Tremor or lightweight-charts)

**What this phase does NOT build:**
- AI analysis (Phase 4)
- Import / broker integration (Phase 5)
- Monetization / plan gates (Phase 6)
- Backend for transactions CRUD (already done in Phase 2)

</domain>

<decisions>
## Implementation Decisions

### Backend — Dashboard Module

**Locked: New module `app/modules/dashboard/`**
- Follow existing module pattern: `__init__.py`, `router.py`, `service.py`, `schemas.py`
- Single endpoint: `GET /dashboard/summary`
- Response must include all fields below — no frontend assembly of data from multiple calls:
  - `net_worth` — total portfolio value (positions × current prices from Redis)
  - `total_invested` — sum of total_cost across all positions
  - `total_return` — net_worth - total_invested (absolute)
  - `total_return_pct` — total_return / total_invested × 100
  - `daily_pnl` — unrealized daily change (current price vs previousClose) × qty per position, summed
  - `asset_allocation` — list of {asset_class, value, pct} — no raw tickers, grouped by class
  - `portfolio_timeseries` — list of {date, value} for portfolio chart (use available transaction history to reconstruct)
  - `recent_transactions` — last 10 transactions (ticker, type, qty, price, date)
- Endpoint must be optimized: single DB query pass + Redis reads, no N+1 queries
- All monetary values must use `Decimal` — serialized as string in JSON to avoid float precision loss

**Locked: Multi-tenant isolation**
- Dashboard endpoint uses `get_authed_db` (same pattern as portfolio endpoints)
- All queries scoped to current tenant_id via RLS — no cross-tenant data leakage possible
- No business logic allowed in frontend — frontend receives pre-computed values

**Locked: data_stale flag propagation**
- If Redis cache is empty for any ticker, return `data_stale: true` at the summary level
- Never return HTTP 500 on stale cache — always return valid response with stale flag

### Frontend — Tech Stack Additions

**Locked: TanStack Query v5** for server state management
- Already decided in ROADMAP — install `@tanstack/react-query`
- All API calls via TanStack Query (not raw fetch in components)
- Query keys: `['dashboard', 'summary']`, `['portfolio', 'positions']`, etc.

**Locked: Chart library**
- Tremor (`@tremor/react`) for allocation pie chart and simple metric cards
- TradingView Lightweight Charts (`lightweight-charts`) for portfolio value timeseries and historical price charts
- Verify React 19 compatibility during research — if incompatible, use recharts as fallback for pie

**Locked: Auth integration pattern**
- JWT is in httpOnly cookie (set by backend) — frontend never reads the token
- API client already exists at `src/lib/api-client.ts` — extend it, don't replace
- Middleware at `middleware.ts` already exists — extend for route protection

**Locked: Feature folder structure**
```
src/features/dashboard/
  components/    (NetWorthCard, AllocationChart, PnlTable, PortfolioChart, RecentTransactions)
  hooks/         (useDashboardSummary)
  types.ts

src/features/portfolio/
  components/    (PositionsTable, TransactionForm)
  hooks/         (usePositions, usePnl)
  types.ts
```

### Frontend — Dashboard View

**Locked: Dashboard layout**
- Top row: NetWorthCard (net_worth, total_return, total_return_pct, daily_pnl)
- Second row: AllocationChart (pie, by asset_class) + PortfolioChart (area chart, timeseries)
- Third row: RecentTransactions table (last 10)

**Locked: Mobile-first responsive**
- Single column on mobile, grid on desktop
- All cards must be readable on 375px viewport

**Locked: P&L labeling**
- Labels must use: "desde a compra / no mês / no ano" (Brazilian Portuguese)
- Positive P&L = green, negative = red (explicit color coding)

**Locked: Macro indicators display**
- SELIC, CDI, IPCA, PTAX from `/market-data/macro` endpoint
- Shown as metric cards in dashboard (not a separate page for v1)

### Claude's Discretion

- Loading states and skeleton UI — implement as you see fit
- Error boundary strategy for stale data indicator
- Exact color palette within Tailwind + shadcn system
- Whether to use Tremor `<DonutChart>` or `<PieChart>` for allocation
- Pagination vs infinite scroll for transaction history
- Exact breakpoints for responsive grid

</decisions>

<specifics>

## API Contract — GET /dashboard/summary

```json
{
  "net_worth": "185430.50",
  "total_invested": "162000.00",
  "total_return": "23430.50",
  "total_return_pct": "14.46",
  "daily_pnl": "1250.30",
  "daily_pnl_pct": "0.68",
  "data_stale": false,
  "asset_allocation": [
    {"asset_class": "acao", "value": "120000.00", "pct": "64.72"},
    {"asset_class": "fii", "value": "45000.00", "pct": "24.27"},
    {"asset_class": "renda_fixa", "value": "20430.50", "pct": "11.01"}
  ],
  "portfolio_timeseries": [
    {"date": "2026-01-01", "value": "155000.00"},
    {"date": "2026-02-01", "value": "168000.00"},
    {"date": "2026-03-14", "value": "185430.50"}
  ],
  "recent_transactions": [
    {"ticker": "VALE3", "type": "buy", "quantity": 100, "unit_price": "65.50", "date": "2026-03-14"},
    {"ticker": "KNRI11", "type": "buy", "quantity": 50, "unit_price": "120.00", "date": "2026-03-13"}
  ]
}
```

## Existing Backend Endpoints (Phase 2, already working)

- `GET /portfolio/positions` — positions with CMP + Redis price enrichment
- `GET /portfolio/pnl` — realized + unrealized P&L, allocation by asset class
- `GET /portfolio/benchmarks` — CDI + IBOVESPA from Redis
- `GET /portfolio/dividends` — dividend/JSCP history
- `GET /market-data/macro` — SELIC, CDI, IPCA, PTAX
- `GET /market-data/fundamentals/{ticker}` — P/L, P/VP, DY
- `GET /market-data/historical/{ticker}` — 1-year OHLCV

## Existing Frontend (Phase 1, already working)

- `src/features/auth/` — login, register, password reset (complete)
- `src/lib/api-client.ts` — base API client with cookie-based auth
- `middleware.ts` — auth middleware (protect routes)
- shadcn/ui primitives already configured (`components.json` present)
- Tailwind 3.4.17 (locked — shadcn incompatible with Tailwind 4)

</specifics>

<deferred>

## Deferred Ideas

- Detailed per-asset page (click on VALE3 → see full history + fundamentals) — Phase 3 shows summary only
- Transaction add/edit form in dashboard — POST /portfolio/transactions exists but form UX is Phase 3 bonus
- PDF/CSV import UI — Phase 5
- AI analysis panels — Phase 4
- Premium gating UI — Phase 6
- Push notifications for dividends — v2

</deferred>

---

*Phase: 03-dashboard-core-ux*
*Context gathered: 2026-03-14 via PRD Express Path*
