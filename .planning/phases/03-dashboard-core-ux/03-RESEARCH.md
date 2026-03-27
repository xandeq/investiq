# Phase 3: Dashboard + Core UX — Research

**Researched:** 2026-03-14
**Domain:** Next.js 15 App Router + FastAPI dashboard module + charting (Recharts/lightweight-charts)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Backend — Dashboard Module**
- New module `app/modules/dashboard/` — follow existing pattern: `__init__.py`, `router.py`, `service.py`, `schemas.py`
- Single endpoint: `GET /dashboard/summary`
- Response fields: `net_worth`, `total_invested`, `total_return`, `total_return_pct`, `daily_pnl`, `daily_pnl_pct`, `data_stale`, `asset_allocation` (grouped by class), `portfolio_timeseries`, `recent_transactions` (last 10)
- Optimized: single DB query pass + Redis reads, no N+1 queries
- All monetary values: `Decimal` serialized as string in JSON
- Multi-tenant isolation via `get_authed_db` + RLS — same pattern as portfolio
- `data_stale: true` if any Redis cache miss; never return HTTP 500 on stale

**Frontend — Tech Stack Additions**
- TanStack Query v5 (`@tanstack/react-query`) — locked
- Tremor (`@tremor/react`) for allocation pie chart and metric cards — but verify React 19 compatibility; recharts fallback if incompatible
- TradingView Lightweight Charts (`lightweight-charts`) for portfolio value timeseries
- JWT in httpOnly cookie — frontend never reads token; extend existing `api-client.ts` and `middleware.ts`

**Feature folder structure — locked:**
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

**Dashboard layout — locked:**
- Top row: NetWorthCard (net_worth, total_return, total_return_pct, daily_pnl)
- Second row: AllocationChart (pie by asset_class) + PortfolioChart (area chart timeseries)
- Third row: RecentTransactions table (last 10)
- Mobile-first responsive; single column on mobile, grid on desktop; 375px minimum
- P&L labels: "desde a compra / no mês / no ano" (Brazilian Portuguese)
- Positive P&L = green, negative = red
- Macro indicators (SELIC, CDI, IPCA, PTAX) as metric cards on dashboard

### Claude's Discretion
- Loading states and skeleton UI
- Error boundary strategy for stale data indicator
- Exact color palette within Tailwind + shadcn system
- Whether to use Tremor `<DonutChart>` or `<PieChart>` for allocation
- Pagination vs infinite scroll for transaction history
- Exact breakpoints for responsive grid

### Deferred Ideas (OUT OF SCOPE)
- Detailed per-asset page (Phase 3 shows summary only)
- Transaction add/edit form in dashboard (bonus only)
- PDF/CSV import UI (Phase 5)
- AI analysis panels (Phase 4)
- Premium gating UI (Phase 6)
- Push notifications for dividends (v2)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| VIEW-01 | Usuário vê carteira consolidada com todos os ativos, valor atual e alocação percentual por categoria | GET /dashboard/summary provides `net_worth`, `asset_allocation`; AllocationChart + PositionsTable render this |
| VIEW-02 | Usuário vê P&L por ativo (ganho/perda realizado e não realizado) | `total_return`, `daily_pnl` from summary; PnlTable component from GET /portfolio/pnl positions |
| VIEW-03 | Usuário vê rentabilidade da carteira comparada com CDI e IBOVESPA | `portfolio_timeseries` for area chart; benchmarks from existing GET /portfolio/benchmarks |
| VIEW-04 | Usuário vê histórico de dividendos/proventos recebidos por ativo e por período | GET /portfolio/dividends already exists; DividendHistory component in dashboard or portfolio feature |
</phase_requirements>

---

## Summary

Phase 3 adds a new backend aggregation module plus a complete Next.js frontend. The backend work is straightforward: a new `app/modules/dashboard/` module following the exact same pattern as portfolio — `__init__.py`, `router.py`, `service.py`, `schemas.py` — registered in `main.py` with one line. The `DashboardService` delegates to existing `PortfolioService` and `MarketDataService` methods; it does NOT duplicate logic, it orchestrates a single DB pass over all transactions plus Redis reads for prices.

