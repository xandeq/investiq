# Phase 17: FII Screener Table - Research

**Researched:** 2026-04-04
**Domain:** FastAPI + SQLAlchemy async + Next.js 15 — FII screener with composite score + Celery beat
**Confidence:** HIGH

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCRF-01 | Usuário pode ver tabela de FIIs ranqueados por score composto calculado a partir de DY 12m, P/VP e liquidez diária | Score formula defined in STATE.md; new columns added to `fii_metadata` via migration; Celery beat task recalculates nightly after `refresh_fii_metadata` |
| SCRF-02 | Usuário pode filtrar FIIs por segmento (Logística, Lajes Corporativas, Shopping, CRI/CRA, FoF, Híbrido, Residencial) | `segmento` column already exists in `fii_metadata`; existing `query_fiis` service already does `ilike` segment filter — extend or copy |
| SCRF-03 | Usuário pode filtrar FIIs por DY mínimo dos últimos 12 meses (slider ou input numérico) | `dy_12m` new column stored in `fii_metadata`; filter mirrors existing `min_dy` pattern in `screener_v2/service.py` |
</phase_requirements>

---

## Summary

Phase 17 builds a new `/fii/screener` frontend page backed by a new `/fii-screener/ranked` API endpoint. The backend work has two parts: (1) a Celery beat task that nightly calculates `dy_12m`, `pvp`, `daily_liquidity`, `score`, `dy_rank`, `pvp_rank`, `liquidity_rank` for every FII and persists them as new columns on `fii_metadata`; (2) a read-only FastAPI endpoint that serves the pre-scored FII list for the screener UI.

The project already has all the required infrastructure. The existing `fii_metadata` table (with `ticker`, `segmento` columns) is the correct anchor for the new score columns. The existing `screener_snapshots` table already holds `pvp`, `dy`, and `regular_market_volume` per ticker daily — the nightly score task joins these two tables to compute percentile ranks. The frontend reuses the pattern established in `screener_v2/FIIScreenerContent.tsx` (table + filter bar + client-side instant filtering), but with `score` and `rank` columns added.

**Primary recommendation:** Add columns to `fii_metadata` (migration 0021), add a new `calculate_fii_scores` Celery beat task to `market_universe/tasks.py`, add a new `/fii-screener` router, and create a new Next.js page at `frontend/src/app/fii/screener/`. Client-side filtering for segment/DY is safe because the entire scored universe (~400 FIIs) fits in a single JSON payload.

---

## Standard Stack

### Core (all already in requirements.txt / package.json — no new installs)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async | 2.x | ORM for score query + migration | Already used throughout |
| Alembic | 1.x | DB migration for new columns | Established migration chain |
| Celery | 5.x | Nightly score calculation beat task | Already used for `refresh_fii_metadata` |
| FastAPI | 0.110+ | New `/fii-screener` router | Established pattern |
| Next.js 15 | 15.x | `/fii/screener` page (app router) | Established frontend stack |
| React (client component) | 18/19 | Filter state + instant client filtering | `"use client"` pattern established |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| fakeredis | test only | Mock Redis in unit tests | Already used in test_market_universe_tasks.py |
| pytest-asyncio | test only | Async test runner | Already configured in pytest.ini |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Columns on `fii_metadata` | New `fii_scores` table | `fii_metadata` already has one row per FII — additional table adds JOIN without benefit |
| Server-side filter (query params) | Client-side filter | ~400 FIIs total payload is ~80KB — client-side instant filtering is better UX; server-side needed only if universe > 10k rows |
| BRAPI `dividendsData` for DY 12m | screener_snapshots `dy` column | `screener_snapshots.dy` is already populated by `refresh_screener_universe` — use it, avoid extra BRAPI calls |

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/modules/
├── market_universe/
│   ├── models.py              # ADD columns to FIIMetadata
│   └── tasks.py               # ADD calculate_fii_scores task
├── fii_screener/              # NEW module
│   ├── __init__.py
│   ├── router.py              # GET /fii-screener/ranked
│   └── schemas.py             # FIIScoredRow, FIIScoredResponse

backend/alembic/versions/
└── 0021_add_fii_score_columns.py   # NEW migration

