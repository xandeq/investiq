# Phase 2: Portfolio Engine + Market Data - Context

**Gathered:** 2026-03-14
**Status:** Ready for planning
**Source:** User priorities (direct session input)

<domain>
## Phase Boundary

Phase 2 delivers the core financial engine: transaction recording, CMP-based P&L, corporate event adjustments, and a fully decoupled async market data pipeline (quotes + macro indicators) served from Redis. This is the computational backbone that feeds the dashboard (Phase 3) and AI analysis (Phase 4+).

**Depends on:** Phase 1 (Auth, RLS, schema, CORS — all validated)
**Feeds into:** Phase 3 (dashboard UI), Phase 4+ (AI analysis)

</domain>

<decisions>
## Implementation Decisions

### CMP Engine (Preço Médio Ponderado)
- Use B3/CVM-mandated CMP methodology — NOT FIFO
- Recalculate CMP on every buy transaction: `new_cmp = (qty_held × cmp_prev + qty_bought × price_bought) / (qty_held + qty_bought)`
- On sell: P&L = `(sell_price - cmp) × qty_sold`; CMP does NOT change on sell
- Must handle partial sales correctly — CMP remains unchanged
- Unit tests must verify against B3 official examples
- IR fields (ganho_bruto, imposto_estimado) stored at transaction time — never computed on the fly

### Corporate Events
- Support: desdobramentos (splits), grupamentos (reverse splits), bonificações
- Events must adjust quantity and CMP without distorting historical P&L
- Retroactive application: event recorded at ex-date, positions recalculated from that point
- Verified against B3 official corporate action examples
- No user-facing corporate event UI in Phase 2 — admin/seed data only

### Asset Types (from v1 schema)
- ações (BR equities)
- FIIs (Fundos de Investimento Imobiliário)
- renda fixa (CDB, LCI, LCA, debentures)
- BDRs (Brazilian Depositary Receipts)
- ETFs

### Market Data Pipeline
- brapi.dev for B3 equity quotes — 15-min delay free tier
- python-bcb for macro indicators (SELIC, CDI, IPCA, câmbio)
- yfinance as fallback for historical data
- **Critical**: individual user API requests NEVER call external APIs directly — always served from Redis cache
- Cache-aside pattern: Celery beat refreshes cache, API reads from Redis, falls back to sync fetch only if Redis is empty (cold start)

### Redis + Celery Architecture
- Redis: both message broker (Celery tasks) AND cache store (market data)
- Celery beat: scheduled quote refresh every 15 min during market hours (10h–17h BRT, weekdays)
- Macro indicators: refresh every 6h (slower-moving data)
- Jobs fully decoupled from FastAPI — no blocking external calls in request path
- Workers in separate Docker service (docker-compose)

### API Design
- P&L endpoint: returns per-asset and portfolio-level P&L, using cached CMP + latest Redis quote
- Allocation endpoint: breakdown by asset class (%)
- Benchmark comparison: CDI (python-bcb) and IBOVESPA (brapi.dev) — same Redis cache pattern
- Dividend history endpoint (per asset)
- Fundamental indicators endpoint (P/L, P/VP, DY, EV/EBITDA) — sourced from brapi.dev

### Claude's Discretion
- Exact Redis key naming convention
- Celery task retry/backoff strategy on brapi.dev rate limits
- SQLAlchemy async session handling in Celery tasks (careful: Celery is sync by default)
- Test strategy for async Celery jobs (mock brapi.dev, test Redis writes)
- Error handling when brapi.dev is down (stale data policy — serve last known + timestamp)
- brapi.dev free tier rate limits — implement request throttling

</decisions>

<specifics>
## Specific Ideas

### CMP Test Cases (from B3 docs)
- Buy 100 shares @ R$10 → CMP = R$10
- Buy 50 more @ R$12 → CMP = (100×10 + 50×12) / 150 = R$10.67
- Sell 80 @ R$15 → P&L = (15-10.67)×80 = R$346.40; CMP stays R$10.67
- Desdobramento 1:2 → qty×2, CMP÷2; P&L unchanged

### Tech Already Decided (from STATE.md)
- FastAPI + SQLAlchemy 2.x async + asyncpg
- Celery + Redis (stack locked at init)
- brapi.dev + python-bcb (locked at init)
- PostgreSQL RLS (SET LOCAL for tenant context)
- Docker Compose for local dev

### Portfolio Schema (from Phase 1)
- `transactions` table exists with asset_type, ticker, qty, price, date, IR fields
- Base from auth.models — portfolio imports only Base (plain DeclarativeBase)
- SAEnum stored at ORM level for cross-DB test compatibility

</specifics>

<deferred>
## Deferred Ideas

- Multi-user tenants (Phase 2+ per STATE.md)
- Admin UI for corporate events (seed data only in Phase 2)
- Options/derivatives support
- Real-time WebSocket quotes (Phase 2 is 15-min delay)
- Tax optimization / DARF generation
- AI-powered analysis (Phase 4+)
- Dashboard UI (Phase 3)

</deferred>

---

*Phase: 02-portfolio-engine-market-data*
*Context gathered: 2026-03-14 via user session priorities*