The critical frontend decision is the chart library. Research confirms that `@tremor/react` is NOT compatible with React 19 without workarounds — it depends on `recharts@2.x` and `@headlessui/react@1.x`, both of which have React 19 peer-dependency conflicts. The correct approach is to use **shadcn/ui's built-in chart components**, which are based on Recharts but handle the peer-dep issues cleanly (shadcn officially declared React 19 compatibility in late 2024). For the portfolio timeseries chart, `lightweight-charts` v5 is the right tool — it requires `'use client'` + `next/dynamic` with `ssr: false` because it is explicitly a browser-only library.

TanStack Query v5 integrates cleanly with Next.js 15 App Router. For this project's architecture — where all data fetching goes through the FastAPI backend with httpOnly cookie auth — the simplest correct pattern is: a `providers.tsx` client component wrapping the app with `QueryClientProvider`, and all queries using `useQuery` (not prefetching in Server Components). This avoids complexity while fully satisfying the requirements. The `apiClient` already uses `credentials: 'include'`, so cookies are forwarded automatically on every query.

**Primary recommendation:** Use shadcn/ui Chart (Recharts-based, React 19 compatible) for the donut allocation chart and area timeseries chart. Use lightweight-charts v5 for historical price charts (DATA-04, not needed in Phase 3 but infrastructure should be ready). Skip Tremor entirely.

---

## Standard Stack

### Core Additions for Phase 3

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `@tanstack/react-query` | ^5.x (latest ~5.67) | Server state, cache, loading/error | Locked decision; React 18+ required (project uses React 19) |
| `recharts` | ^2.15 (pinned, shadcn compat) | Charts via shadcn/ui Chart component | shadcn officially supports this version with React 19 |
| `lightweight-charts` | ^5.1.0 | Portfolio + price timeseries charts | Locked decision; 45KB canvas-based, fastest financial charts |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `@tanstack/react-query-devtools` | ^5.x | Dev-only query inspector | Development only — add to QueryClientProvider boundary |

### What NOT to Install

| Library | Why Not |
|---------|---------|
| `@tremor/react` | Incompatible with React 19 — depends on recharts@2.x (peer dep conflict) and @headlessui/react 1.x. shadcn/ui Chart is the React 19-compatible alternative. |
| `axios` | Not needed — existing `apiClient` uses native fetch with `credentials: 'include'` |
| `date-fns` / `dayjs` | Not needed for Phase 3 — `toLocaleDateString('pt-BR')` is sufficient for date formatting |

### Installation

```bash
# From frontend/ directory
npm install @tanstack/react-query lightweight-charts
npm install --save-dev @tanstack/react-query-devtools

# shadcn chart component (copies component files into your project)
npx shadcn@latest add chart
```

Note: `recharts` is installed as a dependency of the shadcn chart component. Do NOT install it directly — let shadcn manage it to ensure compatible version pinning.

---

## Architecture Patterns

### Backend — New Dashboard Module

The exact same structure as `app/modules/portfolio/`:

```
app/modules/dashboard/
├── __init__.py        (empty)
├── router.py          (single GET /dashboard/summary endpoint)
├── service.py         (DashboardService — delegates to PortfolioService + MarketDataService)
└── schemas.py         (DashboardSummaryResponse and nested schemas)
```

**Registration in main.py** (one line, following existing pattern):

```python
from app.modules.dashboard.router import router as dashboard_router
# ...
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
```

The `_get_redis` dependency function must be replicated in `dashboard/router.py` (or imported from a shared location) so tests can override it independently.

### Backend — DashboardService Design

DashboardService should NOT own any data access logic. It delegates:

```python
class DashboardService:
    async def get_summary(self, db, tenant_id, redis_client) -> DashboardSummaryResponse:
        service = PortfolioService()
        mds = MarketDataService(redis_client)

        # Single DB call: get all transactions (reuse PortfolioService._get_all_transactions)
        # Then in one pass compute: positions, net_worth, daily_pnl, timeseries, recent_txs
        # Redis reads: prices per ticker (parallel), macro once
```

**Key optimization for N+1 prevention:**

`PortfolioService.get_positions()` already loads all transactions in one `SELECT` then groups by ticker in Python. `DashboardService.get_summary()` should call `get_positions()` once and reuse the result for `net_worth`, `daily_pnl`, and `asset_allocation`. Do NOT call `get_positions()` + `get_pnl()` separately — `get_pnl()` calls `get_positions()` internally, causing a double DB round-trip.

**`data_stale` propagation rule:** If `any(pos.current_price_stale for pos in positions)`, set `data_stale: true` in the summary response. Never HTTP 500.