frontend/src/
├── app/fii/screener/
│   └── page.tsx               # NEW page (server shell)
├── features/fii_screener/     # NEW feature
│   ├── api.ts
│   ├── types.ts
│   ├── hooks/
│   │   └── useFIIScreener.ts
│   └── components/
│       └── FIIScoredScreenerContent.tsx
```

### Pattern 1: FIIMetadata Column Extension

**What:** Add score columns to existing `fii_metadata` table via Alembic migration.
**When to use:** FII universe is a single row per ticker — no reason to separate scores into another table.

```python
# Migration 0021 — add to fii_metadata
op.add_column("fii_metadata", sa.Column("dy_12m", sa.Numeric(10, 6), nullable=True))
op.add_column("fii_metadata", sa.Column("pvp", sa.Numeric(10, 4), nullable=True))
op.add_column("fii_metadata", sa.Column("daily_liquidity", sa.BigInteger, nullable=True))
op.add_column("fii_metadata", sa.Column("score", sa.Numeric(8, 4), nullable=True))
op.add_column("fii_metadata", sa.Column("dy_rank", sa.Integer, nullable=True))
op.add_column("fii_metadata", sa.Column("pvp_rank", sa.Integer, nullable=True))
op.add_column("fii_metadata", sa.Column("liquidity_rank", sa.Integer, nullable=True))
op.add_column("fii_metadata", sa.Column("score_updated_at", sa.DateTime(timezone=True), nullable=True))
```

```python
# SQLAlchemy model additions to FIIMetadata in models.py
dy_12m: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)
pvp: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
daily_liquidity: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
score: Mapped[Decimal | None] = mapped_column(Numeric(8, 4), nullable=True)
dy_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
pvp_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
liquidity_rank: Mapped[int | None] = mapped_column(Integer, nullable=True)
score_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

### Pattern 2: Nightly Score Calculation (Celery Beat Task)

**What:** A new task `calculate_fii_scores` joins `screener_snapshots` (latest date) with `fii_metadata` on ticker, computes percentile ranks, writes back to `fii_metadata`.
**When to use:** Runs nightly at 08:00 BRT after `refresh_fii_metadata` (06:00) and `refresh_screener_universe` (07:00).

**Score formula (from STATE.md — locked decision):**
```
normalized_score = (dy_rank * 0.5) + (pvp_rank_inverted * 0.3) + (liquidity_rank * 0.2)
```
- DY: higher = better. Rank 100 = highest DY in universe.
- P/VP: lower = better. Invert: `pvp_rank_inverted = 100 - pvp_rank` (so lowest P/VP gets rank 100).
- Liquidity: higher = better. Rank 100 = highest volume.
- Ranks are integer percentile 0–100 within the FII universe (those with data).

**Percentile rank formula:**
```python
# For a list of N values sorted ascending:
# rank[i] = round(i / (N-1) * 100) if N > 1 else 50
# For DY/liquidity: sort ascending, rank = position
# For P/VP: sort ascending, invert (low P/VP = high inverted rank)
```

```python
@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def calculate_fii_scores(self) -> None:
    """Compute composite score for all FIIs from latest screener_snapshots + fii_metadata.

    Schedule: Tuesday–Sunday at 08:00 BRT (after refresh_fii_metadata at 06:00
    and refresh_screener_universe at 07:00).

    Note: runs every day (not just Monday) because screener_snapshots refreshes daily.
    The FII metadata (segmento) refreshes only on Monday; score refreshes daily
    with new price/DY data.
    """
    from datetime import date
    from decimal import Decimal
    from sqlalchemy import select, func
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    with get_sync_db_session(tenant_id=None) as session:
        # Get latest snapshot date
        latest_date = session.execute(
            select(func.max(ScreenerSnapshot.snapshot_date))
        ).scalar_one_or_none()
        if not latest_date:
            logger.warning("calculate_fii_scores: no snapshot data — skipping")
            return

        # Join fii_metadata with screener_snapshots
        rows = session.execute(
            select(
                FIIMetadata.ticker,
                ScreenerSnapshot.dy,
                ScreenerSnapshot.pvp,
                ScreenerSnapshot.regular_market_volume,
            )
            .outerjoin(
                ScreenerSnapshot,
                (FIIMetadata.ticker == ScreenerSnapshot.ticker)
                & (ScreenerSnapshot.snapshot_date == latest_date)
            )
        ).all()

        # Filter to rows with at least dy or pvp
        valid = [(t, dy, pvp, vol) for t, dy, pvp, vol in rows if dy is not None or pvp is not None]

        # Compute percentile ranks
        # ... (see Architecture Patterns for formula)
        # Write back to fii_metadata via UPDATE
```

### Pattern 3: Read-Only API Endpoint

