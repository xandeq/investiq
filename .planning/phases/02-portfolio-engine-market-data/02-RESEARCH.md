# Phase 2: Portfolio Engine + Market Data - Research

**Researched:** 2026-03-14
**Domain:** CMP calculation engine, Celery + Redis market data pipeline, brapi.dev + python-bcb integration, FastAPI portfolio API
**Confidence:** HIGH (core stack), MEDIUM (brapi.dev pricing details, python-bcb PTAX edge cases)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**CMP Engine (Preço Médio Ponderado)**
- Use B3/CVM-mandated CMP methodology — NOT FIFO
- Recalculate CMP on every buy transaction: `new_cmp = (qty_held × cmp_prev + qty_bought × price_bought) / (qty_held + qty_bought)`
- On sell: P&L = `(sell_price - cmp) × qty_sold`; CMP does NOT change on sell
- Must handle partial sales correctly — CMP remains unchanged
- Unit tests must verify against B3 official examples
- IR fields (ganho_bruto, imposto_estimado) stored at transaction time — never computed on the fly

**Corporate Events**
- Support: desdobramentos (splits), grupamentos (reverse splits), bonificações
- Events must adjust quantity and CMP without distorting historical P&L
- Retroactive application: event recorded at ex-date, positions recalculated from that point
- Verified against B3 official corporate action examples
- No user-facing corporate event UI in Phase 2 — admin/seed data only

**Asset Types (from v1 schema)**
- ações (BR equities), FIIs, renda fixa (CDB, LCI, LCA, debentures), BDRs, ETFs

**Market Data Pipeline**
- brapi.dev for B3 equity quotes — 15-min delay free/startup tier
- python-bcb for macro indicators (SELIC, CDI, IPCA, câmbio)
- yfinance as fallback for historical data
- Critical: individual user API requests NEVER call external APIs directly — always served from Redis cache
- Cache-aside pattern: Celery beat refreshes cache, API reads from Redis, falls back to sync fetch only if Redis is empty (cold start)

**Redis + Celery Architecture**
- Redis: both message broker (Celery tasks) AND cache store (market data)
- Celery beat: scheduled quote refresh every 15 min during market hours (10h–17h BRT, weekdays)
- Macro indicators: refresh every 6h (slower-moving data)
- Workers in separate Docker service (docker-compose)

**API Design**
- P&L endpoint: per-asset and portfolio-level P&L, using cached CMP + latest Redis quote
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

### Deferred Ideas (OUT OF SCOPE)
- Multi-user tenants (Phase 2+ per STATE.md)
- Admin UI for corporate events (seed data only in Phase 2)
- Options/derivatives support
- Real-time WebSocket quotes (Phase 2 is 15-min delay)
- Tax optimization / DARF generation
- AI-powered analysis (Phase 4+)
- Dashboard UI (Phase 3)
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| PORT-01 | User can register buy/sell transactions for acoes B3 (date, qty, price) | Transaction model exists from Phase 1; needs router + CMP service wiring |
| PORT-02 | User can register FII transactions (with monthly exempt dividends support) | is_exempt field exists on Transaction model; dividend transaction_type already defined |
| PORT-03 | User can register renda fixa manually (CDB, LCI, LCA, Tesouro — maturity, coupon rate) | coupon_rate + maturity_date nullable columns exist; needs input validation |
| PORT-04 | User can register BDRs and ETFs available on B3 | asset_class enum covers BDR and ETF; same CRUD as PORT-01 |
| PORT-05 | System calculates preço médio ajustado including corporate event adjustments | CMP formula documented; corporate_actions table exists; recalculation strategy documented |
| PORT-06 | System records and applies corporate events (splits, reverse splits) without distorting P&L | corporate_actions table exists; apply-events-to-positions algorithm documented |
| DATA-01 | System updates cotações automatically (B3, 15-min delay via brapi.dev) with Redis cache | brapi.dev API documented; Celery beat + Redis cache-aside pattern documented |
| DATA-02 | User sees macro indicators in real time (SELIC, CDI, IPCA, câmbio via python-bcb) | python-bcb SGS codes documented (CDI=12, SELIC=11, IPCA=433); PTAX for câmbio |
| DATA-03 | User sees fundamental indicators per asset (P/L, P/VP, DY, EV/EBITDA) | brapi.dev fundamentals endpoint with modules=defaultKeyStatistics,financialData documented |
| DATA-04 | User sees historical price chart for asset (TradingView Lightweight Charts) | brapi.dev /api/quote/{ticker}?range=1y&interval=1d returns OHLCV array; frontend in Phase 3 |
</phase_requirements>

---

## Summary

Phase 2 has two logically independent domains that must be built in sequence. The **market data pipeline** (Celery + Redis + brapi.dev + python-bcb) is infrastructure that must exist before the portfolio API can serve real prices. The **CMP engine** is pure financial calculation logic that can be built and unit-tested independently, then wired to live prices last.

The deepest technical complexity in this phase is the **Celery-SQLAlchemy async mismatch**. The FastAPI application uses `asyncpg` (async-only driver). Celery workers are synchronous by default and cannot use the async engine directly. The correct solution is a **dedicated sync engine** (`psycopg2`) in the Celery worker process, created after the worker forks (not at import time), isolated from the FastAPI async pool. This is a well-known pattern with documented pitfalls.

The brapi.dev **Startup plan** (R$59.99/mo) is the minimum tier needed for 15-min delay data and fundamentals. The free tier has 30-min delay and 15,000 req/month — insufficient for production but usable for development with the 4 free test tickers. The brapi.dev token is a secret that must be fetched from AWS Secrets Manager at startup.