**`portfolio_timeseries` construction:** The most pragmatic approach for v1 is to load all buy transactions ordered by date, then reconstruct point-in-time portfolio values using CMP × quantity snapshots at monthly intervals. This is approximate but correct enough for the trend chart. Implementation: group transactions by month, compute running position values.

### Backend — Decimal Serialization (CONFIRMED)

Pydantic v2 serializes `Decimal` fields as **strings by default** when calling `.model_dump(mode='json')`. FastAPI uses `jsonable_encoder` which calls `model_dump(mode='json')`, so all `Decimal` fields in response schemas are automatically serialized as strings in the JSON response — no additional configuration needed.

The existing schemas already use `Decimal` fields correctly. The new `DashboardSummaryResponse` schema should follow the same pattern.

Verification: existing `PositionResponse` has `cmp: Decimal` and `unrealized_pnl: Decimal | None` — these arrive at the frontend as strings like `"38.50"`. The frontend must parse these with `parseFloat()` or keep them as strings and format with `Intl.NumberFormat`.

### Frontend — Feature Folder Structure

```
src/
├── lib/
│   ├── api-client.ts         (existing — extend only)
│   └── query-client.ts       (NEW — singleton QueryClient factory)
├── providers/
│   └── query-provider.tsx    (NEW — 'use client' QueryClientProvider wrapper)
├── features/
│   ├── auth/                 (existing — do not modify)
│   ├── dashboard/
│   │   ├── api.ts            (NEW — getDashboardSummary() using apiClient)
│   │   ├── hooks/
│   │   │   └── useDashboardSummary.ts   (NEW — useQuery wrapper)
│   │   ├── components/
│   │   │   ├── NetWorthCard.tsx
│   │   │   ├── AllocationChart.tsx      (shadcn Chart + Recharts PieChart)
│   │   │   ├── PortfolioChart.tsx       (shadcn Chart + Recharts AreaChart)
│   │   │   ├── PnlTable.tsx
│   │   │   ├── MacroIndicators.tsx
│   │   │   └── RecentTransactions.tsx
│   │   └── types.ts
│   └── portfolio/
│       ├── api.ts
│       ├── hooks/
│       │   ├── usePositions.ts
│       │   └── usePnl.ts
│       ├── components/
│       │   └── PositionsTable.tsx
│       └── types.ts
└── app/
    ├── layout.tsx             (wrap with QueryProvider)
    ├── dashboard/
    │   └── page.tsx           (Server Component wrapper)
    └── portfolio/
        └── page.tsx
```

### Frontend — QueryClientProvider Setup

`src/providers/query-provider.tsx`:

```typescript
"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";

export function QueryProvider({ children }: { children: React.ReactNode }) {
  // useState ensures one QueryClient per component mount (not recreated per render)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000, // 1 min — avoids immediate refetch on mount
            gcTime: 5 * 60 * 1000, // 5 min default
            retry: 1,
            refetchOnWindowFocus: false, // financial data does not need aggressive refresh
          },
        },
      })
  );
  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && <ReactQueryDevtools />}
    </QueryClientProvider>
  );
}
```

In `src/app/layout.tsx`, wrap `<body>` children with `<QueryProvider>`.

**Why NOT use HydrationBoundary / server prefetching:**
This project uses httpOnly cookies for auth. Server Components in Next.js cannot forward the user's browser cookies to the FastAPI backend without additional infrastructure (forwarding `Cookie` headers from the incoming request to the outgoing fetch). For v1, all data fetching happens client-side in `useQuery` hooks — simpler, correct, and TanStack Query handles caching/loading states. HydrationBoundary is a future optimization.

### Frontend — useDashboardSummary Hook

```typescript
// src/features/dashboard/hooks/useDashboardSummary.ts
"use client";
import { useQuery } from "@tanstack/react-query";
import { getDashboardSummary } from "@/features/dashboard/api";

export function useDashboardSummary() {
  return useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: getDashboardSummary,
    staleTime: 60 * 1000,    // dashboard data fresh for 1 min
    refetchInterval: 5 * 60 * 1000, // auto-refresh every 5 min
  });
}
```

The `getDashboardSummary` function in `api.ts` calls `apiClient<DashboardSummary>("/dashboard/summary")`. The existing `apiClient` already includes `credentials: 'include'` — no changes needed.

### Frontend — Auth and Middleware (NO CHANGES NEEDED)