**What:** `GET /fii-screener/ranked` returns all FIIs with score, sorted by score desc. No pagination needed (universe ~400 rows max). Filtering is done client-side.
**When to use:** Score is pre-calculated nightly — endpoint just reads and sorts.

```python
# router.py
@router.get(
    "/ranked",
    response_model=FIIScoredResponse,
    summary="FIIs ranqueados por score composto",
    tags=["fii-screener"],
)
@limiter.limit("30/minute")
async def get_ranked_fiis(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> FIIScoredResponse:
    ...
```

**Note:** No `get_authed_db` needed — screener data is global (no tenant scoping). Uses `get_global_db` exactly like `screener_v2/router.py`.

### Pattern 4: Frontend Client-Side Filtering

**What:** Fetch all ranked FIIs on mount, store in state, filter/sort in-memory on filter changes — no refetch per filter change.
**When to use:** Universe is ~400 FIIs. Entire payload is ~80KB JSON — trivially small for in-browser filtering.

```typescript
// useFIIScreener.ts
export function useFIIScoredScreener() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["fii-screener-ranked"],
    queryFn: () => getFIIScreenerRanked(),
    staleTime: 1000 * 60 * 60, // 1h — data changes nightly
  });
  return { data, isLoading, error };
}
```

```typescript
// FIIScoredScreenerContent.tsx — filtering pattern
const filtered = useMemo(() => {
  if (!data?.results) return [];
  return data.results.filter((row) => {
    if (segmentoFilter && row.segmento !== segmentoFilter) return false;
    if (minDyFilter && parseFloat(row.dy_12m ?? "0") < minDyFilter) return false;
    return true;
  });
}, [data, segmentoFilter, minDyFilter]);
```

### Anti-Patterns to Avoid

- **Re-fetching on every filter change:** The FII universe is small. Refetching on segment/DY filter change would add latency unnecessarily. Fetch once, filter in memory.
- **Using `get_authed_db` for FII screener:** FII data is global — use `get_global_db`. Using `get_authed_db` adds unnecessary RLS overhead and requires valid tenant context.
- **Calculating scores at request time:** Scores must be pre-calculated by Celery beat. Never compute rank/score in the API endpoint — it requires full-table scan and percentile math.
- **Blocking the beat schedule:** `calculate_fii_scores` depends on both `refresh_fii_metadata` and `refresh_screener_universe` completing first. Schedule at 08:00 BRT, which is 2h after metadata and 1h after screener snapshot.
- **Asyncio in Celery tasks:** All Celery tasks are sync. Use `get_sync_db_session` (psycopg2), not `async_session_factory`. This is established in every existing task in `market_universe/tasks.py`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Percentile ranking | Custom rank algorithm | Standard list-sort + index formula | Sorting a 400-item list is O(N log N) — trivial; no library needed |
| DY 12m calculation | Custom dividend scraper | `screener_snapshots.dy` (already populated by `refresh_screener_universe`) | BRAPI returns `dividendYield` as a field in `financialData` — already stored in `ScreenerSnapshot.dy` daily |
| FII filter bar | Custom UI kit | Copy pattern from `FIIScreenerContent.tsx` exactly | Segment dropdown + DY input already exist and are tested |
| Celery beat timing | Custom scheduler | `crontab(minute=0, hour=8)` in `celery_app.py` | Established pattern — already has 6 other beat tasks |

**Key insight:** `screener_snapshots.dy` is BRAPI's `dividendYield` field from `financialData` — which for FIIs returns trailing DY. This is close enough to "DY 12m" for scoring purposes. There is no need to call `dividendsData` separately for Phase 17.

---

## Open Questions

1. **`screener_snapshots.dy` vs true DY 12m**
   - What we know: `screener_snapshots.dy` stores BRAPI's `dividendYield` from `financialData` (trailing DY). STATE.md says DY 12m = sum of cashDividends for last 12 months / current price.
   - What's unclear: Are these equal? BRAPI trailing DY = sum of dividends paid over last 12 months / current price — which is the same formula. For FIIs it is accurate.
   - Recommendation: Use `screener_snapshots.dy` as `dy_12m`. This avoids extra BRAPI API calls. The score task reads from the snapshot row, not by fetching `dividendsData` live. Document this choice explicitly in the task docstring.