**Primary recommendation:** Build in plan order: 02-01 (Celery+Redis infrastructure) → 02-02 (market data service with Redis cache-aside) → 02-03 (CMP engine, fully unit-testable) → 02-04 (portfolio API that assembles all pieces). Never let the portfolio API call external APIs synchronously in the request path.

---

## Standard Stack

### Core (New in Phase 2)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| celery | 5.4.0 (already installed) | Task queue + beat scheduler | Already in requirements.txt; locked by project |
| redis | 5.2.1 (already installed) | Broker + cache store | Already in requirements.txt; locked by project |
| python-bcb | latest (0.3.x) | BCB macro data (SELIC/CDI/IPCA/câmbio) | Locked by project; official BCB OData/SGS API wrapper |
| yfinance | 0.2.x | Historical price fallback | Locked by project; Yahoo Finance provider for B3 tickers with .SA suffix |
| httpx | 0.27.2 (already installed) | brapi.dev HTTP calls from Celery | Already in requirements.txt; async-capable |
| psycopg2-binary | 2.9.x | Sync PostgreSQL driver for Celery workers | Celery is sync; cannot use asyncpg; separate sync driver required |
| fakeredis | 2.x | Redis mock for unit tests | Supports async and sync API; no real Redis needed in CI |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pandas | 2.x | python-bcb return format (DataFrames) | Required to parse BCB SGS responses |
| requests | 2.x | Sync HTTP in Celery tasks | Celery tasks are sync; requests is simpler than httpx sync API for Celery context |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| psycopg2-binary (sync) | asyncio.run() inside Celery task | asyncio.run() creates a new event loop each call, breaks SQLAlchemy session pool isolation — do not use |
| fakeredis | pytest-redis (real Redis in Docker) | fakeredis is faster and requires no Docker; adequate for unit tests |
| python-bcb pandas output | direct BCB OData HTTP calls | python-bcb handles OData pagination and authentication; not worth re-implementing |
| Celery beat (in-process) | Separate celery-beat service | Beat should run as a separate Docker service to avoid duplicate task scheduling when scaling workers |

### Installation (additions to existing requirements.txt)
```bash
pip install python-bcb yfinance psycopg2-binary fakeredis pandas
```

Docker Compose worker service addition:
```yaml
celery-worker:
  build: ./backend
  depends_on: [redis, postgres]
  environment: *backend-env   # same env vars as backend
  command: celery -A app.celery_app worker --loglevel=info --concurrency=2

celery-beat:
  build: ./backend
  depends_on: [redis]
  command: celery -A app.celery_app beat --loglevel=info
```

---

## Architecture Patterns

### Recommended Project Structure (Phase 2 additions)

```
backend/
├── app/
│   ├── celery_app.py            # Celery app factory, beat_schedule, worker signals
│   ├── core/
│   │   ├── db.py                # (existing) async engine + get_tenant_db
│   │   └── db_sync.py           # NEW: sync engine for Celery workers (psycopg2)
│   └── modules/
│       ├── portfolio/
│       │   ├── models.py        # (existing) Transaction + CorporateAction
│       │   ├── schemas.py       # (existing skeleton) + expand for P&L responses
│       │   ├── router.py        # NEW: CRUD + P&L + allocation endpoints
│       │   ├── service.py       # REPLACE skeleton: CMP engine + position calculator
│       │   └── cmp.py           # NEW: pure CMP calculation functions (no DB, testable)
│       └── market_data/
│           ├── __init__.py
│           ├── router.py        # NEW: /market-data/quotes, /macro, /fundamentals
│           ├── schemas.py       # NEW: QuoteResponse, MacroResponse, FundamentalsResponse
│           ├── service.py       # NEW: Redis read layer (never calls external APIs)
│           ├── tasks.py         # NEW: Celery tasks (brapi.dev fetch, bcb fetch)
│           └── adapters/
│               ├── brapi.py     # NEW: brapi.dev HTTP client wrapper
│               ├── bcb.py       # NEW: python-bcb wrapper (sync, for Celery)
│               └── yfinance.py  # NEW: yfinance fallback wrapper
tests/
├── test_cmp.py                  # Pure unit tests — no DB, no Redis
├── test_portfolio_api.py        # API integration tests — SQLite + fakeredis
├── test_market_data_tasks.py    # Celery task tests — mock brapi.dev, fakeredis
└── test_portfolio_positions.py  # Position calculation with corporate events
```

### Pattern 1: CMP Engine (Pure Calculation Layer)

**What:** CMP is calculated in `app/modules/portfolio/cmp.py` as pure functions with no framework dependencies. The service layer loads transactions from the DB and passes them to these functions.

**When to use:** Every buy transaction triggers CMP recalculation for that ticker. Sell transactions use the current CMP without changing it. Corporate events modify CMP and quantity before P&L is applied.