The existing `middleware.ts` already protects `/dashboard` and `/portfolio` routes by checking the `access_token` cookie presence. No changes are needed for Phase 3.

The `useAuth` hook already exists for client-side UI state (show/hide nav items). The FastAPI backend enforces actual auth on every API call via `get_authed_db`.

### Frontend — lightweight-charts v5 Pattern (SSR-safe)

`lightweight-charts` v5 is explicitly browser-only. The correct pattern for Next.js App Router:

```typescript
// src/features/dashboard/components/PortfolioChart.tsx
"use client";
import { useEffect, useRef } from "react";
import { createChart, AreaSeries } from "lightweight-charts";

export function PortfolioChart({ data }: { data: TimeseriesPoint[] }) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 300,
      layout: { background: { color: "transparent" } },
    });
    const series = chart.addSeries(AreaSeries, {
      lineColor: "#2563eb",
      topColor: "rgba(37, 99, 235, 0.3)",
      bottomColor: "rgba(37, 99, 235, 0)",
    });
    series.setData(
      data.map((p) => ({ time: p.date, value: parseFloat(p.value) }))
    );
    const handleResize = () => {
      chart.applyOptions({ width: containerRef.current?.clientWidth ?? 600 });
    };
    window.addEventListener("resize", handleResize);
    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, [data]);

  return <div ref={containerRef} className="w-full" />;
}
```

**v5 breaking change:** Use `chart.addSeries(AreaSeries, options)` — NOT `chart.addAreaSeries(options)`. Import `AreaSeries` explicitly from `'lightweight-charts'`.

**No `next/dynamic` needed** when the component already has `"use client"` at the top AND `createChart` is inside `useEffect`. The chart code runs only in the browser. If for any reason you need to import `PortfolioChart` from a Server Component, wrap the import: `const PortfolioChart = dynamic(() => import('./PortfolioChart'), { ssr: false })`.

### Frontend — shadcn Chart for Allocation Donut

shadcn/ui Chart components are Recharts wrapped in a theming layer. They are fully compatible with React 19 (shadcn confirmed React 19 support in 2024). Install with `npx shadcn@latest add chart` — this copies `components/ui/chart.tsx` into the project and installs `recharts` as a dependency.

**DO NOT install `@tremor/react`** — it is incompatible with React 19 (depends on recharts@2.x via peer deps that conflict with React 19, and @headlessui/react@1.x which is also incompatible).

Allocation donut example with shadcn:

```typescript
"use client";
import { PieChart, Pie, Cell, Tooltip } from "recharts";
import { ChartContainer, ChartTooltipContent } from "@/components/ui/chart";

const COLORS = {
  acao: "hsl(var(--chart-1))",
  fii: "hsl(var(--chart-2))",
  renda_fixa: "hsl(var(--chart-3))",
  bdr: "hsl(var(--chart-4))",
  etf: "hsl(var(--chart-5))",
};

export function AllocationChart({ allocation }: { allocation: AllocationItem[] }) {
  const chartData = allocation.map((item) => ({
    name: item.asset_class,
    value: parseFloat(item.value),
    fill: COLORS[item.asset_class as keyof typeof COLORS] ?? "#888",
  }));
  const chartConfig = Object.fromEntries(
    allocation.map((item) => [item.asset_class, { label: item.asset_class }])
  );
  return (
    <ChartContainer config={chartConfig} className="h-64 w-full">
      <PieChart>
        <Pie data={chartData} dataKey="value" innerRadius={60} outerRadius={90}>
          {chartData.map((entry, i) => (
            <Cell key={i} fill={entry.fill} />
          ))}
        </Pie>
        <Tooltip content={<ChartTooltipContent />} />
      </PieChart>
    </ChartContainer>
  );
}
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Server state / loading / error | Custom fetch hooks with useState | TanStack Query `useQuery` | Race conditions, stale closures, deduplication, cache invalidation — all solved |
| Chart rendering | Raw SVG or Canvas charts | shadcn Chart (Recharts) / lightweight-charts | Responsive handling, accessibility, tooltip UX, data normalization |
| Decimal string → display | Custom number formatter | `Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })` | Handles thousands separators, decimal commas, currency symbol for Brazilian locale |
| Loading skeletons | Custom pulsing divs | shadcn `Skeleton` component | Already in project, consistent pulse animation |
| Responsive grid | Manual CSS grid media queries | Tailwind responsive prefixes (`sm:`, `lg:`, `xl:`) | Already in project with Tailwind 3.4 |
| Date formatting | Manual date math | `toLocaleDateString('pt-BR')` | Zero-dependency, correct Brazilian locale (dd/mm/yyyy) |
| Portfolio timeseries reconstruction | A complex algorithm from scratch | Accumulate CMP × qty snapshots per month in Python | Simple enough to own; no library does this domain-specific computation |

**Key insight:** The most dangerous hand-roll trap in this phase is writing a custom React data-fetching hook with loading/error state. TanStack Query's `useQuery` eliminates the need for this entirely and provides automatic deduplication (if both `useDashboardSummary` and `useMacroIndicators` run simultaneously, requests are not duplicated).

---

## Common Pitfalls

### Pitfall 1: Tremor + React 19 Peer Dependency Hell

**What goes wrong:** `npm install @tremor/react` succeeds with `--legacy-peer-deps`, but at runtime you get hydration errors or undefined component errors because `@headlessui/react@1.x` does not support React 19.

**Why it happens:** `@tremor/react@3.x` pins `@headlessui/react@^1.7` and `recharts@^2.x`, both incompatible with React 19 peer requirements.

**How to avoid:** Do not install `@tremor/react`. Use shadcn/ui Chart components (Recharts-based, properly peer-dep managed).

**Warning signs:** Any `npm install` that requires `--legacy-peer-deps` or `--force` for a UI component library is a red flag.

### Pitfall 2: lightweight-charts called during SSR

**What goes wrong:** `ReferenceError: window is not defined` or `document is not defined` at build time.

**Why it happens:** `createChart` accesses `document.createElement('canvas')` at import time in some bundler configurations, or the component file is executed during SSR.

**How to avoid:** Always put `createChart` inside `useEffect`. The `"use client"` directive on the component file alone is NOT sufficient if the component is imported in a Server Component tree that renders on the server first. Use `next/dynamic(() => import('./PortfolioChart'), { ssr: false })` as the safe guard when unsure.

**Warning signs:** Build errors mentioning `window` or `document` in the lightweight-charts file path.

### Pitfall 3: N+1 in DashboardService

**What goes wrong:** `DashboardService` calls `PortfolioService.get_pnl()` (which internally calls `get_positions()`) AND ALSO calls `get_positions()` separately — two full DB scans.

**Why it happens:** `get_pnl()` returns a `PnLResponse` that includes `positions`, `allocation`, and `total_portfolio_value`. The developer re-calls `get_positions()` to access positions separately.

**How to avoid:** Call `get_pnl()` once, extract `positions` from the result, and use `pnl_response.positions`, `pnl_response.allocation`, and `pnl_response.total_portfolio_value` directly.

### Pitfall 4: Decimal Strings Parsed Incorrectly on Frontend

**What goes wrong:** `parseFloat("185430.50")` works correctly. But if a future API response uses commas (e.g., from a different locale), it would silently become `NaN`.

**Why it happens:** FastAPI / Pydantic v2 serializes `Decimal` as strings like `"185430.50"` (always dot as decimal separator, no commas). This is safe to `parseFloat()`.

**How to avoid:** Use `parseFloat(value)` for numeric operations, `Intl.NumberFormat('pt-BR')` for display. Never use `Number(value)` on strings with potential commas.

### Pitfall 5: QueryClient Created on Every Render

**What goes wrong:** New `QueryClient` on every render discards cache, causing infinite refetch loops.

**Why it happens:** `const queryClient = new QueryClient()` at module scope or without `useState` in the provider.

**How to avoid:** Use `const [queryClient] = useState(() => new QueryClient(...))` in the provider component — guaranteed one instance per mount.

### Pitfall 6: TanStack Query v5 API Changes from v4

**What goes wrong:** Code copied from v4 tutorials uses `onSuccess`, `onError`, `cacheTime` — these are removed in v5.

**Why it happens:** Most tutorial content online is for v4 (released 2022-2023).

**How to avoid:**
- v5 renames: `cacheTime` → `gcTime`
- v5 removes: `onSuccess`, `onError`, `onSettled` query options (use `useEffect` watching `data`/`error` instead, or `.then()` on `queryClient.prefetchQuery()`)
- v5 changes: single object argument for `useQuery({ queryKey, queryFn })` — no positional overloads

---

## Code Examples

### GET /dashboard/summary — DashboardService skeleton

```python
# Source: based on existing PortfolioService pattern in app/modules/portfolio/service.py
from decimal import Decimal
from sqlalchemy import select
from app.modules.portfolio.service import PortfolioService
from app.modules.market_data.service import MarketDataService
from app.modules.dashboard.schemas import DashboardSummaryResponse, AllocationSummary, TimeseriesPoint, RecentTransaction
from app.modules.portfolio.models import Transaction

