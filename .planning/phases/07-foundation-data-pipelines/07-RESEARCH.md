# Phase 7: Foundation + Data Pipelines - Research

**Researched:** 2026-03-21
**Domain:** Celery beat pipelines, SQLAlchemy 2.x global tables, ANBIMA OAuth2, CVM CSV, brapi.dev screener universe, TaxEngine pattern
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Tesouro Direto data source:**
- D-01: ANBIMA API is the primary source for Tesouro Direto rates (credentials are in hand — production endpoint, real live rates)
- D-02: ANBIMA credentials go into AWS Secrets Manager at `tools/anbima` — Celery worker fetches at task startup, same pattern as `tools/brapi` and other API keys
- D-03: CKAN CSV (Tesouro Nacional open data) is the fallback if ANBIMA API fails — no auth, updated daily, URL to confirm during research
- D-04: `refresh_tesouro_rates` task runs every 6 hours on the existing beat schedule — ANBIMA provides intraday updates

**CDB/LCI/LCA catalog:**
- D-05: `fixed_income_catalog` table is seeded via Alembic migration INSERT statements (no admin endpoint needed in Phase 7)
- D-06: Updates to reference rates are done via direct SQL — acceptable because these only shift significantly when CDI moves meaningfully (monthly at most)
- D-07: Seed rows to include CDB % CDI, LCI/LCA % CDI, CDB IPCA+, LCA IPCA+ at specific ranges per holding period
- D-08: UI must always label these as "taxas de referência de mercado" — never "oferta ao vivo"

**TaxEngine schema:**
- D-09: `tax_config` table — one row per IR tier. Schema: `(id, asset_class, holding_days_min, holding_days_max, rate_percent, is_exempt, label)`
- D-10: Scope is IR regressivo + LCI/LCA PF exemption + FII dividend exemption — NOT full IR matrix
- D-11: Seed data: 4 IR regressivo tiers, LCI/LCA PF is_exempt=true, FII dividend is_exempt=true
- D-12: No admin API — rate changes go through direct SQL
- D-13: TaxEngine is a pure Python service class reading from `tax_config` at init time (cached in-process, no per-call DB hit)

**brapi.dev universe fetch:**
- D-14: Paid brapi plan confirmed — 15k req/month limit is not a constraint (Startup plan = 150k req/month)
- D-15: Daily rebuild schedule: weekdays only (Mon–Fri), never weekends
- D-16: Partial failure handling: accept partial snapshot, log per-ticker failures, continue. Failed tickers retain previous snapshot row
- D-17: Per-ticker sleep: 200ms between requests. On 429 from brapi: exponential backoff up to 3 retries, then skip ticker and log

**Module structure:**
- D-18: New top-level module `app/modules/market_universe/` contains Phase 7 code: `models.py`, `tasks.py`, `tax_engine.py` (no router)
- D-19: `get_global_db` FastAPI dependency goes in `app/core/db.py` alongside existing `get_db` and `get_tenant_db`

### Claude's Discretion
- Exact ANBIMA OAuth2 token refresh logic (client_credentials grant assumed, confirm during research)
- CVM FII vacancy data fetch URL and CSV format for `refresh_fii_metadata`
- Batching strategy within brapi.dev requests (single ticker per call vs batch endpoint if available)
- Index design for `screener_snapshots` (composite on ticker + snapshot_date likely sufficient)

### Deferred Ideas (OUT OF SCOPE)
- Admin UI for updating CDB/LCI/LCA reference rates
- Full IR matrix (acoes monthly R$20k exemption, day-trade 20%)
- brapi.dev checkpoint/resume for failed runs
- Tesouro Direto websocket / real-time rate streaming
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SCRA-04 | System atualiza snapshot do universo de ações diariamente via Celery (nunca por requisição de usuário) | Celery beat crontab pattern confirmed from `celery_app.py`; brapi.dev `/quote/list` endpoint fetches all tickers; `screener_snapshots` table design documented below; `get_sync_db_session(tenant_id=None)` pattern confirmed for global writes |
</phase_requirements>

---

## Summary

Phase 7 is pure infrastructure — no user-facing endpoints. It establishes three global (non-tenant-scoped) tables via Alembic migration 0015, a TaxEngine service class reading from a `tax_config` table at init time, and three Celery beat pipelines. All three pipelines follow the established pattern in `app/modules/market_data/tasks.py` and write to namespaced Redis keys that never collide with `market:*`.