```python
# app/modules/portfolio/cmp.py
# Source: B3/CVM methodology — pure functions, no DB or Redis coupling
from decimal import Decimal
from dataclasses import dataclass

@dataclass
class Position:
    ticker: str
    quantity: Decimal
    cmp: Decimal       # preço médio ponderado
    total_cost: Decimal  # quantity × cmp (for verification)

def apply_buy(pos: Position, qty_bought: Decimal, price: Decimal) -> Position:
    """Recalculate CMP after a purchase. CMP formula: B3 methodology."""
    new_qty = pos.quantity + qty_bought
    new_cmp = (pos.quantity * pos.cmp + qty_bought * price) / new_qty
    return Position(
        ticker=pos.ticker,
        quantity=new_qty,
        cmp=new_cmp,
        total_cost=new_qty * new_cmp,
    )

def apply_sell(pos: Position, qty_sold: Decimal, sell_price: Decimal) -> tuple[Position, Decimal]:
    """Apply sell. CMP unchanged. Returns (updated_position, realized_pnl)."""
    realized_pnl = (sell_price - pos.cmp) * qty_sold
    new_qty = pos.quantity - qty_sold
    return (
        Position(pos.ticker, new_qty, pos.cmp, new_qty * pos.cmp),
        realized_pnl,
    )

def apply_desdobramento(pos: Position, factor: Decimal) -> Position:
    """Split: qty × factor, cmp ÷ factor. Total cost unchanged."""
    return Position(
        ticker=pos.ticker,
        quantity=pos.quantity * factor,
        cmp=pos.cmp / factor,
        total_cost=pos.total_cost,  # unchanged
    )

def apply_grupamento(pos: Position, factor: Decimal) -> Position:
    """Reverse split: qty ÷ factor, cmp × factor. Total cost unchanged."""
    return Position(
        ticker=pos.ticker,
        quantity=pos.quantity / factor,
        cmp=pos.cmp * factor,
        total_cost=pos.total_cost,  # unchanged
    )

def apply_bonificacao(pos: Position, factor: Decimal, bonus_price: Decimal) -> Position:
    """Bonus shares: add qty, recalculate CMP with bonus shares at bonus_price."""
    bonus_qty = pos.quantity * factor
    new_qty = pos.quantity + bonus_qty
    new_cmp = (pos.quantity * pos.cmp + bonus_qty * bonus_price) / new_qty
    return Position(pos.ticker, new_qty, new_cmp, new_qty * new_cmp)
```

### Pattern 2: Redis Cache Keys Convention

**What:** Consistent key naming prevents collisions and makes cache inspection easy.

```python
# Convention (Claude's discretion — prescriptive choice):
QUOTE_KEY        = "market:quote:{ticker}"           # e.g. market:quote:PETR4
QUOTE_BATCH_KEY  = "market:quotes:batch:{date}"      # e.g. market:quotes:batch:2026-03-14
MACRO_KEY        = "market:macro:{indicator}"        # e.g. market:macro:CDI
IBOV_KEY         = "market:quote:^BVSP"              # IBOVESPA via brapi.dev index
FUNDAMENTALS_KEY = "market:fundamentals:{ticker}"    # e.g. market:fundamentals:PETR4

TTL_QUOTE        = 60 * 20     # 20 min (slightly more than 15-min refresh)
TTL_MACRO        = 60 * 60 * 7 # 7 hours (refresh every 6h, buffer included)
TTL_FUNDAMENTALS = 60 * 60 * 24  # 24 hours (fundamentals don't change intraday)

# Redis value format: JSON string (no pickle — safer for Redis inspection)
import json, redis

def set_quote(r: redis.Redis, ticker: str, data: dict) -> None:
    r.setex(QUOTE_KEY.format(ticker=ticker), TTL_QUOTE, json.dumps(data))

def get_quote(r: redis.Redis, ticker: str) -> dict | None:
    raw = r.get(QUOTE_KEY.format(ticker=ticker))
    return json.loads(raw) if raw else None
```

### Pattern 3: Celery App Factory + Beat Schedule

**What:** Single Celery app instance shared by workers and beat. Beat schedule targets market hours in America/Sao_Paulo timezone.

```python
# app/celery_app.py
# Source: Celery official docs + project-specific decisions
from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "investiq",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.modules.market_data.tasks"],
)

celery_app.conf.update(
    timezone="America/Sao_Paulo",
    enable_utc=True,  # Store internally as UTC, schedule in SP timezone
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    beat_schedule={
        # B3 quotes: every 15 min on weekdays during market hours (10h–17h BRT)
        "refresh-b3-quotes": {
            "task": "app.modules.market_data.tasks.refresh_quotes",
            "schedule": crontab(
                minute="*/15",
                hour="10-17",
                day_of_week="mon-fri",
            ),
        },
        # IBOVESPA benchmark: same schedule as quotes
        "refresh-ibovespa": {
            "task": "app.modules.market_data.tasks.refresh_ibovespa",
            "schedule": crontab(
                minute="*/15",
                hour="10-17",
                day_of_week="mon-fri",
            ),
        },
        # Macro indicators: every 6 hours (SELIC/CDI/IPCA change slowly)
        "refresh-macro": {
            "task": "app.modules.market_data.tasks.refresh_macro",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        # Fundamentals: once daily at 8am SP time (before market opens)
        "refresh-fundamentals": {
            "task": "app.modules.market_data.tasks.refresh_fundamentals",
            "schedule": crontab(hour=8, minute=0, day_of_week="mon-fri"),
        },
    },
)
```

### Pattern 4: Celery Worker with Sync SQLAlchemy Engine

**What:** Celery workers are synchronous processes. They cannot share the FastAPI async engine (asyncpg). Use a separate sync engine (`psycopg2`) created after worker process fork to avoid connection pool corruption.

**Critical:** Create the sync engine in the `worker_process_init` signal (after fork), not at module import time. Never share connections across processes.

```python
# app/core/db_sync.py
# Source: SQLAlchemy docs + celery/celery#9388 GitHub discussion
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from app.core.config import settings

# Convert asyncpg URL to psycopg2 URL
def _sync_url(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")

_sync_engine = None
SyncSessionLocal = None

def init_sync_engine():
    """Called once per worker process after fork (celery worker_process_init signal)."""
    global _sync_engine, SyncSessionLocal
    _sync_engine = create_engine(
        _sync_url(settings.DATABASE_URL),
        pool_pre_ping=True,
        pool_size=2,  # workers don't need large pools
        max_overflow=3,
    )
    SyncSessionLocal = sessionmaker(_sync_engine, expire_on_commit=False)

@contextmanager
def get_sync_session() -> Session:
    """Context manager for sync DB sessions in Celery tasks."""
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

```python
# In celery_app.py — hook into worker lifecycle
from celery.signals import worker_process_init