class DashboardService:
    async def get_summary(self, db, tenant_id: str, redis_client) -> DashboardSummaryResponse:
        portfolio_svc = PortfolioService()
        mds = MarketDataService(redis_client)

        # Single call — returns positions with prices from Redis
        pnl = await portfolio_svc.get_pnl(db, tenant_id, redis_client)
        positions = pnl.positions

        net_worth = pnl.total_portfolio_value
        total_invested = sum(p.total_cost for p in positions)
        total_return = net_worth - total_invested
        total_return_pct = (total_return / total_invested * Decimal("100")) if total_invested > 0 else Decimal("0")

        data_stale = any(p.current_price_stale for p in positions)

        # Asset allocation (already computed in pnl.allocation)
        asset_allocation = [
            AllocationSummary(
                asset_class=item.asset_class,
                value=item.total_value,
                pct=item.percentage,
            )
            for item in pnl.allocation
        ]

        # Daily P&L: need previous_close per ticker — from Redis QuoteCache
        daily_pnl = Decimal("0")
        for p in positions:
            if p.current_price is not None:
                quote = await mds.get_quote(p.ticker)
                if not quote.data_stale and quote.previous_close:
                    daily_pnl += (quote.price - quote.previous_close) * p.quantity

        # Recent transactions (last 10)
        result = await db.execute(
            select(Transaction)
            .where(Transaction.transaction_type.in_(["buy", "sell"]))
            .order_by(Transaction.transaction_date.desc())
            .limit(10)
        )
        recent_txs = [
            RecentTransaction(
                ticker=tx.ticker,
                type=tx.transaction_type.value,
                quantity=tx.quantity,
                unit_price=tx.unit_price,
                date=tx.transaction_date,
            )
            for tx in result.scalars().all()
        ]

        return DashboardSummaryResponse(
            net_worth=net_worth,
            total_invested=total_invested,
            total_return=total_return,
            total_return_pct=total_return_pct,
            daily_pnl=daily_pnl,
            daily_pnl_pct=(daily_pnl / net_worth * Decimal("100")) if net_worth > 0 else Decimal("0"),
            data_stale=data_stale,
            asset_allocation=asset_allocation,
            portfolio_timeseries=[],  # implemented in Plan 03-02
            recent_transactions=recent_txs,
        )
```

### DashboardSummaryResponse schema

```python
# Source: follows pattern in app/modules/portfolio/schemas.py
from decimal import Decimal
from datetime import date
from pydantic import BaseModel

class AllocationSummary(BaseModel):
    asset_class: str
    value: Decimal
    pct: Decimal

class TimeseriesPoint(BaseModel):
    date: date
    value: Decimal

class RecentTransaction(BaseModel):
    ticker: str
    type: str
    quantity: Decimal
    unit_price: Decimal
    date: date

class DashboardSummaryResponse(BaseModel):
    net_worth: Decimal
    total_invested: Decimal
    total_return: Decimal
    total_return_pct: Decimal
    daily_pnl: Decimal
    daily_pnl_pct: Decimal
    data_stale: bool = False
    asset_allocation: list[AllocationSummary]
    portfolio_timeseries: list[TimeseriesPoint]
    recent_transactions: list[RecentTransaction]
```

All `Decimal` fields are automatically serialized as strings in FastAPI JSON responses via Pydantic v2's default behavior.

### Dashboard API function (frontend)

```typescript
// Source: follows pattern in src/features/auth/api.ts
import { apiClient } from "@/lib/api-client";
import type { DashboardSummary } from "@/features/dashboard/types";

export async function getDashboardSummary(): Promise<DashboardSummary> {
  return apiClient<DashboardSummary>("/dashboard/summary");
}
```

### Brazilian currency formatter

```typescript
// Source: MDN Intl.NumberFormat — zero dependencies
export const formatBRL = (value: string | number): string =>
  new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    minimumFractionDigits: 2,
  }).format(typeof value === "string" ? parseFloat(value) : value);

