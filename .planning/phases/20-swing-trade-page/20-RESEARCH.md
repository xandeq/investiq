# Phase 20: Swing Trade Page — Research

## Key Findings

### 1. Redis Data Available (No New APIs Needed)
- `market:quote:{TICKER}` → QuoteCache{symbol, price, change, change_pct, fetched_at}
- `market:historical:{TICKER}` → HistoricalCache{ticker, points[]{date(epoch), open, high, low, close, volume}}
- `market:fundamentals:{TICKER}` → FundamentalsCache{ticker, pl, pvp, dy, ev_ebitda}
- Historical points have Unix epoch dates — filter last 30d by comparing timestamps

### 2. Portfolio Positions Access
- `GET /portfolio/positions` → list[PositionResponse] with ticker, quantity, asset_class, cmp, current_price
- Service: `PortfolioService.get_positions(db, tenant_id, redis_client)` — uses get_authed_db (RLS)
- Groups buy/sell transactions, applies CMP engine, enriches with Redis quote

### 3. Alembic Migration Chain
- Latest head: `0022_add_detected_opportunities.py`
- New migration: `0023_add_swing_trade_operations.py`

### 4. Router Registration Pattern (main.py)
```python
from app.modules.swing_trade.router import router as swing_trade_router
app.include_router(swing_trade_router, prefix="/swing-trade", tags=["swing-trade"])
```

### 5. Model Pattern (from DetectedOpportunity)
- UUID string PK, Base from app.modules.auth.models
- mapped_column with String/Numeric/DateTime/Boolean/Text types
- Swing trade IS tenant-scoped (unlike DetectedOpportunity which is global)

### 6. PROTECTED_PATHS (frontend/middleware.ts)
- Array on line 5: `["/dashboard", "/portfolio", "/analysis", "/stock", "/fii", "/opportunity-detector"]`
- Add `"/swing-trade"` to this array

### 7. Frontend Feature Structure (from opportunity_detector)
```
src/features/swing_trade/
  api.ts          — fetch functions
  types.ts        — TypeScript interfaces
  hooks/          — React hooks (useSwingSignals, useSwingOperations)
  components/     — UI components (SignalsCard, RadarTable, OperationsTable)
```
Page at: `src/app/swing-trade/page.tsx`

### 8. Radar Stock Lists (reuse from radar.py)
- RADAR_ACOES: 20 top IBOV stocks with sectors
- RADAR_FIIS: 12 FIIs with segments
- Can import these lists directly for swing trade signals

### 9. Signal Computation Logic
- 30d high: max(point.high for point in historical.points if point.date >= 30d_ago)
- Discount: (current_price - high_30d) / high_30d * 100
- BUY: discount < -12% AND dy > 5% (dividend-focused filter)
- SELL: for open operations, current_price > entry_price * 1.10
- STOP: current_price < stop_price

### 10. Auth Pattern for Tenant-Scoped Data
- Use `get_authed_db` (sets RLS tenant) + `get_current_tenant_id`
- Same pattern as portfolio/router.py
- Redis client via dependency injection: `_get_redis()` function