@worker_process_init.connect
def init_worker(**kwargs):
    from app.core.db_sync import init_sync_engine
    init_sync_engine()
```

### Pattern 5: brapi.dev Adapter with Redis Cache-Aside

**What:** Celery task fetches quotes from brapi.dev and writes to Redis. FastAPI routes read from Redis only — never call brapi.dev directly.

```python
# app/modules/market_data/adapters/brapi.py
# Source: brapi.dev docs at https://brapi.dev/docs
import httpx
import json

BRAPI_BASE = "https://brapi.dev/api"

def fetch_quotes(tickers: list[str], token: str) -> dict:
    """Sync HTTP call for Celery tasks. Returns dict of ticker -> quote data."""
    # Startup plan: up to 10 tickers per request
    ticker_str = ",".join(tickers[:10])
    url = f"{BRAPI_BASE}/quote/{ticker_str}"
    r = httpx.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={"fundamental": "false"},  # quotes only; fundamentals fetched separately
        timeout=10.0,
    )
    r.raise_for_status()
    data = r.json()
    return {item["symbol"]: item for item in data.get("results", [])}

def fetch_fundamentals(ticker: str, token: str) -> dict:
    """Fetch P/L, P/VP, DY, EV/EBITDA for a single ticker."""
    url = f"{BRAPI_BASE}/quote/{ticker}"
    r = httpx.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={"modules": "defaultKeyStatistics,financialData"},
        timeout=10.0,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    return results[0] if results else {}

def fetch_historical(ticker: str, token: str, range_: str = "1y") -> list[dict]:
    """OHLCV history for TradingView charts. range: 1d/5d/1mo/3mo/6mo/1y/2y/5y"""
    url = f"{BRAPI_BASE}/quote/{ticker}"
    r = httpx.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params={"range": range_, "interval": "1d"},
        timeout=15.0,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    if not results:
        return []
    return results[0].get("historicalDataPrice", [])
```

### Pattern 6: python-bcb Macro Adapter

**What:** Wraps python-bcb SGS calls and formats for Redis storage. All calls are synchronous (safe in Celery tasks). Returns pandas DataFrames converted to dicts.

```python
# app/modules/market_data/adapters/bcb.py
# Source: python-bcb docs at https://wilsonfreitas.github.io/python-bcb/
from bcb import sgs, currency, PTAX
from decimal import Decimal
import datetime

# SGS series codes (BCB official)
SGS_CDI   = 12    # Taxa DI / CDI diária
SGS_SELIC = 11    # Taxa SELIC diária
SGS_IPCA  = 433   # IPCA mensal

def fetch_cdi_rate() -> dict:
    """Latest CDI rate from BCB SGS."""
    df = sgs.get({"CDI": SGS_CDI}, last=1)
    latest = df.iloc[-1]
    return {
        "value": float(latest["CDI"]),
        "date": str(df.index[-1].date()),
        "unit": "% a.a.",
        "source": "BCB-SGS-12",
    }

def fetch_selic_rate() -> dict:
    """Latest SELIC target rate from BCB SGS."""
    df = sgs.get({"SELIC": SGS_SELIC}, last=1)
    latest = df.iloc[-1]
    return {
        "value": float(latest["SELIC"]),
        "date": str(df.index[-1].date()),
        "unit": "% a.a.",
        "source": "BCB-SGS-11",
    }

def fetch_ipca_rate() -> dict:
    """Latest IPCA monthly reading from BCB SGS."""
    df = sgs.get({"IPCA": SGS_IPCA}, last=1)
    latest = df.iloc[-1]
    return {
        "value": float(latest["IPCA"]),
        "date": str(df.index[-1].date()),
        "unit": "% a.m.",
        "source": "BCB-SGS-433",
    }

def fetch_usd_brl() -> dict:
    """Latest USD/BRL PTAX rate from BCB."""
    today = datetime.date.today().strftime("%-m/%-d/%Y")
    ptax = PTAX()
    ep = ptax.get_endpoint("CotacaoMoedaDia")
    result = ep.query().parameters(moeda="USD", dataCotacao=today).collect()
    if result is None or result.empty:
        # Fallback: last 5 days (weekend/holiday)
        ep2 = ptax.get_endpoint("CotacaoMoedaPeriodo")
        start = (datetime.date.today() - datetime.timedelta(days=5)).strftime("%-m/%-d/%Y")
        result = ep2.query().parameters(
            moeda="USD", dataInicial=start, dataFinalCotacao=today
        ).collect()
        result = result.tail(1)
    row = result.iloc[-1]
    return {
        "value": float(row["cotacaoVenda"]),
        "date": str(row["dataHoraCotacao"])[:10],
        "unit": "BRL/USD",
        "source": "BCB-PTAX",
    }