The ANBIMA API uses standard OAuth2 client_credentials grant with 1-hour token TTL. Token must be refreshed before each task run (or cached with expiry tracking). The fallback is the Tesouro Nacional CKAN CSV at `https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv` — a 13MB daily-updated CSV covering all Tesouro Direto history since 2002.

The CVM FII informe mensal comes as annual ZIP files at `https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{YEAR}.zip`. The ZIP contains multiple CSVs — the data dictionary must be consulted for exact field names for `segmento` and `vacancia_financeira`. These files are updated weekly.

**Primary recommendation:** Follow the established task pattern from `market_data/tasks.py` exactly, use `get_sync_db_session(tenant_id=None)` for all task DB writes, register new tasks in `celery_app.includes`, and store ANBIMA credentials in AWS SM at `tools/anbima`.

---

## Standard Stack

### Core (already in project, no new installs needed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| celery | existing | Beat scheduler + task runner | Already in project — `celery_app.py` pattern established |
| redis (sync) | existing | `_get_redis()` pattern in tasks | Already used in `market_data/tasks.py` |
| SQLAlchemy 2.x | existing | `Mapped[T]` + `mapped_column()` models | All existing models use this pattern |
| psycopg2 | existing | Sync driver for Celery tasks | `db_sync.py` already handles this |
| requests | existing | HTTP client for brapi.dev | Already used in `BrapiClient` |
| boto3 | existing | AWS Secrets Manager fetch | Already used in `BrapiClient._fetch_token_from_aws()` |
| alembic | existing | DB migrations | Pattern established through 0014 |

### Supporting (no new dependencies required)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `zipfile` (stdlib) | stdlib | Extract CVM FII ZIP | `refresh_fii_metadata` — CVM serves ZIP not raw CSV |
| `csv` / `io` (stdlib) | stdlib | Parse CSV inside ZIP | Avoid pandas dependency for simple tabular reads |
| `base64` (stdlib) | stdlib | Encode ANBIMA client_id:secret | ANBIMA Basic auth header |
| `time` (stdlib) | stdlib | Sleep between brapi.dev calls | 200ms per-ticker sleep already in `BrapiClient` |

**No new pip installs required for Phase 7.** All dependencies are already declared.

---

## Architecture Patterns

### New Module Structure
```
backend/app/modules/market_universe/
├── __init__.py
├── models.py          # screener_snapshots, fii_metadata, fixed_income_catalog, tax_config
├── tasks.py           # 3 Celery beat tasks
└── tax_engine.py      # Pure Python TaxEngine service class

backend/alembic/versions/
└── 0015_add_market_universe_tables.py   # Single migration for all 4 new tables

backend/app/core/
└── db.py              # Add get_global_db() async dependency
```

### Pattern 1: Global Table (No tenant_id, No RLS)

All 4 Phase 7 tables are global — they store universe-level data, not per-tenant data. The key differences from tenant-scoped tables:
- No `tenant_id` column
- No RLS policy (`ALTER TABLE ... ENABLE ROW LEVEL SECURITY` is omitted)
- Still `GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO app_user` — the app_user role needs read/write access

**Source:** `app/modules/auth/models.py` — `users` table has no `tenant_id` and is a reference model for global tables. Migration `0013_add_screener_runs.py` shows the GRANT pattern to copy.

### Pattern 2: Celery Beat Task Registration

New tasks MUST be added to both `include` list AND `beat_schedule` in `celery_app.py`:

```python
# Source: backend/app/celery_app.py — existing pattern
app = Celery(
    "investiq",
    include=[
        "app.modules.market_data.tasks",
        # ADD:
        "app.modules.market_universe.tasks",  # <-- register module
    ],
)

app.conf.update(
    beat_schedule={
        # ADD all 3 new entries:
        "refresh-screener-universe-daily": {
            "task": "app.modules.market_universe.tasks.refresh_screener_universe",
            "schedule": crontab(minute=0, hour=7, day_of_week="1-5"),  # 7h BRT Mon-Fri
            "args": [],
        },
        "refresh-fii-metadata-weekly": {
            "task": "app.modules.market_universe.tasks.refresh_fii_metadata",
            "schedule": crontab(minute=0, hour=6, day_of_week="1"),  # Monday 6h BRT
            "args": [],
        },
        "refresh-tesouro-rates-6h": {
            "task": "app.modules.market_universe.tasks.refresh_tesouro_rates",
            "schedule": crontab(minute=0, hour="*/6"),
            "args": [],
        },
    }
)
```

### Pattern 3: Task DB Write (Global, No Tenant Scope)