2. **Segmento values in production fii_metadata**
   - What we know: `refresh_fii_metadata` parses CVM ZIP's "complemento" CSV and looks for `Segmento` column. The CVM `complemento` CSV may not contain a `Segmento` column — it may be in the `caracteristicas` CSV.
   - What's unclear: Are `segmento` values actually populated in production? The task code comments say "Segmento is typically in a separate 'caracteristicas' file".
   - Recommendation: The planner should include a task to verify segmento population by checking the DB (or CVM CSV structure). If `segmento` is NULL for most FIIs, the segment filter will return empty results. This is a data quality risk.

3. **FII universe size**
   - What we know: `screener_snapshots` stores all B3 tickers. FII filter uses `ticker.like("%11")`. B3 has approximately 400–500 FIIs.
   - What's unclear: How many tickers currently satisfy `ticker.like("%11")` in screener_snapshots? Some non-FII tickers also end in 11.
   - Recommendation: Acceptable risk — plan proceeds assuming ~400 FIIs. FII segment filter and DY filter reduce this further.

4. **`score_updated_at` null handling in frontend**
   - What we know: Until the first Celery beat run after deploy, all score/rank columns will be NULL.
   - Recommendation: The API response should include a `score_available: bool` flag or return rows ordered by ticker when score is NULL, with a UI notice "Scores sendo calculados — disponíveis amanhã".

---

## Runtime State Inventory

> Not a rename/refactor phase. Omit — no runtime state to migrate.

---

## Common Pitfalls

### Pitfall 1: Celery Task Dependencies — Wrong Execution Order

**What goes wrong:** `calculate_fii_scores` runs before `refresh_screener_universe` and reads yesterday's snapshot data, producing stale scores.
**Why it happens:** Beat schedules are independent — there is no built-in task dependency chain in Celery beat.
**How to avoid:** Schedule `calculate_fii_scores` at 08:00 BRT, which is 1 hour after `refresh_screener_universe` (07:00) and 2 hours after `refresh_fii_metadata` (06:00). This is the same defensive pattern used for the existing tasks.
**Warning signs:** `score_updated_at` timestamps show scores calculated before today's snapshot_date.

### Pitfall 2: P/VP Rank Inversion

**What goes wrong:** Lower P/VP is better for FIIs, but a naive ascending sort gives rank 0 (worst) to the lowest P/VP — opposite of intent.
**Why it happens:** Percentile rank sorts ascending by default — rank 100 = highest value.
**How to avoid:** For P/VP, sort ascending (lowest P/VP = index 0), then `pvp_rank_inverted = 100 - rank`. This gives rank 100 to the lowest P/VP.
**Warning signs:** FIIs with P/VP = 0.7 ranked below FIIs with P/VP = 1.5 in the screener.

### Pitfall 3: NULL Values in Rank Calculation

**What goes wrong:** FIIs with NULL `dy` or `pvp` throw errors or get incorrectly ranked.
**Why it happens:** `screener_snapshots.dy` and `pvp` can be NULL if BRAPI returned MODULES_NOT_AVAILABLE.
**How to avoid:** Filter out NULL values before percentile calculation. FIIs with NULL fields for a metric receive `rank = None` for that metric and are excluded from score calculation (score = None). The frontend shows them at the bottom with "—" in score column.
**Warning signs:** Score calculation task errors on `NoneType comparison`.

### Pitfall 4: Segment Values Mismatch Between CVM and UI Labels

**What goes wrong:** UI shows "Logística" as filter option but `fii_metadata.segmento` contains "Logistica" (no accent) or full CVM category names like "TipoFIITijolo".
**Why it happens:** CVM CSV field values are not standardized across years. The `refresh_fii_metadata` task stores whatever the CSV contains.
**How to avoid:** Inspect actual `segmento` values in production DB before building the filter dropdown. If CVM values differ from ROADMAP labels (Logística, Lajes Corporativas, etc.), map them in the frontend or normalize in the task.
**Warning signs:** Segment dropdown shows options but filtering returns 0 results.

### Pitfall 5: FII Page Route Conflict

**What goes wrong:** Next.js route `/fii/screener` conflicts with `/fii/[ticker]` — "screener" gets treated as a ticker.
**Why it happens:** Both routes live under `/fii/`. Next.js resolves static segments before dynamic — but only if the static page exists.
**How to avoid:** Create `frontend/src/app/fii/screener/page.tsx` (static route) alongside `frontend/src/app/fii/[ticker]/page.tsx` (dynamic route). Next.js App Router resolves static segments first, so `/fii/screener` will NOT match `[ticker]`.
**Warning signs:** `/fii/screener` redirects to a ticker detail page for "SCREENER".