```

### Anti-Patterns to Avoid

- **Calling brapi.dev from FastAPI request handlers:** Never. All external HTTP calls happen in Celery tasks. The API reads Redis only. Violating this collapses the caching architecture on every request.
- **Using asyncio.run() inside a Celery task:** Creates a new event loop each invocation, breaks SQLAlchemy session pool, causes "attached to a different loop" errors. Use psycopg2 sync engine instead.
- **Sharing the asyncpg engine with Celery workers:** asyncpg is async-only and cannot be used in sync context. Workers need a separate psycopg2 engine created after process fork.
- **Creating the sync engine at module import time:** Module is imported in the main process before forking. Forked workers inherit a broken connection pool state. Always create in `worker_process_init` signal.
- **Storing Redis values as Python pickle:** Pickle is version-sensitive and a security risk. Always store as JSON strings.
- **Batching more than 10 tickers per brapi.dev request on Startup plan:** The Startup plan allows up to 10 tickers per request. Exceed it and the API returns 400/402.
- **Recomputing CMP on every API request from raw transactions:** Expensive O(n) scan on every read. Compute CMP at transaction write time, cache the position snapshot, serve from cache.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| BCB macro data fetch | Custom HTTP calls to BCB OData | `python-bcb` `sgs.get()` + `PTAX` | BCB OData pagination, date format quirks, authentication — already handled |
| B3 quotes | Raw scraping / alternative APIs | brapi.dev (primary) + yfinance (fallback) | B3 licensing; these APIs handle the scraping legally |
| Redis mock in tests | Manual dict-based fake | `fakeredis` | Full Redis command fidelity including TTL, EXPIRE, INCR — critical for testing quote cache logic |
| Task scheduling | Custom cron inside FastAPI lifespan | Celery beat | Distributed, retry logic, timezone-aware, process isolation |
| Ticker-to-position mapping | Custom join queries | Aggregate transactions in-memory after DB fetch | Simpler than complex SQL aggregation; positions are per-tenant per-ticker |
| Decimal precision for financial math | float | `Decimal` from stdlib | Float has binary rounding errors — `Decimal('10.67')` is exact, `10.67` (float) is not |

**Key insight:** Financial calculations require exact `Decimal` arithmetic throughout. CMP computed with floats will produce rounding errors that compound across transactions and produce wrong tax calculations. The Transaction model already uses `Numeric(18,8)` — always use `Decimal` in Python, never `float`, for price/quantity/CMP fields.

---

## Common Pitfalls

### Pitfall 1: CMP Drift from Float Arithmetic

**What goes wrong:** CMP is calculated using Python floats. After 20+ transactions, accumulated rounding errors produce a CMP that differs from B3's official calculation by a few centavos — enough to fail unit tests and produce incorrect IR values.

**Why it happens:** `0.1 + 0.2 != 0.3` in IEEE 754 floating point. Financial division compounds the error.

**How to avoid:** Use `Decimal` for ALL price, quantity, and CMP fields. Convert from DB `Numeric` to `Decimal`, not to `float`. The `Decimal` type in Python is arbitrary precision.

**Warning signs:** Unit tests against B3 examples pass with `pytest.approx(tolerance=0.01)` but fail at exact equality — this means float is being used somewhere.

### Pitfall 2: Celery Worker Inheriting Async Engine Connections

**What goes wrong:** The async SQLAlchemy engine (created at module import time in `db.py`) is inherited by forked Celery worker processes. The asyncpg connection pool is event-loop bound. Workers cannot use it in their synchronous context — `asyncio.get_event_loop()` in the worker context returns a closed/wrong loop.

**Why it happens:** Python `fork()` copies the parent process memory including open connections. asyncpg connections are not fork-safe.

**How to avoid:** Use `worker_process_init` Celery signal to initialize a fresh `psycopg2`-based sync engine after fork. Never call `get_db()` (the async FastAPI dependency) from a Celery task.

**Warning signs:** `RuntimeError: This event loop is already running` or `asyncpg.exceptions._base.InterfaceError: cannot call blocking function in an async context` in Celery worker logs.

### Pitfall 3: CMP Not Recalculated After Corporate Events

**What goes wrong:** A desdobramento (2:1 split) doubles the share count. The CMP is not halved. The next sell P&L calculation uses the old (pre-split) CMP against post-split prices — reporting a phantom loss of ~50% per share.

**Why it happens:** Corporate events retroactively change the position state. If CMP is stored once and not updated when events are applied, positions become incorrect.

**How to avoid:** When applying corporate events, always recalculate the position forward from the ex-date. The `apply_desdobramento()` pure function must be called in the position calculation pipeline before any sell after the event date. Store event application timestamp alongside each corporate action.

**Warning signs:** P&L for assets with known splits shows large phantom gains/losses; B3 example test cases fail after corporate event injection.

### Pitfall 4: Celery Beat Running as Multiple Instances

**What goes wrong:** Both a `celery-worker` and a `celery-beat` service are defined in Docker Compose but someone accidentally runs beat inside the worker service too. Quote refresh tasks fire twice per interval, doubling brapi.dev request count, hitting rate limits.

**Why it happens:** Celery workers can also run the beat scheduler with `--beat` flag. Easy to add accidentally.

**How to avoid:** Keep beat and worker as strictly separate Docker Compose services. Worker: `celery -A app.celery_app worker`. Beat: `celery -A app.celery_app beat`. Never add `--beat` to the worker command.

**Warning signs:** Duplicate tasks in Celery logs; brapi.dev request count in dashboard is twice the expected value.

### Pitfall 5: brapi.dev Free Tier Limits in Development

**What goes wrong:** Development uses the free tier (15,000 req/month, 30-min delay). The Startup/Pro plan is needed for 15-min delay and fundamentals access. Testing with the free tier works fine for the 4 test tickers but breaks when real portfolios have other assets.

**Why it happens:** brapi.dev free tier only gives full unrestricted access to PETR4, MGLU3, VALE3, ITUB4. Other tickers need a paid plan or a valid token.

**How to avoid:** Get the brapi.dev token from AWS Secrets Manager. For dev/test, use the 4 free tickers in all test fixtures. For production readiness, verify the Startup plan is active before Phase 2 launches.

**Warning signs:** `401 Unauthorized` or empty results for tickers other than the 4 free ones; fundamentals endpoint returns empty on free tier.

### Pitfall 6: python-bcb Date Format for PTAX

**What goes wrong:** PTAX `CotacaoMoedaDia` endpoint requires date in M/D/YYYY format (no zero-padding). Using `2026-03-14` (ISO format) returns an empty result or API error.

**Why it happens:** The BCB OData API uses a non-standard US-style date format.

**How to avoid:** Format PTAX dates with `date.strftime("%-m/%-d/%Y")` (removes zero-padding). On Windows, use `date.strftime("%#m/%#d/%Y")` instead (Windows strftime format). Wrap this in a platform-safe helper.

**Warning signs:** PTAX calls return empty DataFrames; exchange rate cache is never populated.

### Pitfall 7: Redis TTL Race Condition at Market Open

**What goes wrong:** At 10h00 BRT (market open), the beat schedule fires the quote refresh task. Between the previous 17h15 update (last market day) and 10h00 today, all quote keys have expired (TTL 20 min). User requests between 9h45 and 10h15 hit Redis, find nothing, and the cold-start fallback calls brapi.dev synchronously in the request path — violating the "never call external APIs in request" rule.

**Why it happens:** TTL is set to 20 min, but quotes may be 17 hours stale (after market closes). Keys expire and leave a window before the next Celery refresh.

**How to avoid:** Set TTL for closed-market hours to a longer value (e.g., 8 hours or `None`). After market close (17h30), the last quote task should set TTL to 8+ hours. Alternatively: cold-start fallback is acceptable ONLY during the first refresh after server restart, and should be async (return stale data + `data_stale: true` flag rather than blocking).

**Warning signs:** Slow API responses at 10h00–10h15 BRT; logs show `brapi.dev` called from FastAPI workers (not Celery workers).

---

## Code Examples

### B3 CMP Test Cases (Verified Against CONTEXT.md B3 Examples)

```python
# Source: B3 official methodology (from CONTEXT.md specifics)
# tests/test_cmp.py — pure unit tests, no DB required
from decimal import Decimal
from app.modules.portfolio.cmp import Position, apply_buy, apply_sell, apply_desdobramento