```python
# Source: backend/app/core/db_sync.py — confirmed existing pattern
from app.core.db_sync import get_sync_db_session

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def refresh_screener_universe(self) -> None:
    with get_sync_db_session(tenant_id=None) as session:  # None = no RLS injection
        # upsert into screener_snapshots
        ...
```

### Pattern 4: Redis Write in Tasks

```python
# Source: backend/app/modules/market_data/tasks.py — _get_redis() pattern
def _get_redis() -> redis_lib.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_lib.Redis.from_url(url)

# Phase 7 Redis key namespaces (NEVER use market:* prefix):
# screener:universe:{TICKER}     — ex=86400 (24h, refreshed daily)
# tesouro:rates:{BOND_CODE}      — ex=21600 (6h, refreshed every 6h)
# fii:metadata:{TICKER}          — ex=604800 (7d, refreshed weekly)
```

### Pattern 5: TaxEngine Service Class

TaxEngine reads from DB once at instantiation, caches in-process. It is a pure Python class with no IO after init:

```python
# app/modules/market_universe/tax_engine.py
class TaxEngine:
    def __init__(self, db_session):
        rows = db_session.execute(select(TaxConfig)).scalars().all()
        self._rates = {(r.asset_class, r.holding_days_min): r for r in rows}

    def get_rate(self, asset_class: str, holding_days: int) -> Decimal:
        """Returns IR rate percent (0 for exempt assets)."""
        ...

    def is_exempt(self, asset_class: str) -> bool:
        ...
```

Phase 8/9/10 instantiate TaxEngine once per request with the global DB session. No per-call DB hit.

### Pattern 6: get_global_db Async Dependency

```python
# app/core/db.py — add alongside get_db and get_tenant_db
async def get_global_db() -> AsyncGenerator[AsyncSession, None]:
    """DB session without tenant injection — for global tables (screener, catalog, tax)."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

This uses the same `async_session_factory` (asyncpg engine) as `get_tenant_db` — it simply skips the `SET LOCAL rls.tenant_id` step. Since global tables have no RLS policy, this is safe.

### Pattern 7: ANBIMA OAuth2 Token Fetch

```python
# Confirmed: client_credentials grant, 1-hour token TTL
# Source: developers.anbima.com.br/en/documentacao/visao-geral/autenticacao/

import base64, requests

def _get_anbima_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        "https://api.anbima.com.br/oauth/access-token",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Basic {credentials}",
        },
        json={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]