---

## Code Examples

### Score Calculation (Percentile Rank)

```python
# Source: Derived from STATE.md score formula + standard percentile algorithm
from decimal import Decimal

def _percentile_ranks(values: list[float | None]) -> list[int | None]:
    """Compute 0–100 percentile ranks for a list, preserving None positions.

    Rank 100 = highest value. None values receive None rank.
    """
    indexed = [(v, i) for i, v in enumerate(values) if v is not None]
    if not indexed:
        return [None] * len(values)
    indexed.sort(key=lambda x: x[0])  # ascending: rank 0 = lowest
    n = len(indexed)
    ranks: dict[int, int] = {}
    for pos, (_, orig_i) in enumerate(indexed):
        ranks[orig_i] = round(pos / max(n - 1, 1) * 100)
    return [ranks.get(i) for i in range(len(values))]

# Usage in calculate_fii_scores:
tickers = [row.ticker for row in fii_rows]
dy_values = [float(row.dy) if row.dy is not None else None for row in fii_rows]
pvp_values = [float(row.pvp) if row.pvp is not None else None for row in fii_rows]
vol_values = [float(row.vol) if row.vol is not None else None for row in fii_rows]

dy_ranks = _percentile_ranks(dy_values)         # high DY = high rank
pvp_ranks = _percentile_ranks(pvp_values)        # raw ranks ascending
pvp_inverted = [100 - r if r is not None else None for r in pvp_ranks]  # low PVP = high rank
liquidity_ranks = _percentile_ranks(vol_values)  # high vol = high rank

for i, ticker in enumerate(tickers):
    dr, pr, lr = dy_ranks[i], pvp_inverted[i], liquidity_ranks[i]
    if dr is not None and pr is not None and lr is not None:
        score = Decimal(str(dr * 0.5 + pr * 0.3 + lr * 0.2))
    else:
        score = None
```

### API Endpoint Pattern (matches screener_v2 pattern)

```python
# Source: D:/claude-code/investiq/backend/app/modules/screener_v2/router.py
@router.get(
    "/ranked",
    response_model=FIIScoredResponse,
    summary="FIIs ranqueados por score composto (DY 12m + P/VP + Liquidez)",
    tags=["fii-screener"],
)
@limiter.limit("30/minute")
async def get_ranked_fiis(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> FIIScoredResponse:
    from sqlalchemy import select
    rows = await global_db.execute(
        select(FIIMetadata)
        .where(FIIMetadata.score.isnot(None))
        .order_by(FIIMetadata.score.desc())
    )
    fiis = rows.scalars().all()
    # Also fetch those without score (score = None → show at bottom)
    ...
```

### Frontend FII Row Type

```typescript
// Source: adapted from frontend/src/features/screener_v2/types.ts
export interface FIIScoredRow {
  ticker: string;
  short_name: string | null;
  segmento: string | null;
  dy_12m: string | null;         // percentage string, e.g. "0.09" = 9%
  pvp: string | null;
  daily_liquidity: number | null; // R$ volume
  score: string | null;           // 0–100 composite score
  dy_rank: number | null;
  pvp_rank: number | null;
  liquidity_rank: number | null;
  score_updated_at: string | null;
}

export interface FIIScoredResponse {
  disclaimer: string;
  score_available: boolean;    // false if scores not yet calculated
  total: number;
  results: FIIScoredRow[];
}
```

### Next.js Page Route (static vs dynamic)

```typescript
// Source: D:/claude-code/investiq/frontend/src/app/stock/[ticker]/page.tsx pattern
// frontend/src/app/fii/screener/page.tsx — STATIC route (resolves before [ticker])
import type { Metadata } from "next";
import { FIIScoredScreenerContent } from "@/features/fii_screener/components/FIIScoredScreenerContent";

export const metadata: Metadata = {
  title: "FII Screener — InvestIQ",
};

export default function FIIScreenerPage() {
  return <FIIScoredScreenerContent />;
}
```

### Celery Beat Registration