def test_cmp_buy_sequence():
    pos = Position("PETR4", Decimal("0"), Decimal("0"), Decimal("0"))
    # Buy 100 @ R$10 → CMP = R$10
    pos = apply_buy(pos, Decimal("100"), Decimal("10"))
    assert pos.cmp == Decimal("10")
    assert pos.quantity == Decimal("100")

    # Buy 50 more @ R$12 → CMP = (100×10 + 50×12) / 150 = R$10.666...
    pos = apply_buy(pos, Decimal("50"), Decimal("12"))
    expected_cmp = (Decimal("100") * Decimal("10") + Decimal("50") * Decimal("12")) / Decimal("150")
    assert pos.cmp == expected_cmp  # Decimal: exact
    assert pos.quantity == Decimal("150")

def test_cmp_sell_does_not_change_cmp():
    pos = Position("PETR4", Decimal("150"), Decimal("1600") / Decimal("150"), Decimal("1600"))
    cmp_before = pos.cmp
    # Sell 80 @ R$15 → P&L = (15 - CMP) × 80
    new_pos, pnl = apply_sell(pos, Decimal("80"), Decimal("15"))
    assert new_pos.cmp == cmp_before   # CMP must not change on sell
    assert new_pos.quantity == Decimal("70")
    assert pnl == (Decimal("15") - cmp_before) * Decimal("80")

def test_desdobramento_preserves_total_cost():
    pos = Position("PETR4", Decimal("100"), Decimal("10"), Decimal("1000"))
    split_pos = apply_desdobramento(pos, Decimal("2"))
    assert split_pos.quantity == Decimal("200")
    assert split_pos.cmp == Decimal("5")
    assert split_pos.total_cost == Decimal("1000")  # unchanged
```

### Celery Task: Quote Refresh

```python
# app/modules/market_data/tasks.py
# Source: project decisions + Celery official patterns
import json
import redis as redis_lib
from celery.utils.log import get_task_logger
from app.celery_app import celery_app
from app.core.config import settings

logger = get_task_logger(__name__)
_redis_client = None

def get_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_lib.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_client

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 60s backoff on brapi.dev errors
    name="app.modules.market_data.tasks.refresh_quotes",
)
def refresh_quotes(self, tickers: list[str] | None = None):
    """Refresh B3 quotes from brapi.dev into Redis cache."""
    from app.modules.market_data.adapters.brapi import fetch_quotes
    from app.core.db_sync import get_sync_session

    # Get list of active tickers from DB if not provided
    if tickers is None:
        with get_sync_session() as session:
            from sqlalchemy import text, select
            result = session.execute(
                text("SELECT DISTINCT ticker FROM transactions WHERE asset_class IN ('acao', 'BDR', 'ETF', 'FII')")
            )
            tickers = [row[0] for row in result]

    if not tickers:
        return

    # Fetch in batches of 10 (Startup plan limit)
    brapi_token = settings.BRAPI_TOKEN  # fetched from AWS SM at startup
    r = get_redis()
    import time
    for i in range(0, len(tickers), 10):
        batch = tickers[i:i+10]
        try:
            quotes = fetch_quotes(batch, brapi_token)
            for ticker, data in quotes.items():
                r.setex(f"market:quote:{ticker}", 60 * 20, json.dumps(data))
            if i + 10 < len(tickers):
                time.sleep(1)  # rate limit buffer between batch requests
        except Exception as exc:
            logger.error(f"brapi.dev fetch failed for batch {batch}: {exc}")
            raise self.retry(exc=exc)
```

### FastAPI Route: P&L Endpoint

```python
# app/modules/portfolio/router.py (sketch)
# Source: project decisions — Redis read only, no external calls
from fastapi import APIRouter, Depends
from app.core.db import get_tenant_db
from app.modules.portfolio.service import PortfolioService
import redis.asyncio as aioredis

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

@router.get("/pnl")
async def get_portfolio_pnl(
    db=Depends(get_tenant_db),
    redis_client: aioredis.Redis = Depends(get_redis_client),
):
    """Return per-asset and portfolio-level P&L using cached CMP + latest Redis quote."""
    service = PortfolioService(db, redis_client)
    return await service.calculate_portfolio_pnl()