export const formatPct = (value: string | number): string =>
  `${parseFloat(String(value)).toFixed(2)}%`;
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `@tremor/react` for React dashboards | shadcn/ui Chart (Recharts) | Mid-2024 (React 19 era) | Tremor is no longer viable for React 19 projects |
| `lightweight-charts` v4 `addAreaSeries()` | v5 `addSeries(AreaSeries, opts)` | v5.0 release 2024 | Breaking API change; must import `AreaSeries` explicitly |
| TanStack Query `cacheTime` | `gcTime` (v5 rename) | v5.0 Oct 2023 | Old tutorials show `cacheTime` — does not exist in v5 |
| TanStack Query `onSuccess` callback | `useEffect` watching `data` | v5.0 Oct 2023 | Removed; query-level callbacks gone |
| React Query v4 `useQuery(key, fn, opts)` | `useQuery({ queryKey, queryFn, ...opts })` | v5.0 Oct 2023 | Positional overloads removed |

**Deprecated/outdated:**
- `@tremor/react`: last published a year ago (v3.18.7), not updated for React 19
- `lightweight-charts` `addAreaSeries()`, `addLineSeries()`: removed in v5 — use `addSeries(AreaSeries)` pattern

---

## Open Questions

1. **`previous_close` field in QuoteCache**
   - What we know: `MarketDataService.get_quote()` returns `QuoteCache` with `price`, `change`, `change_pct`, `fetched_at`, `data_stale`
   - What's unclear: Does `QuoteCache` include `previous_close`? The schema is in `app/modules/market_data/schemas.py` (not read during research). `daily_pnl` calculation needs previous close or can derive it from `price - change`.
   - Recommendation: In `DashboardService`, compute `previous_close_price = quote.price - quote.change` (both are in `QuoteCache`). No schema changes needed.

2. **`portfolio_timeseries` implementation complexity**
   - What we know: The API contract requires `{date, value}` points; Phase 2 stores transactions with dates.
   - What's unclear: How far back should the timeseries go? Monthly snapshots suffice for v1 trend visualization.
   - Recommendation: Implement as monthly snapshots from earliest transaction date to today. Load all buy/sell transactions in one query, compute running positions per month using the CMP engine, multiply by current prices (last known). This is an approximation acceptable for v1.

3. **shadcn chart component version in project**
   - What we know: `components.json` is present (shadcn configured). Chart component may or may not already be added.
   - What's unclear: Whether `npx shadcn@latest add chart` has been run.
   - Recommendation: Plan 03-01 should verify and run `npx shadcn@latest add chart` as a setup step.

---

## Validation Architecture