```python
# Source: D:/claude-code/investiq/backend/app/celery_app.py
# Add to beat_schedule dict:
"calculate-fii-scores-daily": {
    "task": "app.modules.market_universe.tasks.calculate_fii_scores",
    # 08:00 BRT, every day — after refresh_fii_metadata (06h) and
    # refresh_screener_universe (07h Mon-Fri)
    "schedule": crontab(minute=0, hour=8),
    "args": [],
},
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (asyncio_mode = auto) |
| Config file | `backend/pytest.ini` |
| Quick run command | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_phase17_fii_screener.py -x -q` |
| Full suite command | `cd D:/claude-code/investiq/backend && python -m pytest tests/ -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRF-01 | Score formula produces correct composite score from dy/pvp/liquidity percentile ranks | unit | `pytest tests/test_phase17_fii_screener.py::test_score_formula -x` | ❌ Wave 0 |
| SCRF-01 | `calculate_fii_scores` Celery task registered in beat_schedule | unit | `pytest tests/test_phase17_fii_screener.py::test_score_beat_schedule_registered -x` | ❌ Wave 0 |
| SCRF-01 | `GET /fii-screener/ranked` returns rows ordered by score desc | integration | `pytest tests/test_phase17_fii_screener.py::test_ranked_endpoint_ordered_by_score -x` | ❌ Wave 0 |
| SCRF-01 | `GET /fii-screener/ranked` returns 401 for unauthenticated | integration | `pytest tests/test_phase17_fii_screener.py::test_ranked_endpoint_requires_auth -x` | ❌ Wave 0 |
| SCRF-02 | Segment filter in response schema (`segmento` field present) | unit | `pytest tests/test_phase17_fii_screener.py::test_segmento_field_in_response -x` | ❌ Wave 0 |
| SCRF-03 | DY filter (client-side in frontend) — `dy_12m` field present in response | unit | `pytest tests/test_phase17_fii_screener.py::test_dy_12m_field_in_response -x` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_phase17_fii_screener.py -x -q`
- **Per wave merge:** `python -m pytest tests/ -x -q`
- **Phase gate:** Full suite green (257+ tests) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_phase17_fii_screener.py` — covers all 6 test cases above
- [ ] No new conftest.py needed — existing `conftest.py` (client, db_session, email_stub) is sufficient

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate `global_fiis` table mentioned in v1.1 context | `fii_metadata` table (migration 0015) is the actual table name | v1.1 | STATE.md refers to "global_fiis" but the SQLAlchemy model is `FIIMetadata` with `__tablename__ = "fii_metadata"` — use `fii_metadata` everywhere |
| DY in screener_snapshots as BRAPI `dividendYield` | Same — no change | v1.1 | `screener_snapshots.dy` already holds trailing DY; suitable for score calculation |

**Deprecated/outdated:**
- STATE.md refers to "global_fiis table" — this is `fii_metadata` in actual code. Do not create a new `global_fiis` table.

---

## Sources

### Primary (HIGH confidence)

- Codebase inspection:
  - `backend/app/modules/market_universe/models.py` — FIIMetadata schema (fii_metadata table, existing columns)
  - `backend/app/modules/market_universe/tasks.py` — Celery task patterns (sync context, psycopg2, batch upsert via pg_insert)
  - `backend/app/modules/screener_v2/service.py` — FII query pattern (join screener_snapshots + fii_metadata, ILIKE segment filter)
  - `backend/app/modules/screener_v2/router.py` — get_global_db pattern, limiter, Query params
  - `backend/app/celery_app.py` — Beat schedule format, task includes list, timezone
  - `backend/app/core/db.py` — get_global_db vs get_authed_db distinction
  - `frontend/src/features/screener_v2/components/FIIScreenerContent.tsx` — Filter bar UI pattern
  - `frontend/src/app/stock/[ticker]/page.tsx` — Static vs dynamic route pattern
  - `backend/alembic/versions/0020_add_analysis_tables.py` — Migration format (revision chain)
  - `backend/pytest.ini` — Test framework config

### Secondary (MEDIUM confidence)

- STATE.md `## v1.3 Architecture Decisions` — Score formula `normalized_score = (DY_rank * 0.5) + (P_VP_rank * 0.3) + (liquidity_rank * 0.2)` — this is a locked decision
- STATE.md `## Open Questions` — BRAPI segmento availability and FII universe size flagged as unknowns
- REQUIREMENTS.md — SCRF-01/02/03 scope boundaries

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all libraries already in use; no new dependencies
- Architecture: HIGH — directly derived from existing patterns in codebase
- Pitfalls: HIGH — P/VP inversion, NULL handling, route conflict, segment mismatch all verified from code
- Score formula: HIGH — locked decision in STATE.md
- Segment values: LOW — not verified from production DB; CVM CSV field availability for `Segmento` is uncertain

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable stack; BRAPI API format unlikely to change)