```

### fakeredis Usage in Tests

```python
# tests/conftest.py additions for Phase 2
# Source: fakeredis docs at https://fakeredis.readthedocs.io/
import fakeredis
import pytest_asyncio

@pytest_asyncio.fixture
async def fake_redis_async():
    """Async fakeredis server for market data service tests."""
    server = fakeredis.FakeServer()
    r = fakeredis.aioredis.FakeRedis(server=server, decode_responses=True)
    yield r
    await r.aclose()

@pytest.fixture
def fake_redis_sync():
    """Sync fakeredis for Celery task tests."""
    server = fakeredis.FakeServer()
    r = fakeredis.FakeRedis(server=server, decode_responses=True)
    yield r
    r.close()
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| aioredis (separate async Redis lib) | `redis.asyncio` (built into redis-py 4.2+) | redis-py 4.2.0 (2022) | No separate aioredis install; `import redis.asyncio as aioredis` |
| `python-jose` for JWT | PyJWT 2.8.x | FastAPI docs update ~2024 | Already resolved in Phase 1 — do not use python-jose |
| `float` for financial calc | `Decimal` | Immutable best practice | Required for exact CMP; failures in IR calculations are legal liability |
| Celery `--beat` flag inside worker | Separate `celery beat` process | Celery 4+ best practice | Prevents duplicate task scheduling in multi-worker setups |
| `aioredis` in requirements.txt | `redis[asyncio]` or just `redis` 5.x | redis-py 5.x | redis-py 5.2.1 already in requirements.txt — no additional package needed |

**Deprecated/outdated:**
- `aioredis`: Do not add. Use `redis.asyncio` from the already-installed `redis==5.2.1`.
- `celery-pool-asyncio`: A workaround for running async tasks in Celery. Not needed here — market data tasks are sync-safe (HTTP calls, Redis writes). Avoid adding complexity.
- `pickle` serialization in Redis: Security risk. Use `json` as task_serializer and for all Redis values.

---

## brapi.dev Plan Decision

**CRITICAL: Verify brapi.dev plan before implementation begins (flagged in STATE.md)**

| Plan | Cost | Req/month | Delay | Max tickers/request | Fundamentals |
|------|------|-----------|-------|---------------------|--------------|
| Free | R$0 | 15,000 | 30 min | Any (4 free tickers only) | No |
| Startup | R$59.99/mo | 150,000 | 15 min | 10 | Selected indicators |
| Pro | R$99.99/mo | 500,000 | 5 min | 20 | Full (BP, DRE, DFC) |

**For Phase 2:** Startup plan is the minimum viable tier. 15-min delay is the project requirement. The free tier is sufficient only for development testing with the 4 free tickers.

**Rate limit strategy (no explicit per-minute limit documented):** Implement 1-second sleep between batch requests in Celery tasks to avoid triggering undocumented server-side throttling. Add `Retry-After` header handling in the adapter.

**Token storage:** brapi.dev token goes in AWS Secrets Manager. Add to `Settings` in `config.py` as `BRAPI_TOKEN: str = ""`. Never hardcode.

---

## Open Questions

1. **brapi.dev plan verification**
   - What we know: Startup plan costs R$59.99/mo and provides 15-min delay + fundamentals; token is required
   - What's unclear: Whether the project already has a plan activated; if not, delay purchases
   - Recommendation: Check brapi.dev account before Plan 02-02 implementation; development proceeds with 4 free tickers

2. **CMP for renda fixa (CDB, LCI, LCA)**
   - What we know: CMP methodology is defined for equity (buy/sell with market price)
   - What's unclear: Renda fixa does not have daily market price — it accrues. P&L is mark-to-book (contracted rate) not mark-to-market
   - Recommendation: Treat renda fixa P&L as: `current_value = principal × (1 + coupon_rate/year)^days_elapsed`; no CMP concept applies; display as "rendimento acumulado" not "P&L"

3. **IBOVESPA via brapi.dev**
   - What we know: brapi.dev supports indices; IBOVESPA may be at endpoint `/api/quote/^BVSP` or similar
   - What's unclear: Exact ticker symbol for IBOVESPA in brapi.dev — verify against the live API
   - Recommendation: Test with `^BVSP` and `IBOV` — use whichever returns data; document in adapter

4. **PTAX date format on Windows**
   - What we know: python-bcb PTAX requires M/D/YYYY format (no zero-padding); `%-m` works on Linux/Mac
   - What's unclear: Docker containers run Linux; development on Windows uses Git Bash — but the actual app runs in Docker (Linux), so `%-m` is safe
   - Recommendation: Use `%-m/%-d/%Y` in the Docker environment; add a comment noting Windows strftime difference