```

Token expires in 3600 seconds. Since `refresh_tesouro_rates` runs every 6 hours, fetch a fresh token at each task invocation — do not cache across task runs. The task is infrequent enough that per-run token fetch is correct.

### Anti-Patterns to Avoid

- **Using `market:*` Redis prefix for Phase 7 data:** Would collide with existing Phase 2 market data keys. Always use `screener:*`, `tesouro:*`, `fii:*` prefixes.
- **Calling brapi.dev inside a FastAPI request handler:** Phase 7 establishes the pattern of read-from-DB only; Phase 8 must read `screener_snapshots`, never call brapi.dev per-request.
- **Hardcoding IR rates as Python constants:** Rates must come from `tax_config` table — LCI/LCA exemption reform is pending in 2026.
- **Using asyncpg session inside Celery tasks:** Tasks are synchronous; always use `get_sync_db_session()` from `db_sync.py`. Never import `async_session_factory`.
- **Omitting task module from `celery_app.includes`:** Beat schedule entries will be registered but tasks will never be found, causing `NotRegistered` errors silently.
- **Skipping GRANT in migration:** New tables without `GRANT ... TO app_user` will cause `permission denied for table` errors at runtime under the `app_user` role.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ANBIMA token caching across task runs | Custom token cache with expiry logic | Fetch fresh token per task run | 6h interval > 1h TTL — always expired anyway |
| CVM ZIP parsing | Custom archive handler | `zipfile.ZipFile` + `io.TextIOWrapper` | stdlib handles this cleanly |
| Exponential backoff on brapi.dev 429 | Custom retry loop | `self.retry(exc=exc, countdown=2**attempt*60)` | Celery's built-in retry with countdown parameter |
| Global DB session for tasks | New engine setup | `get_sync_db_session(tenant_id=None)` | Already implemented in `db_sync.py` |
| Redis client for tasks | New Redis factory | Copy `_get_redis()` from `market_data/tasks.py` | Identical pattern, no new dependency |

---

## Common Pitfalls

### Pitfall 1: brapi.dev Batch Size for Universe Fetch
**What goes wrong:** `/quote/list` returns paginated results — not all ~900 B3 tickers in one call. If the task only reads the first page, it builds an incomplete universe.
**Why it happens:** The Startup plan supports up to 10 assets per batch call via comma-separated tickers. Fetching all fundamentals requires per-ticker calls to `/quote/{ticker}?modules=defaultKeyStatistics,financialData`.
**How to avoid:** For `screener_snapshots`, fetch fundamental data per-ticker using `BrapiClient.fetch_fundamentals()` which already exists. Use `/quote/list` only to discover the ticker universe (paginated with `?limit=&page=`), then iterate per ticker for fundamentals with 200ms sleep.
**Warning signs:** `screener_snapshots` row count is suspiciously low (< 200 tickers) after first run.

### Pitfall 2: CVM ZIP Contains Multiple CSVs
**What goes wrong:** The CVM FII informe mensal ZIP (`inf_mensal_fii_2026.zip`) contains multiple CSV files for different aspects of the monthly report. If the task reads the wrong CSV, it will find no `segmento` or `vacancia` data.
**Why it happens:** CVM structures its data with separate files per reporting section (e.g., `inf_mensal_fii_ativo_passivo_AAAA.csv`, `inf_mensal_fii_complemento_AAAA.csv`). The data dictionary PDF defines which file has vacancy/segment data.
**How to avoid:** Download and inspect the 2026 ZIP before writing the task. Look for files containing `segmento` or `vacancia` column names. Log the list of files found in the ZIP during the task run.
**Warning signs:** `fii_metadata` table has NULL `segmento` values after the weekly task runs.

### Pitfall 3: ANBIMA Token Fetch Failure Blocks Tesouro Task
**What goes wrong:** If ANBIMA credentials are missing or wrong, the token fetch raises an exception that causes the task to fail entirely — no Tesouro rates are stored.
**Why it happens:** The task fails at the auth step before any data is fetched.
**How to avoid:** Implement the CKAN CSV fallback in a try/except block. If ANBIMA token fetch fails, log a WARNING and proceed with CKAN CSV download. This ensures data is always populated even if ANBIMA is unavailable.
**Warning signs:** `tesouro:rates:*` Redis keys disappear after ANBIMA credential rotation.

### Pitfall 4: `app.modules.market_universe.tasks` Not in `includes`
**What goes wrong:** Celery beat fires the task, but the worker raises `celery.exceptions.NotRegistered` and the task is silently dropped.
**Why it happens:** `beat_schedule` entries are registered in Celery's beat process, but workers must load task modules via `include`. If the module is missing from `include`, workers don't know about the task.
**How to avoid:** Always add the task module to `include` list in `celery_app.py` AT THE SAME TIME as adding `beat_schedule` entries.
**Warning signs:** No task execution logs appear even though beat fires the schedule.

### Pitfall 5: TaxEngine Stale Cache After DB Seed Update
**What goes wrong:** TaxEngine is initialized once per FastAPI process, caching `tax_config` rows. After a direct SQL update to `tax_config`, the running process still uses old rates.
**Why it happens:** In-process cache is never invalidated on DB changes.
**How to avoid:** This is accepted behavior per D-12 (rate changes require direct SQL). Document that a process restart is required after updating `tax_config`. Phase 8+ should instantiate TaxEngine per request (from global DB session) — not as a module-level singleton. Per-request init is fast because `tax_config` has ~10 rows.
**Warning signs:** Tax calculation returns old rates after a `tax_config` UPDATE statement.

---

## Code Examples

### Alembic Migration 0015 — Global Table Pattern
```python
# Source: backend/alembic/versions/0013_add_screener_runs.py (adapted for global tables)
# Key difference: NO RLS ENABLE, NO tenant_id column