> `workflow.nyquist_validation` is `true` in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (existing, confirmed in conftest.py) |
| Config file | `backend/pytest.ini` or `pyproject.toml` (check existing) |
| Quick run command | `cd backend && pytest tests/test_dashboard_api.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| VIEW-01 | GET /dashboard/summary returns net_worth + asset_allocation | Integration | `pytest tests/test_dashboard_api.py::test_dashboard_summary_returns_allocation -x` | ❌ Wave 0 |
| VIEW-01 | asset_allocation grouped by asset_class (no raw tickers) | Integration | `pytest tests/test_dashboard_api.py::test_allocation_grouped_by_class -x` | ❌ Wave 0 |
| VIEW-02 | total_return and daily_pnl present and computed | Integration | `pytest tests/test_dashboard_api.py::test_pnl_fields_present -x` | ❌ Wave 0 |
| VIEW-02 | data_stale=true when Redis cache empty | Integration | `pytest tests/test_dashboard_api.py::test_data_stale_on_cache_miss -x` | ❌ Wave 0 |
| VIEW-03 | portfolio_timeseries returns non-empty list for user with transactions | Integration | `pytest tests/test_dashboard_api.py::test_timeseries_nonempty -x` | ❌ Wave 0 |
| VIEW-03 | benchmarks endpoint returns CDI + IBOVESPA (already exists) | Integration | `pytest tests/test_portfolio_api.py::test_benchmarks -x` | ✅ |
| VIEW-04 | GET /portfolio/dividends returns dividend transactions | Integration | `pytest tests/test_portfolio_api.py::test_get_dividends -x` | ✅ |
| VIEW-01-04 | 401 returned when no auth cookie present | Integration | `pytest tests/test_dashboard_api.py::test_dashboard_requires_auth -x` | ❌ Wave 0 |
| DashboardService schema | Decimal fields serialize as strings in JSON | Unit | `pytest tests/test_dashboard_schemas.py -x` | ❌ Wave 0 |

### What Can Be Unit Tested (Backend)

- `DashboardService.get_summary()` — pure computation logic with fakeredis + SQLite (same pattern as existing portfolio tests)
- `DashboardSummaryResponse` schema — Pydantic validation, Decimal serialization via `model_dump(mode='json')`
- `portfolio_timeseries` construction function — pure function, no DB needed, can take list of transaction dicts

### What Requires Integration Tests (Backend)

- `GET /dashboard/summary` — full stack: auth cookie → FastAPI → DashboardService → PortfolioService → MarketDataService → response validation
- Auth enforcement — 401 when cookie missing, 200 when valid
- RLS tenant isolation — user A cannot see user B's data (same pattern as `test_rls.py`)

### What Requires E2E / Visual Testing (Frontend)

- AllocationChart renders without crashing — requires browser/jsdom with canvas mock
- PortfolioChart (lightweight-charts) renders without crashing — requires canvas mock or visual regression tool
- Responsive layout at 375px — manual or Playwright screenshot test

**Recommended E2E approach for Phase 3:** Playwright for smoke tests on the dashboard page. Not required for Phase 3 completion — backend integration tests gate the phase. Frontend component tests with Vitest + React Testing Library are recommended but not blocking.

### Frontend Test Strategy (if added)

For TanStack Query components in Vitest:

```typescript
// Pattern: wrap component in QueryClientProvider with test client
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}
```

Mock `apiClient` at the module level with `vi.mock('@/lib/api-client')`.

### Sampling Rate

- **Per task commit:** `cd backend && pytest tests/test_dashboard_api.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q`
- **Phase gate:** Full backend suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `backend/tests/test_dashboard_api.py` — covers VIEW-01, VIEW-02, VIEW-03 (dashboard endpoint integration tests)
- [ ] `backend/tests/test_dashboard_schemas.py` — covers Decimal string serialization, schema validation
- [ ] Frontend test infrastructure (`frontend/vitest.config.ts`, `frontend/src/test/setup.ts`) — covers component smoke tests (optional for Phase 3)

---

## Sources

### Primary (HIGH confidence)
- Official lightweight-charts migration docs: https://tradingview.github.io/lightweight-charts/docs/migrations/from-v4-to-v5 — v5 breaking changes, new addSeries API
- Official lightweight-charts React tutorial: https://tradingview.github.io/lightweight-charts/tutorials/react/simple — useRef + useEffect pattern, cleanup
- shadcn/ui Chart docs: https://ui.shadcn.com/docs/components/chart — Recharts-based chart component, React 19 compatible
- shadcn/ui React 19 docs: https://ui.shadcn.com/docs/react-19 — confirmed React 19 compatibility
- TanStack Query SSR guide: https://tanstack.com/query/v5/docs/react/guides/ssr — HydrationBoundary, server prefetch patterns
- TanStack Query advanced SSR: https://tanstack.com/query/v5/docs/react/guides/advanced-ssr — Next.js App Router integration

### Secondary (MEDIUM confidence)
- Pydantic v2 Decimal serialization behavior: https://github.com/pydantic/pydantic/issues/7457 — confirmed Decimal serialized as string by default in JSON mode
- @tremor/react React 19 issue: https://github.com/tremorlabs/tremor-npm/issues/1072 — confirmed incompatibility, no fix released in v3.18.7
- shadcn Twitter announcement: https://x.com/shadcn/status/1852989121519816740 — "shadcn/ui is now fully compatible with React 19"

### Tertiary (LOW confidence)
- WebSearch synthesis for lightweight-charts SSR pattern — consistent across multiple sources, aligns with official docs
- WebSearch synthesis for TanStack Query v5 providers.tsx setup — aligns with official documentation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — library versions verified via npm/GitHub, React 19 compat verified via official sources
- Architecture patterns: HIGH — based on reading actual project source (main.py, router.py, service.py, schemas.py, conftest.py)
- Pitfalls: HIGH — Tremor incompatibility and lightweight-charts SSR issue verified via GitHub issues + official docs
- Frontend TQ integration: HIGH — official TanStack Query docs + confirmed API changes v4→v5

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (30 days — stable ecosystem, no fast-moving parts except shadcn minor updates)