5. **Position snapshot storage vs. real-time recalculation**
   - What we know: Positions could be recalculated on every P&L request from raw transactions (accurate but O(n)); or a snapshot table could cache the current position state (fast but needs invalidation)
   - What's unclear: Portfolio size per user in v1 (likely <50 assets; O(n) recalc is acceptable)
   - Recommendation: Recalculate positions from transactions on each P&L request for v1 (simplest, no cache invalidation bugs); add position snapshot table only if performance degrades in Phase 3+

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already configured) |
| Config file | `backend/pytest.ini` — exists with `asyncio_mode = auto` |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |
| Estimated runtime | ~45 seconds (SQLite in-memory + fakeredis) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PORT-01 | POST /portfolio/transactions creates buy with CMP calculated | integration | `pytest tests/test_portfolio_api.py::test_create_buy_transaction -x` | Wave 0 |
| PORT-02 | FII dividend transaction stored with is_exempt=True | integration | `pytest tests/test_portfolio_api.py::test_fii_dividend_exempt -x` | Wave 0 |
| PORT-03 | Renda fixa transaction stores coupon_rate and maturity_date | integration | `pytest tests/test_portfolio_api.py::test_renda_fixa_transaction -x` | Wave 0 |
| PORT-04 | BDR and ETF transactions accepted with correct asset_class | integration | `pytest tests/test_portfolio_api.py::test_bdr_etf_transaction -x` | Wave 0 |
| PORT-05 | CMP recalculates correctly across buy/sell sequence (B3 examples) | unit | `pytest tests/test_cmp.py -x` | Wave 0 |
| PORT-06 | Desdobramento 2:1 doubles qty, halves CMP, leaves total_cost unchanged | unit | `pytest tests/test_cmp.py::test_desdobramento_preserves_total_cost -x` | Wave 0 |
| DATA-01 | Celery task writes quote to Redis; FastAPI reads from Redis (no external call) | integration | `pytest tests/test_market_data_tasks.py::test_refresh_quotes_writes_redis -x` | Wave 0 |
| DATA-02 | GET /market-data/macro returns SELIC, CDI, IPCA, câmbio from Redis | integration | `pytest tests/test_portfolio_api.py::test_macro_from_redis -x` | Wave 0 |
| DATA-03 | GET /market-data/fundamentals/{ticker} returns P/L, P/VP, DY, EV/EBITDA from Redis | integration | `pytest tests/test_portfolio_api.py::test_fundamentals_from_redis -x` | Wave 0 |
| DATA-04 | GET /market-data/historical/{ticker} returns OHLCV array from Redis | integration | `pytest tests/test_portfolio_api.py::test_historical_from_redis -x` | Wave 0 |

### Critical Unit Test Coverage: CMP Engine

The CMP engine (`cmp.py`) is pure Python with no framework dependencies. All tests run without DB or Redis. These tests are the ground truth for correctness.

```
tests/test_cmp.py:
  test_cmp_initial_buy              → PORT-05 (first buy establishes CMP)
  test_cmp_buy_sequence             → PORT-05 (B3 example: 100@10 then 50@12)
  test_cmp_sell_does_not_change_cmp → PORT-05 (sell preserves CMP)
  test_cmp_partial_sell             → PORT-05 (partial sell)
  test_desdobramento_preserves_total_cost → PORT-06
  test_grupamento_preserves_total_cost    → PORT-06
  test_bonificacao_adjusts_cmp           → PORT-06
  test_corporate_event_before_sell       → PORT-06 (split then sell = correct P&L)
```

### Sampling Rate
- **Per task commit:** `pytest tests/test_cmp.py tests/test_portfolio_api.py -x -q`
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_cmp.py` — pure unit tests for CMP engine (PORT-05, PORT-06)
- [ ] `backend/tests/test_portfolio_api.py` — API integration tests (PORT-01–04, DATA-02–04)
- [ ] `backend/tests/test_market_data_tasks.py` — Celery task tests with mocked brapi.dev + fakeredis (DATA-01)
- [ ] `backend/tests/test_portfolio_positions.py` — position calculation with corporate event sequences
- [ ] New conftest fixtures: `fake_redis_async`, `fake_redis_sync`, `mock_brapi_client`
- [ ] Package install: `pip install python-bcb yfinance psycopg2-binary fakeredis pandas`

---

## Sources

### Primary (HIGH confidence)
- brapi.dev/pricing — verified plan tiers (free: 15k req/30-min delay; Startup: 150k req/15-min delay/R$59.99)
- brapi.dev/docs/acoes.mdx — verified endpoint parameters including `modules`, `range`, `interval`, `fundamental`
- docs.celeryq.dev/en/stable/userguide/periodic-tasks.html — official Celery beat configuration + crontab + timezone
- wilsonfreitas.github.io/python-bcb/sgs.html — SGS API usage, series codes, DataFrame return format
- wilsonfreitas.github.io/python-bcb/currency.html — PTAX API, `CotacaoMoedaDia`, parameter format
- fakeredis.readthedocs.io — async + sync fakeredis support confirmed
- redis.io/faq — confirmed aioredis merged into redis-py 4.2+
- Phase 1 decisions: asyncpg engine, psycopg2 need for Celery, SET LOCAL RLS, shared Base

### Secondary (MEDIUM confidence)
- celery/celery GitHub discussion #9058 — asyncio + Celery limitations, asyncio.run() pitfall
- sqlalchemy/sqlalchemy GitHub discussion #5923 — sync vs async engine in same app pattern
- ryan-zheng.medium.com — Celery + SQLAlchemy connection pool isolation (post-fork pattern)
- SGS series codes: CDI=12, SELIC=11, IPCA=433 — sourced from BCB open data portal references in search results

### Tertiary (LOW confidence — flag for validation)
- brapi.dev exact per-minute rate limits: not documented publicly; 1-second batch sleep is conservative assumption
- IBOVESPA ticker symbol in brapi.dev: `^BVSP` assumed based on Yahoo Finance convention; must be verified against live API before Plan 02-02

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in requirements.txt or verified at PyPI/official docs
- CMP algorithm: HIGH — formula locked by CONTEXT.md, verified against B3 methodology description
- brapi.dev integration: HIGH for endpoints, MEDIUM for plan limits (confirmed pricing page; rate limits undocumented)
- python-bcb: MEDIUM — official docs consulted; PTAX date format edge case is LOW (Linux vs Windows)
- Celery-SQLAlchemy async bridge: HIGH — confirmed by SQLAlchemy official docs + multiple GitHub discussions
- Architecture patterns: HIGH — based on project's existing established patterns (db.py, conftest.py)

**Research date:** 2026-03-14
**Valid until:** 2026-04-14 (stable ecosystem; main risk: brapi.dev pricing changes or IBOVESPA ticker format)