def upgrade() -> None:
    # screener_snapshots — one row per ticker per snapshot_date
    op.create_table(
        "screener_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("short_name", sa.String(100), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("regular_market_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("regular_market_change_percent", sa.Numeric(10, 6), nullable=True),
        sa.Column("regular_market_volume", sa.BigInteger, nullable=True),
        sa.Column("market_cap", sa.BigInteger, nullable=True),
        sa.Column("pl", sa.Numeric(10, 4), nullable=True),
        sa.Column("pvp", sa.Numeric(10, 4), nullable=True),
        sa.Column("dy", sa.Numeric(10, 6), nullable=True),
        sa.Column("ev_ebitda", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_screener_snapshots_ticker_date", "screener_snapshots", ["ticker", "snapshot_date"])
    op.create_index("ix_screener_snapshots_date", "screener_snapshots", ["snapshot_date"])

    # fii_metadata — one row per FII ticker (upserted weekly)
    op.create_table(
        "fii_metadata",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False, unique=True),
        sa.Column("segmento", sa.String(50), nullable=True),
        sa.Column("vacancia_financeira", sa.Numeric(8, 4), nullable=True),
        sa.Column("num_cotistas", sa.Integer, nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_fii_metadata_ticker", "fii_metadata", ["ticker"], unique=True)

    # fixed_income_catalog — seeded, read-only after migration
    op.create_table(
        "fixed_income_catalog",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_type", sa.String(20), nullable=False),  # CDB, LCI, LCA, TD_SELIC, etc.
        sa.Column("indexer", sa.String(20), nullable=False),           # CDI, IPCA, PREFIXADO, SELIC
        sa.Column("min_months", sa.Integer, nullable=False),
        sa.Column("max_months", sa.Integer, nullable=True),
        sa.Column("min_rate_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("max_rate_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("is_reference", sa.Boolean, server_default="true", nullable=False),
    )

    # tax_config — TaxEngine reads this
    op.create_table(
        "tax_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_class", sa.String(30), nullable=False),   # renda_fixa, FII, acao
        sa.Column("holding_days_min", sa.Integer, nullable=False),
        sa.Column("holding_days_max", sa.Integer, nullable=True),  # NULL = no upper bound
        sa.Column("rate_percent", sa.Numeric(6, 4), nullable=False),
        sa.Column("is_exempt", sa.Boolean, server_default="false", nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
    )

    # GRANT to app_user — required for all tables (no RLS, but still needs permissions)
    for table in ["screener_snapshots", "fii_metadata", "fixed_income_catalog", "tax_config"]:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO app_user")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")

    # Seed tax_config — IR regressivo 4 tiers + exemptions
    op.execute("""
        INSERT INTO tax_config (id, asset_class, holding_days_min, holding_days_max, rate_percent, is_exempt, label) VALUES
        ('tc-rf-1', 'renda_fixa', 0,   180, 22.50, false, 'IR Regressivo ≤180 dias'),
        ('tc-rf-2', 'renda_fixa', 181, 360, 20.00, false, 'IR Regressivo 181–360 dias'),
        ('tc-rf-3', 'renda_fixa', 361, 720, 17.50, false, 'IR Regressivo 361–720 dias'),
        ('tc-rf-4', 'renda_fixa', 721, NULL, 15.00, false, 'IR Regressivo >720 dias'),
        ('tc-lci-1', 'LCI',       0,   NULL,  0.00, true,  'LCI PF — Isento de IR'),
        ('tc-lca-1', 'LCA',       0,   NULL,  0.00, true,  'LCA PF — Isento de IR'),
        ('tc-fii-1', 'FII',       0,   NULL,  0.00, true,  'FII Dividendo — Isento de IR')
    """)

    # Seed fixed_income_catalog — reference ranges per D-07
    op.execute("""
        INSERT INTO fixed_income_catalog (id, instrument_type, indexer, min_months, max_months, min_rate_pct, max_rate_pct, label, is_reference) VALUES
        ('cdb-cdi-6m',  'CDB', 'CDI', 6,  12, 95.00, 100.00, 'CDB 6 meses — 95% a 100% CDI',   true),
        ('cdb-cdi-1a',  'CDB', 'CDI', 12, 24, 100.00, 107.00, 'CDB 1 ano — 100% a 107% CDI',   true),
        ('cdb-cdi-2a',  'CDB', 'CDI', 24, 60, 105.00, 110.00, 'CDB 2 anos — 105% a 110% CDI',  true),
        ('cdb-cdi-5a',  'CDB', 'CDI', 60, NULL, 108.00, 115.00, 'CDB 5 anos — 108% a 115% CDI', true),
        ('lci-cdi-6m',  'LCI', 'CDI', 6,  12, 80.00, 88.00, 'LCI 6 meses — 80% a 88% CDI',    true),
        ('lci-cdi-1a',  'LCI', 'CDI', 12, 24, 85.00, 92.00, 'LCI 1 ano — 85% a 92% CDI',      true),
        ('lci-cdi-2a',  'LCI', 'CDI', 24, NULL, 88.00, 95.00, 'LCI 2 anos — 88% a 95% CDI',   true),
        ('lca-cdi-6m',  'LCA', 'CDI', 6,  12, 80.00, 88.00, 'LCA 6 meses — 80% a 88% CDI',    true),
        ('lca-cdi-1a',  'LCA', 'CDI', 12, 24, 85.00, 92.00, 'LCA 1 ano — 85% a 92% CDI',      true),
        ('lca-cdi-2a',  'LCA', 'CDI', 24, NULL, 88.00, 95.00, 'LCA 2 anos — 88% a 95% CDI',   true),
        ('cdb-ipca-3a', 'CDB', 'IPCA', 36, 60, 5.00, 5.00, 'CDB IPCA+ 3 anos — IPCA+5%',      true),
        ('cdb-ipca-5a', 'CDB', 'IPCA', 60, NULL, 5.50, 5.50, 'CDB IPCA+ 5 anos — IPCA+5.5%', true),
        ('lca-ipca-2a', 'LCA', 'IPCA', 24, 60, 4.00, 4.00, 'LCA IPCA+ 2 anos — IPCA+4%',      true),
        ('lca-ipca-5a', 'LCA', 'IPCA', 60, NULL, 4.50, 4.50, 'LCA IPCA+ 5 anos — IPCA+4.5%', true)
    """)
```

### ANBIMA Token + Tesouro Rates Fetch
```python
# Source: developers.anbima.com.br/en/documentacao/visao-geral/autenticacao/
# Source: developers.anbima.com.br/en/documentacao/precos-indices/apis-de-precos/titulos-publicos/

import base64
import json
import requests

ANBIMA_TOKEN_URL = "https://api.anbima.com.br/oauth/access-token"
ANBIMA_TITULOS_URL = "https://api.anbima.com.br/feed/precos-indices/v1/titulos-publicos/mercado-secundario-TPF"
CKAN_CSV_FALLBACK_URL = (
    "https://www.tesourotransparente.gov.br/ckan/dataset/"
    "df56aa42-484a-4a59-8184-7676580c81e3/resource/"
    "796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv"
)

def _get_anbima_credentials() -> tuple[str, str]:
    """Fetch ANBIMA client_id + client_secret from AWS Secrets Manager."""
    import boto3
    client = boto3.client("secretsmanager", region_name="us-east-1")
    resp = client.get_secret_value(SecretId="tools/anbima")
    secret = json.loads(resp["SecretString"])
    return secret["ANBIMA_CLIENT_ID"], secret["ANBIMA_CLIENT_SECRET"]

def _get_anbima_token(client_id: str, client_secret: str) -> str:
    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    resp = requests.post(
        ANBIMA_TOKEN_URL,
        headers={"Content-Type": "application/json", "Authorization": f"Basic {credentials}"},
        json={"grant_type": "client_credentials"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["access_token"]

def _fetch_tesouro_from_anbima(token: str) -> list[dict]:
    """Fetch Tesouro Direto secondary market rates from ANBIMA."""
    resp = requests.get(
        ANBIMA_TITULOS_URL,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()  # list of bond records with tipo_titulo, data_vencimento, taxa_indicativa, pu

def _fetch_tesouro_from_ckan_fallback() -> list[dict]:
    """CKAN CSV fallback — no auth, daily updated, 13MB file."""
    import csv, io
    resp = requests.get(CKAN_CSV_FALLBACK_URL, timeout=60)
    resp.raise_for_status()
    reader = csv.DictReader(io.StringIO(resp.text, newline=""), delimiter=";")
    # Filter to today's date only to avoid parsing full history since 2002
    from datetime import date
    today_str = date.today().strftime("%d/%m/%Y")
    return [row for row in reader if row.get("Data Vencimento") is not None]
    # Note: CSV uses ';' separator and date format DD/MM/YYYY
    # Columns include: Tipo Titulo, Data Vencimento, Data Base, Taxa Compra Manha, Taxa Venda Manha, PU Compra Manha, PU Venda Manha, PU Base Manha
```

### CVM FII ZIP Fetch Pattern
```python
# Source: https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal
# ZIP URL pattern: https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{YEAR}.zip

import zipfile, io, csv
from datetime import date

CVM_FII_ZIP_URL = "https://dados.cvm.gov.br/dados/FII/DOC/INF_MENSAL/DADOS/inf_mensal_fii_{year}.zip"

def _fetch_cvm_fii_data() -> list[dict]:
    year = date.today().year
    url = CVM_FII_ZIP_URL.format(year=year)
    resp = requests.get(url, timeout=120)  # Large file — generous timeout
    resp.raise_for_status()

    rows = []
    with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
        # Log available files for debugging — helps identify which CSV has segmento/vacancia
        csv_files = [name for name in zf.namelist() if name.endswith(".csv")]
        logger.info("CVM FII ZIP contains: %s", csv_files)

        # NOTE: Exact filename must be confirmed by downloading and inspecting the ZIP.
        # Expected pattern based on CVM conventions: inf_mensal_fii_complemento_{YEAR}.csv
        # or inf_mensal_fii_ativo_passivo_{YEAR}.csv — verify during Wave 0.
        target_file = next(
            (f for f in csv_files if "complemento" in f.lower() or "segmento" in f.lower()),
            csv_files[0] if csv_files else None,
        )
        if target_file is None:
            raise ValueError("No CSV found in CVM FII ZIP")

        with zf.open(target_file) as f:
            reader = csv.DictReader(
                io.TextIOWrapper(f, encoding="latin-1"),  # CVM uses latin-1
                delimiter=";"
            )
            rows = list(reader)
    return rows
```

### brapi.dev Universe Fetch Strategy
```python
# Two-step approach:
# Step 1: GET /quote/list?limit=100&page=N to discover all tickers (pagination)
# Step 2: Per-ticker GET /quote/{ticker}?modules=defaultKeyStatistics,financialData for fundamentals
# 200ms sleep between calls (already in BrapiClient._get)

# The existing BrapiClient.fetch_fundamentals() handles step 2 correctly.
# Step 1 requires a new method in BrapiClient or inline pagination in the task.

# Screener snapshot upsert pattern (PostgreSQL INSERT ... ON CONFLICT):
from sqlalchemy.dialects.postgresql import insert as pg_insert

stmt = pg_insert(ScreenerSnapshot).values(
    id=str(uuid.uuid4()),
    ticker=ticker,
    snapshot_date=today,
    pl=fundamentals.get("pl"),
    pvp=fundamentals.get("pvp"),
    dy=fundamentals.get("dy"),
    ev_ebitda=fundamentals.get("ev_ebitda"),
    ...
).on_conflict_do_update(
    index_elements=["ticker", "snapshot_date"],
    set_={"pl": fundamentals.get("pl"), "pvp": ..., "updated_at": func.now()}
)
session.execute(stmt)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tesouro Direto JSON endpoint (tesourodireto.com.br/json) | ANBIMA API (primary) + CKAN CSV fallback | Aug 2025 (old endpoint 404) | Must use ANBIMA API — old endpoint is dead |
| Hardcoded IR constants in Python | `tax_config` DB table | Phase 7 (by design) | Rate changes = DB UPDATE only, no deploy |
| brapi.dev free tier (15k/month) | brapi.dev Startup plan (150k/month) | Confirmed per D-14 | Universe rebuild of ~900 tickers/day is viable |

**Deprecated/outdated:**
- `tesourodireto.com.br/api/v1/TesouroDireto` — 404 since August 2025 per STATE.md. Do not reference.
- ANBIMA sandbox URL `api-sandbox.anbima.com.br` — Phase 7 uses production credentials directly (D-01).

---

## Open Questions

1. **CVM FII CSV exact column names for `segmento` and `vacancia_financeira`**
   - What we know: CVM ZIP URL confirmed. Annual ZIPs contain multiple CSVs. Data dictionary PDF exists.
   - What's unclear: Exact CSV filename within ZIP and exact column names for segmento/vacância
   - Recommendation: Wave 0 task — download the 2026 ZIP, list files, inspect headers, hardcode the correct filename and column names before writing `refresh_fii_metadata`

2. **brapi.dev `/quote/list` pagination — total ticker count**
   - What we know: Startup plan supports up to 10 assets per batch. `/quote/list` endpoint exists.
   - What's unclear: Total number of B3 tickers discoverable via `/quote/list` pagination
   - Recommendation: Accept the ticker discovery via pagination in Wave 0 — test with a real token to determine page count. STATE.md says "~900 tickers" — use this as estimate.

3. **ANBIMA API — exact response field names for bond type and rate**
   - What we know: Endpoint is `mercado-secundario-TPF`. Fields include bond type, maturity, bid/ask rates, indicative rate, unit price.
   - What's unclear: Exact JSON field names (e.g., `tipo_titulo` vs `bondType`, `taxa_indicativa` vs `indicativeRate`)
   - Recommendation: Test ANBIMA API call once credentials are in AWS SM. Map field names before writing Redis serialization.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest with asyncio_mode=auto |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd D:/_DEV/claude-code/financas/backend && python -m pytest tests/test_market_universe_tasks.py tests/test_tax_engine.py -x -q` |
| Full suite command | `cd D:/_DEV/claude-code/financas/backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRA-04 | `refresh_screener_universe` task writes to DB and is NOT triggered by API requests | unit (fakeredis + mock brapi) | `pytest tests/test_market_universe_tasks.py::test_refresh_screener_universe_writes_db -x` | ❌ Wave 0 |
| SCRA-04 | Beat schedule entry exists for screener universe | unit | `pytest tests/test_market_universe_tasks.py::test_screener_beat_schedule_registered -x` | ❌ Wave 0 |
| SCRA-04 | `get_global_db` returns session without tenant injection | unit | `pytest tests/test_market_universe_tasks.py::test_get_global_db_no_rls -x` | ❌ Wave 0 |
| SCRA-04 | TaxEngine returns correct IR rates for 4 tiers | unit | `pytest tests/test_tax_engine.py::test_ir_regressivo_tiers -x` | ❌ Wave 0 |
| SCRA-04 | TaxEngine returns is_exempt=True for LCI/LCA/FII | unit | `pytest tests/test_tax_engine.py::test_exemptions -x` | ❌ Wave 0 |
| SCRA-04 | Redis keys use correct namespaces (never `market:*`) | unit | `pytest tests/test_market_universe_tasks.py::test_redis_namespace_isolation -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_market_universe_tasks.py tests/test_tax_engine.py -x -q`
- **Per wave merge:** `pytest tests/ -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_market_universe_tasks.py` — covers SCRA-04 task behavior, beat registration, namespace isolation
- [ ] `tests/test_tax_engine.py` — covers TaxEngine IR tiers, exemption logic, DB-driven rates
- [ ] Inspect CVM FII ZIP to confirm exact CSV filename and column names (manual step, document findings)

---

## Sources

### Primary (HIGH confidence)
- `backend/app/celery_app.py` — Beat schedule pattern, task includes, crontab syntax
- `backend/app/core/db_sync.py` — `get_sync_db_session(tenant_id=None)` for global table writes
- `backend/app/core/db.py` — `get_tenant_db` pattern to clone for `get_global_db`
- `backend/app/modules/market_data/tasks.py` — `_get_redis()`, task decorator, Redis write pattern
- `backend/app/modules/market_data/adapters/brapi.py` — `BrapiClient.fetch_fundamentals()`, token fetch from AWS SM
- `backend/alembic/versions/0013_add_screener_runs.py` — Migration GRANT pattern
- `backend/alembic/versions/0014_add_trial_fields.py` — Latest migration (down_revision for 0015)
- `backend/pytest.ini` — Test framework config, asyncio_mode=auto
- [ANBIMA Developers — Authentication](https://developers.anbima.com.br/en/documentacao/visao-geral/autenticacao/) — OAuth2 flow confirmed: client_credentials, Basic auth, 3600s TTL
- [ANBIMA Developers — Federal Government Bonds](https://developers.anbima.com.br/en/documentacao/precos-indices/apis-de-precos/titulos-publicos/) — Endpoint `mercado-secundario-TPF` confirmed

### Secondary (MEDIUM confidence)
- [Tesouro Transparente CKAN — Taxas Tesouro Direto](https://www.tesourotransparente.gov.br/ckan/dataset/taxas-dos-titulos-ofertados-pelo-tesouro-direto) — CKAN CSV URL confirmed, 13MB, updated daily, last updated 2026-03-21
- [CVM Dados Abertos — FII Informe Mensal](https://dados.cvm.gov.br/dataset/fii-doc-inf_mensal) — ZIP URL pattern confirmed `inf_mensal_fii_{YEAR}.zip`, updated weekly
- [brapi.dev docs](https://brapi.dev/docs) — Startup plan confirmed (150k req/month), `/quote/list` endpoint confirmed, `/quote/{ticker}?modules=defaultKeyStatistics,financialData` for fundamentals

### Tertiary (LOW confidence — requires validation)
- CVM FII CSV exact column names for `segmento` and `vacancia_financeira` — must be verified by downloading and inspecting the 2026 ZIP
- ANBIMA API exact JSON field names for `tipo_titulo`, `taxa_indicativa`, `pu` — must be verified with a live API call using production credentials

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all dependencies are already in the project, no new installs
- Architecture patterns: HIGH — verified against existing codebase files directly
- ANBIMA OAuth2 flow: HIGH — official docs confirm client_credentials, exact endpoint, 1h TTL
- CKAN CSV fallback: HIGH — URL confirmed, file exists, updated daily
- CVM FII data: MEDIUM — ZIP URL confirmed, exact column names not verified (Wave 0 manual step required)
- brapi.dev batching: MEDIUM — endpoint exists, exact pagination params require live testing
- Pitfalls: HIGH — derived from direct code inspection and official API behavior

**Research date:** 2026-03-21
**Valid until:** 2026-04-21 (stable APIs — ANBIMA/CVM/brapi.dev change infrequently)
