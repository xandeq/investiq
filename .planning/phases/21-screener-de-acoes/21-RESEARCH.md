# Phase 21: Screener de Ações - Research

**Researched:** 2026-04-12
**Domain:** FastAPI endpoint + SQLAlchemy async migration + Next.js 15 client-side screener
**Confidence:** HIGH — all findings verified against actual production codebase files

## Summary

Phase 21 adds a filterable universe screener for ~900 B3 equities. The backend requires three coordinated changes: (1) Migration 0024 adds `variacao_12m_pct` to `screener_snapshots`, (2) `BrapiClient.fetch_fundamentals()` extracts `52WeekChange` from `defaultKeyStatistics`, and (3) a new `GET /screener/universe` endpoint returns all rows from the latest snapshot without server-side filtering. The frontend replicates the Phase 17 FII screener pattern exactly: a `useAcoesUniverse` hook fetches the full dataset once, `useMemo` applies client-side filters, and paginaton is purely in-memory at PAGE_SIZE=50.

**Critical data gap confirmed:** `screener_snapshots` currently has NO `variacao_12m_pct` column — only `regular_market_change_percent` (daily %). The migration is a hard prerequisite. Until the migration runs and the next Celery beat executes, this column will be NULL for all rows.

**Primary recommendation:** Implement backend (migration + brapi extraction + endpoint) in Wave 1 before any frontend work. The frontend depends on the new `variacao_12m_pct` field being populated.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Coluna `variacao_12m_pct Numeric(10,6) NULLABLE` via Migration 0024 (head: 0023)
- **D-02:** `BrapiClient.fetch_fundamentals()` extrai `52WeekChange` de `defaultKeyStatistics`, retorna como `variacao_12m`
- **D-03:** Upsert em `refresh_screener_universe` mapeia e persiste `variacao_12m_pct` — campo pode ser NULL
- **D-04:** Exibir como `Var. 12m%` com cor verde/vermelho — reutilizar `changeBadge()` existente
- **D-05:** Nova página em `frontend/app/acoes/screener/page.tsx` — diretório não existe ainda
- **D-06:** Novo feature directory `frontend/src/features/acoes_screener/`
- **D-07:** Rota `/screener/acoes` existente permanece intacta — duas rotas coexistem
- **D-08:** Filtros client-side com `useMemo` (igual Phase 17)
- **D-09:** `GET /screener/universe` em `backend/app/modules/screener_v2/router.py` — retorna todos os ~900 tickers sem filtros, sem paginação
- **D-10:** Response fields: `ticker`, `short_name`, `sector`, `regular_market_price`, `variacao_12m_pct`, `dy`, `pl`, `market_cap`
- **D-11:** DY decimal (0.09=9%) — frontend multiplica por 100
- **D-12:** Endpoint requer `get_current_user` + `get_global_db`
- **D-13:** Filtros: DY mín (input numérico em %), P/L máx (input), Setor B3 (dropdown), Market Cap (botões small/mid/large)
- **D-14:** Market Cap tiers: Small < R$ 2B, Mid R$ 2B–10B, Large > R$ 10B
- **D-15:** Ordenação client-side por qualquer coluna — clique no header alterna asc/desc
- **D-16:** Paginação client-side PAGE_SIZE=50
- **D-17:** Click no ticker → `<Link href={/stock/${ticker}}>`

### Claude's Discretion
- Valores exatos dos setores B3 disponíveis no dropdown (pesquisar via `SELECT DISTINCT sector FROM screener_snapshots ORDER BY sector` antes de hardcodar)
- Skeleton/loading state enquanto endpoint carrega
- Mensagem de empty state quando nenhum ativo passa nos filtros
- Ordenação inicial (default): sem ordenação definida ou por market_cap desc
- Exact spacing e typography

### Deferred Ideas (OUT OF SCOPE)
- Nenhuma sugestão de escopo adicional surgiu durante a discussão
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SCRA-01 | Tabela de ações ordenável (Ticker, Nome, Setor, Preço, Var 12m%, DY, P/L, Market Cap) | Migration 0024 adds `variacao_12m_pct`; endpoint returns all 8 fields; client-side sort via useState + useMemo |
| SCRA-02 | Filtros DY mínimo / P/L máximo / Setor B3 / Market Cap | Full dataset loaded once; useMemo filters applied in-memory; pattern confirmed from FIIScoredScreenerContent |
| SCRA-03 | Click ticker → /stock/[ticker] | `<Link href={/stock/${ticker}}>` — `/stock/[ticker]` page already exists and is confirmed operational |
| SCRA-04 | Paginação da tabela | Client-side pagination at PAGE_SIZE=50, same pattern as AcoesScreenerContent (currentPage / totalPages calculated from filtered.length) |
</phase_requirements>

## Standard Stack

### Core — Already in Project
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | HTTP router for `/screener/universe` | Already in use; `screener_v2/router.py` is the target file |
| SQLAlchemy async | existing | `query_screener_universe()` service function | Pattern from `query_acoes()` — same `select + func.max(snapshot_date)` pattern |
| Alembic | existing | Migration 0024 | Pattern from `0023_add_swing_trade_operations.py` — sqlite dialect gate |
| React Query (`@tanstack/react-query`) | existing | `useAcoesUniverse` hook | Same pattern as `useFIIScoredScreener` — `staleTime: 1h`, no re-fetch on filter change |
| Next.js 15 | existing | `app/acoes/screener/page.tsx` | appDir confirmed at `frontend/app/` (not `frontend/src/app/`) |
| Tailwind CSS | existing | All table styling | `max-w-7xl`, `font-mono`, `text-xs`, `animate-pulse` skeleton — exact classes from reference files |

### Installation
No new packages required. All dependencies already in production.

## Architecture Patterns

### Recommended Project Structure (new files only)
```
backend/
├── alembic/versions/
│   └── 0024_add_variacao_12m_pct.py          # ADD column to screener_snapshots
├── app/modules/
│   ├── market_universe/
│   │   └── models.py                          # ADD variacao_12m_pct field
│   ├── market_data/adapters/
│   │   └── brapi.py                           # ADD 52WeekChange extraction
│   ├── market_universe/
│   │   └── tasks.py                           # ADD variacao_12m_pct to upsert
│   └── screener_v2/
│       ├── router.py                          # ADD GET /screener/universe
│       ├── schemas.py                         # ADD ScreenerUniverseRow + Response
│       └── service.py                         # ADD query_screener_universe()
frontend/
├── app/acoes/screener/
│   └── page.tsx                               # NEW page (dir doesn't exist yet)
└── src/features/acoes_screener/
    ├── api.ts                                 # getAcoesUniverse()
    ├── types.ts                               # AcoesUniverseRow, AcoesUniverseResponse
    ├── hooks/
    │   └── useAcoesUniverse.ts                # useQuery, staleTime 1h
    └── components/
        └── AcoesUniverseContent.tsx           # useMemo filter, sort, pagination
```

### Pattern 1: Migration with SQLite Dialect Gate (from Phase 20)
**What:** `op.add_column` for simple nullable column — no RLS, no index needed.
**When to use:** Adding a nullable column to a global table (no RLS = no `if dialect.name == "postgresql"` needed for the column itself).

```python
# Source: backend/alembic/versions/0023_add_swing_trade_operations.py (adapted)
revision = "0024_add_variacao_12m_pct"
down_revision = "0023_add_swing_trade_operations"

def upgrade() -> None:
    op.add_column(
        "screener_snapshots",
        sa.Column("variacao_12m_pct", sa.Numeric(10, 6), nullable=True),
    )

def downgrade() -> None:
    op.drop_column("screener_snapshots", "variacao_12m_pct")
```

NOTE: No dialect gate needed here — `op.add_column` works on both SQLite (for tests) and PostgreSQL. The dialect gate in 0023 was only for RLS policy SQL. This migration is simpler.

### Pattern 2: BrapiClient.fetch_fundamentals() Extension
**What:** Add `52WeekChange` extraction from `defaultKeyStatistics` in `_parse_response`.
**Key insight:** `defaultKeyStatistics` is already fetched (`modules=defaultKeyStatistics,financialData`). The field just needs to be extracted and returned.

```python
# Source: backend/app/modules/market_data/adapters/brapi.py (current _parse_response)
# ADD to _parse_response dict:
"variacao_12m": _extract(key_stats, "52WeekChange"),
# Full updated return:
return {
    "pl": (...),
    "pvp": _extract(key_stats, "priceToBook"),
    "dy": _extract(financial, "dividendYield"),
    "ev_ebitda": _extract(key_stats, "enterpriseToEbitda"),
    "variacao_12m": _extract(key_stats, "52WeekChange"),  # NEW
}
```

CONFIDENCE: MEDIUM — `52WeekChange` is a standard Yahoo Finance key (brapi wraps Yahoo). The field key name is verified by the fact that `defaultKeyStatistics` is already the correct module per existing code.

### Pattern 3: Celery Task Upsert Extension
**What:** Add `variacao_12m_pct` to the `row` dict and to the `set_()` in `_flush_batch`.

```python
# Source: backend/app/modules/market_universe/tasks.py (refresh_screener_universe)
# In the row dict (after line ~289):
row = {
    ...,
    "variacao_12m_pct": _safe_decimal(fund.get("variacao_12m")) if fund else None,  # NEW
}
# In _flush_batch set_() (after line ~241):
set_={
    ...,
    "variacao_12m_pct": stmt.excluded.variacao_12m_pct,  # NEW
}
```

### Pattern 4: GET /screener/universe Endpoint
**What:** New endpoint that returns all rows from latest snapshot — no server-side filtering, no pagination. Reuses `get_current_user` + `get_global_db` + `@limiter.limit("30/minute")`.
**Contrast with existing:** `/screener/acoes` does server-side filtering with limit/offset. The new `/screener/universe` dumps the full table (latest date) and lets the frontend filter.

```python
# Source: backend/app/modules/screener_v2/router.py (pattern from screener_acoes)
@router.get(
    "/universe",
    response_model=ScreenerUniverseResponse,
    summary="Universo completo de ações B3 (snapshot diário, sem filtros)",
    tags=["screener-v2"],
)
@limiter.limit("30/minute")
async def screener_universe(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> ScreenerUniverseResponse:
    rows = await query_screener_universe(db=global_db)
    return ScreenerUniverseResponse(results=rows)
```

### Pattern 5: query_screener_universe() Service Function
**What:** Simpler than `query_acoes()` — no filter params, no pagination, just latest-date rows ordered by market_cap desc.

```python
# Source: backend/app/modules/screener_v2/service.py (pattern from query_acoes)
async def query_screener_universe(db: AsyncSession) -> list[ScreenerUniverseRow]:
    latest_date_result = await db.execute(
        select(func.max(ScreenerSnapshot.snapshot_date))
    )
    latest_date = latest_date_result.scalar_one_or_none()
    if latest_date is None:
        return []

    stmt = (
        select(ScreenerSnapshot)
        .where(ScreenerSnapshot.snapshot_date == latest_date)
        .order_by(ScreenerSnapshot.market_cap.desc().nullslast())
    )
    result = await db.execute(stmt)
    snapshots = result.scalars().all()

    return [
        ScreenerUniverseRow(
            ticker=s.ticker,
            short_name=s.short_name,
            sector=s.sector,
            regular_market_price=_safe_decimal(s.regular_market_price),
            variacao_12m_pct=_safe_decimal(s.variacao_12m_pct),
            dy=_safe_decimal(s.dy),
            pl=_safe_decimal(s.pl),
            market_cap=s.market_cap,
        )
        for s in snapshots
    ]
```

### Pattern 6: New Pydantic Schemas
**What:** Two new schemas in `screener_v2/schemas.py`. Minimal — only the 8 fields needed per D-10.

```python
# Source: backend/app/modules/screener_v2/schemas.py (pattern from AcaoRow)
class ScreenerUniverseRow(BaseModel):
    ticker: str
    short_name: str | None
    sector: str | None
    regular_market_price: Decimal | None
    variacao_12m_pct: Decimal | None
    dy: Decimal | None
    pl: Decimal | None
    market_cap: int | None

class ScreenerUniverseResponse(BaseModel):
    disclaimer: str = CVM_DISCLAIMER
    results: list[ScreenerUniverseRow]
```

### Pattern 7: Frontend Hook — useAcoesUniverse
**What:** React Query hook fetching `/screener/universe` once with 1h staleTime. No params — full dataset, filter client-side.

```typescript
// Source: frontend/src/features/fii_screener/hooks/useFIIScreener.ts (pattern)
export function useAcoesUniverse() {
  return useQuery<AcoesUniverseResponse>({
    queryKey: ["acoes-universe"],
    queryFn: getAcoesUniverse,
    staleTime: 1000 * 60 * 60,  // 1h — data refreshed nightly
  });
}
```

### Pattern 8: Frontend useMemo Filter + Client-Side Sort
**What:** Filter and sort the full dataset in memory. Both applied in a single `useMemo` to avoid double-render.

```typescript
// Source: frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx (pattern)
const [sortCol, setSortCol] = useState<keyof AcoesUniverseRow | null>(null);
const [sortDir, setSortDir] = useState<"asc" | "desc">("desc");
const [minDy, setMinDy] = useState("");
const [maxPl, setMaxPl] = useState("");
const [sectorFilter, setSectorFilter] = useState("");
const [mcapTier, setMcapTier] = useState<"" | "small" | "mid" | "large">("");

const filtered = useMemo(() => {
  if (!data?.results) return [];
  let rows = data.results.filter((row) => {
    if (minDy && row.dy !== null) {
      if (parseFloat(row.dy) * 100 < parseFloat(minDy)) return false;
    }
    if (maxPl && row.pl !== null) {
      if (parseFloat(row.pl) > parseFloat(maxPl)) return false;
    }
    if (sectorFilter && row.sector !== sectorFilter) return false;
    if (mcapTier) {
      const mc = row.market_cap ?? 0;
      if (mcapTier === "small" && mc >= 2_000_000_000) return false;
      if (mcapTier === "mid" && (mc < 2_000_000_000 || mc >= 10_000_000_000)) return false;
      if (mcapTier === "large" && mc < 10_000_000_000) return false;
    }
    return true;
  });
  if (sortCol) {
    rows = [...rows].sort((a, b) => {
      const av = a[sortCol] ?? null;
      const bv = b[sortCol] ?? null;
      if (av === null) return 1;
      if (bv === null) return -1;
      const cmp = av < bv ? -1 : av > bv ? 1 : 0;
      return sortDir === "asc" ? cmp : -cmp;
    });
  }
  return rows;
}, [data, minDy, maxPl, sectorFilter, mcapTier, sortCol, sortDir]);
```

### Pattern 9: Client-Side Pagination
**What:** Slice the `filtered` array. Mirrors `AcoesScreenerContent` pagination exactly.

```typescript
// Source: frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx
const PAGE_SIZE = 50;
const [page, setPage] = useState(0);
const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
const pageRows = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
// Reset page to 0 when filters change
```

### Pattern 10: Page Layout
**What:** Exact structure from `frontend/app/fii/screener/page.tsx`.

```typescript
// Source: frontend/app/fii/screener/page.tsx
import { AppNav } from "@/components/AppNav";
import { AcoesUniverseContent } from "@/features/acoes_screener/components/AcoesUniverseContent";

export default function AcoesScreenerPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <div className="space-y-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Screener de Ações</h1>
              <p className="text-sm text-gray-500 mt-1">
                Explore o universo completo de ações B3 — filtros por fundamentos
              </p>
            </div>
            <AcoesUniverseContent />
          </div>
        </div>
      </main>
    </>
  );
}
```

### Anti-Patterns to Avoid
- **Server-side filtering for universe endpoint:** The universe endpoint must return ALL rows. The existing `/screener/acoes` does server-side filtering — that is the old pattern. DO NOT add Query params to `/screener/universe`.
- **Creating a new router file:** Add `/universe` to the existing `screener_v2/router.py`. No new router file needed. `main.py` already mounts `screener_v2_router` at `/screener`.
- **Touching `main.py`:** The existing `screener_v2_router` is already mounted. No change to `main.py` needed.
- **Resetting `page` state inside `useMemo`:** Side effects inside `useMemo` are forbidden. Reset page via `useEffect` watching filter state, or reset in each filter's `onChange` handler.
- **Using `segmentoBadge()` for sectors:** CONTEXT explicitly says sector should be plain text. There are too many B3 sectors for colored badges.
- **Hardcoding the sector list:** The sector values come from brapi's `/quote/list` endpoint and may not match the SECTORS array in `AcoesScreenerContent.tsx`. Use `SELECT DISTINCT sector FROM screener_snapshots` (Wave 0 task) to get the real list.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async SQLAlchemy query | Custom session management | `get_global_db` dependency (already imported in `router.py`) | Existing pattern; global table, no RLS |
| Safe decimal conversion | Custom try/except | `_safe_decimal()` from `service.py` | Already implemented, handles None/invalid |
| React Query cache | Custom useState + fetch | `useQuery` with `staleTime: 1h` | Prevents 900-ticker re-fetch on every filter change |
| BRL market cap formatting | Custom format function | `fmtBRL()` from `AcoesScreenerContent.tsx` — import or copy to `acoes_screener/utils.ts` | Already handles B/M/K formatting |
| Var. 12m% colored badge | New badge component | `changeBadge()` from `AcoesScreenerContent.tsx` — import or copy | Already handles +/- color logic |
| Generic number format | Custom toFixed wrapper | `fmt()` from `FIIScoredScreenerContent.tsx` or `AcoesScreenerContent.tsx` | Handles null → "—" fallback |
| Skeleton loading rows | Custom loading state | `Array.from({ length: 8 }).map(...)` pattern from `FIIScoredScreenerContent.tsx` | Established loading skeleton pattern |

**Key insight:** Three utility functions (`fmt`, `fmtBRL`, `changeBadge`) already exist in production. Either copy them to `acoes_screener/utils.ts` or import directly from `screener_v2` — do NOT rewrite them.

## Common Pitfalls

### Pitfall 1: Migration Head Mismatch
**What goes wrong:** Creating migration 0024 with `down_revision = "wrong_id"` — Alembic refuses to run.
**Why it happens:** The exact revision ID in `0023_add_swing_trade_operations.py` is `"0023_add_swing_trade_operations"` (the full string, not just "0023").
**How to avoid:** Read the `revision` field at the top of `0023_add_swing_trade_operations.py` and copy it verbatim as `down_revision` in 0024.
**Warning signs:** `alembic upgrade head` fails with "Target database is not up to date" or "Can't locate revision identified by".

### Pitfall 2: variacao_12m_pct Always NULL After Migration
**What goes wrong:** Migration runs, column exists, but all rows show `null` for `Var. 12m%`.
**Why it happens:** The Celery beat task (`refresh_screener_universe`) only runs Mon-Fri at 07:00 BRT. A newly-added column won't have data until the next scheduled run.
**How to avoid:** In testing, manually trigger `refresh_screener_universe.apply()` or seed test data with non-null `variacao_12m_pct`. The frontend must gracefully show "—" for null values (use `changeBadge()` which handles null).
**Warning signs:** All rows show "—" in `Var. 12m%` column — this is correct behavior day-1, not a bug.

### Pitfall 3: DY Display Off by 100x
**What goes wrong:** DY shows as "0.09%" instead of "9%".
**Why it happens:** `dy` is stored as decimal (0.09 = 9%). Must multiply by 100 in frontend.
**How to avoid:** In `useMemo` filter: `parseFloat(row.dy) * 100 < parseFloat(minDy)`. In display: `(parseFloat(row.dy) * 100).toFixed(2) + "%"`. Same convention confirmed in `FIIScoredScreenerContent.tsx` line 61.
**Warning signs:** A stock with obvious 9% DY shows as 0.09%.

### Pitfall 4: Page State Not Reset on Filter Change
**What goes wrong:** User is on page 5, applies a filter that returns 30 rows, but page shows empty because page 5 doesn't exist in 30 rows.
**Why it happens:** `page` state is not reset when filter state changes.
**How to avoid:** Reset `page` to 0 in every filter's `onChange` handler, OR compute `pageRows = filtered.slice(...)` and clamp page to 0 if `page * PAGE_SIZE >= filtered.length`.
**Warning signs:** Filter returns results count > 0 but table shows "nenhum ativo encontrado".

### Pitfall 5: Sort State vs. Filter State Interaction
**What goes wrong:** Sort is applied to `data.results` before filtering, so sorted order is lost when filters change.
**Why it happens:** Applying sort and filter in separate passes.
**How to avoid:** Apply both in a single `useMemo`: filter first, then sort the filtered result. The `filtered` variable is both filtered AND sorted. The dependency array includes all filter state AND sort state.
**Warning signs:** Sorting works but breaks after applying any filter.

### Pitfall 6: 52WeekChange Not in brapi Free Tier
**What goes wrong:** `fetch_fundamentals()` returns `None` for `variacao_12m` even after the code change.
**Why it happens:** brapi may not include `52WeekChange` in `defaultKeyStatistics` on the free/startup tier, or some tickers don't have 52-week history.
**How to avoid:** The column is designed as NULLABLE. NULL is acceptable. Log a debug message when `52WeekChange` is missing. Do NOT fail the entire upsert.
**Warning signs:** `variacao_12m_pct` is NULL for ALL tickers — check if `defaultKeyStatistics` is being returned at all (may need `?modules=defaultKeyStatistics` param confirmed — it already is).

### Pitfall 7: frontend/app/acoes/ Directory Does Not Exist
**What goes wrong:** Creating `frontend/app/acoes/screener/page.tsx` fails or is placed in wrong location.
**Why it happens:** The `acoes/` directory does not exist today (confirmed via `ls`).
**How to avoid:** Create both `frontend/app/acoes/` and `frontend/app/acoes/screener/` directories before writing `page.tsx`. The planner must include directory creation as an explicit step.
**Warning signs:** `page.tsx` created but route 404s in Next.js.

## Code Examples

### Confirmed Exact Patterns

#### 1. DY filter comparison (decimal storage)
```typescript
// Source: frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx line 110-113
// dy_12m is stored as decimal (0.09 = 9%), convert to % for comparison
if (!isNaN(minDy) && rowDy * 100 < minDy) return false;
```

#### 2. Market Cap format
```typescript
// Source: frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx lines 20-25
function fmtBRL(val: number | null): string {
  if (val === null) return "—";
  if (val >= 1_000_000_000) return `R$ ${(val / 1_000_000_000).toFixed(1)}B`;
  if (val >= 1_000_000) return `R$ ${(val / 1_000_000).toFixed(0)}M`;
  return `R$ ${val.toLocaleString("pt-BR")}`;
}
```

#### 3. Colored change badge
```typescript
// Source: frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx lines 27-33
function changeBadge(val: string | null) {
  if (!val) return <span className="text-gray-400">—</span>;
  const n = parseFloat(val);
  if (isNaN(n)) return <span className="text-gray-400">—</span>;
  const color = n >= 0 ? "text-emerald-600" : "text-red-500";
  return <span className={`font-medium ${color}`}>{n >= 0 ? "+" : ""}{n.toFixed(2)}%</span>;
}
```

#### 4. Pagination (server-side model — adapt to client-side)
```typescript
// Source: frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx lines 77-79
const total = data?.total ?? 0;
const currentPage = Math.floor(offset / PAGE_SIZE) + 1;
const totalPages = Math.ceil(total / PAGE_SIZE);
// For client-side: replace `total` with `filtered.length`, use `page` instead of offset
```

#### 5. Skeleton loading rows
```typescript
// Source: frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx lines 212-220
{isLoading
  ? Array.from({ length: 8 }).map((_, i) => (
      <tr key={i} className="border-b border-gray-100">
        {Array.from({ length: 8 }).map((_, j) => (  // 8 cols for ações universe
          <td key={j} className="py-3 px-4">
            <div className="h-4 bg-gray-100 rounded animate-pulse" />
          </td>
        ))}
      </tr>
    ))
  : pageRows.map((row) => <AcoesUniverseRow key={row.ticker} row={row} />)}
```

#### 6. Ticker cell with short_name beneath
```typescript
// Source: frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx lines 74-84
<td className="py-3 px-4">
  <Link href={`/stock/${row.ticker}`}
    className="font-mono font-bold text-sm text-blue-600 hover:underline">
    {row.ticker}
  </Link>
  {row.short_name && (
    <div className="text-xs text-gray-500 truncate max-w-[140px]">
      {row.short_name}
    </div>
  )}
</td>
```

## State of the Art

| Old Approach | Current Approach | Notes |
|--------------|------------------|-------|
| `/screener/acoes` server-side filter + pagination | `/screener/universe` full dump + client-side filter | Phase 21 pattern — ~900 items fits in browser |
| Hardcoded SECTORS list in AcoesScreenerContent | Dynamic from DB query | CONTEXT says to query `SELECT DISTINCT sector` before hardcoding |
| `regular_market_change_percent` (daily % only) | + `variacao_12m_pct` (52-week %) | Migration 0024 adds the new column |

**Current `screener_snapshots` columns confirmed (from models.py):**
- `id`, `ticker`, `snapshot_date`, `short_name`, `sector`
- `regular_market_price`, `regular_market_change_percent`, `regular_market_volume`
- `market_cap`, `pl`, `pvp`, `dy`, `ev_ebitda`, `created_at`
- **MISSING:** `variacao_12m_pct` — added by Migration 0024

**Current `BrapiClient.fetch_fundamentals()` return keys confirmed:**
- `pl`, `pvp`, `dy`, `ev_ebitda`
- **MISSING:** `variacao_12m` — added by D-02

## Open Questions

1. **Exact 52WeekChange field name in brapi response**
   - What we know: `defaultKeyStatistics` module is already fetched; `52WeekChange` is the standard Yahoo Finance field name
   - What's unclear: Whether brapi renames it or passes it through as-is
   - Recommendation: Add extraction in `_parse_response`, run a test with a real ticker (e.g., PETR4) to verify the key name before committing; if key is absent, log at DEBUG level and return None (acceptable per D-03)

2. **Real sector values in production screener_snapshots**
   - What we know: `AcoesScreenerContent.tsx` has a hardcoded SECTORS list but it may not match actual DB values
   - What's unclear: Exact sector strings brapi uses (may be English like "Energy" or Portuguese like "Energia")
   - Recommendation: Wave 0 task — query `SELECT DISTINCT sector FROM screener_snapshots WHERE sector IS NOT NULL ORDER BY sector` on VPS and use those exact strings in the dropdown

3. **Performance of full 900-row fetch**
   - What we know: FII screener fetches ~400 rows fine; ações universe is ~900 rows
   - What's unclear: Response payload size (estimate ~200KB JSON for 900 rows × 8 fields)
   - Recommendation: No pagination on the endpoint; if response is slow, add `?limit=` escape hatch later. Target is <500ms per STATE.md.

## Validation Architecture

`nyquist_validation` is enabled per `.planning/config.json`.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend) + Playwright (E2E) |
| Config file | `backend/pytest.ini` or `backend/pyproject.toml` (existing) |
| Quick run command | `cd backend && pytest tests/test_screener_universe.py -x -q` |
| Full suite command | `cd backend && pytest -x -q` |
| E2E run command | `cd frontend && npx playwright test e2e/acoes-screener.spec.ts` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SCRA-01 | GET /screener/universe returns 8 fields per row | unit (pytest) | `pytest tests/test_screener_universe.py::test_universe_response_shape -x` | ❌ Wave 0 |
| SCRA-01 | variacao_12m_pct nullable — no error when NULL | unit (pytest) | `pytest tests/test_screener_universe.py::test_universe_allows_null_variacao -x` | ❌ Wave 0 |
| SCRA-01 | Column sort toggles asc/desc | unit (vitest or manual) | Manual — client-side sort has no backend test | Manual only |
| SCRA-02 | DY filter: row.dy*100 < minDy excluded | unit (pytest useMemo logic or vitest) | Manual browser test — filter logic is frontend-only | Manual only |
| SCRA-02 | Market cap tiers: small/mid/large boundaries correct | unit (pytest or vitest) | Manual — 2B/10B threshold in useMemo | Manual only |
| SCRA-03 | Click ticker navigates to /stock/[ticker] | E2E (Playwright) | `npx playwright test e2e/acoes-screener.spec.ts --grep "click ticker"` | ❌ Wave 0 |
| SCRA-04 | Pagination shows PAGE_SIZE=50 rows per page | E2E (Playwright) | `npx playwright test e2e/acoes-screener.spec.ts --grep "pagination"` | ❌ Wave 0 |
| all | /acoes/screener page loads without JS errors | E2E smoke (Playwright) | `npx playwright test e2e/acoes-screener.spec.ts --grep "loads"` | ❌ Wave 0 |
| all | Existing 257+ backend tests still pass | regression | `cd backend && pytest -x -q` | ✅ existing |
| all | Existing 72 Playwright tests still pass | regression | `cd frontend && npx playwright test` | ✅ existing |

### Backend Unit Tests Required (new file: `backend/tests/test_screener_universe.py`)

```python
# Test 1: endpoint returns ScreenerUniverseResponse shape
async def test_universe_endpoint_response_shape(client, auth_headers):
    resp = await client.get("/screener/universe", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert "disclaimer" in data
    # Each row has the 8 required fields
    if data["results"]:
        row = data["results"][0]
        for field in ["ticker", "short_name", "sector", "regular_market_price",
                      "variacao_12m_pct", "dy", "pl", "market_cap"]:
            assert field in row

# Test 2: null variacao_12m_pct does not cause 500
async def test_universe_allows_null_variacao(client, auth_headers, db_with_null_variacao):
    resp = await client.get("/screener/universe", headers=auth_headers)
    assert resp.status_code == 200

# Test 3: BrapiClient.fetch_fundamentals returns variacao_12m key
def test_fetch_fundamentals_includes_variacao_12m():
    from app.modules.market_data.adapters.brapi import BrapiClient
    client = BrapiClient(token="test")
    # Mock _get to return a fake response with 52WeekChange
    with patch.object(client, "_get") as mock_get:
        mock_get.return_value = {"results": [{"defaultKeyStatistics": {"52WeekChange": 0.15}}]}
        result = client.fetch_fundamentals("PETR4")
    assert "variacao_12m" in result
    assert result["variacao_12m"] == 0.15

# Test 4: refresh_screener_universe upsert includes variacao_12m_pct
def test_screener_universe_upsert_includes_variacao(fake_redis_sync):
    # Extend existing test_refresh_screener_universe_writes_db pattern
    # Verify the DB row dict contains "variacao_12m_pct" key
    ...
```

### Playwright E2E Tests Required (new file: `frontend/e2e/acoes-screener.spec.ts`)

```typescript
test.describe('Acoes Screener Universe', () => {
  test('/acoes/screener loads without errors', async ({ page }) => {
    await login(page);
    const jsErrors: string[] = [];
    page.on('pageerror', err => jsErrors.push(err.message));
    await page.goto('/acoes/screener');
    await page.waitForTimeout(5000);
    const critical = jsErrors.filter(e => !e.includes('ResizeObserver'));
    expect(critical).toHaveLength(0);
    const body = await page.locator('body').innerText();
    expect(body).not.toMatch(/application error/i);
  });

  test('table shows required columns', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(5000);
    const headers = await page.locator('th').allInnerTexts();
    const joined = headers.join(' ');
    expect(joined).toMatch(/Ticker|Ativo/i);
    expect(joined).toMatch(/Setor/i);
    expect(joined).toMatch(/Var\.|12m/i);
    expect(joined).toMatch(/DY/i);
    expect(joined).toMatch(/P\/L/i);
    expect(joined).toMatch(/Market Cap/i);
  });

  test('DY filter reduces row count', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(5000);
    const before = await page.locator('tbody tr').count();
    await page.locator('input[placeholder*="Ex: 5"], input[placeholder*="DY"]').first().fill('20');
    await page.waitForTimeout(500);
    const after = await page.locator('tbody tr').count();
    expect(after).toBeLessThanOrEqual(before);
  });

  test('click ticker navigates to /stock/[ticker]', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(5000);
    const firstTickerLink = page.locator('a[href^="/stock/"]').first();
    await expect(firstTickerLink).toBeVisible({ timeout: 5000 });
    await firstTickerLink.click();
    await page.waitForURL(/\/stock\/.+/, { timeout: 5000 });
    expect(page.url()).toMatch(/\/stock\//);
  });

  test('pagination next button works when more than 50 rows', async ({ page }) => {
    await login(page);
    await page.goto('/acoes/screener');
    await page.waitForTimeout(5000);
    const nextBtn = page.locator('button').filter({ hasText: /próxima|next/i }).first();
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
      await page.waitForTimeout(500);
      // Verify page counter changed
      const body = await page.locator('body').innerText();
      expect(body).toMatch(/Página 2/i);
    }
  });
});
```

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_screener_universe.py -x -q`
- **Per wave merge:** `cd backend && pytest -x -q` (full suite)
- **Phase gate:** Full backend suite + Playwright `acoes-screener.spec.ts` green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_screener_universe.py` — covers SCRA-01 backend shape + variacao_12m extraction
- [ ] `frontend/e2e/acoes-screener.spec.ts` — covers SCRA-01/02/03/04 E2E
- [ ] Directory creation: `frontend/app/acoes/screener/` does not exist yet — must be created before page.tsx
- [ ] Sector discovery SQL: `SELECT DISTINCT sector FROM screener_snapshots WHERE sector IS NOT NULL ORDER BY sector` — run on VPS to get real sector list for dropdown

## Sources

### Primary (HIGH confidence)
- `D:/claude-code/investiq/backend/app/modules/market_universe/models.py` — ScreenerSnapshot model, confirmed columns present/absent
- `D:/claude-code/investiq/backend/app/modules/screener_v2/router.py` — exact endpoint patterns, dependency injection
- `D:/claude-code/investiq/backend/app/modules/screener_v2/service.py` — query_acoes() pattern for new query_screener_universe()
- `D:/claude-code/investiq/backend/app/modules/screener_v2/schemas.py` — AcaoRow + CVM_DISCLAIMER patterns
- `D:/claude-code/investiq/backend/app/modules/market_data/adapters/brapi.py` — fetch_fundamentals() current state + _parse_response
- `D:/claude-code/investiq/backend/app/modules/market_universe/tasks.py` — _flush_batch upsert pattern + row dict structure
- `D:/claude-code/investiq/backend/alembic/versions/0023_add_swing_trade_operations.py` — migration pattern, confirmed head revision ID
- `D:/claude-code/investiq/frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx` — useMemo filter pattern, skeleton loading, segmento filter
- `D:/claude-code/investiq/frontend/src/features/screener_v2/components/AcoesScreenerContent.tsx` — changeBadge(), fmtBRL(), fmt(), DY decimal convention, pagination
- `D:/claude-code/investiq/frontend/app/fii/screener/page.tsx` — page layout pattern
- `D:/claude-code/investiq/frontend/src/features/fii_screener/hooks/useFIIScreener.ts` — useQuery staleTime pattern
- `D:/claude-code/investiq/frontend/src/features/fii_screener/api.ts` — apiClient call pattern
- `D:/claude-code/investiq/frontend/e2e/screener.spec.ts` — Playwright test patterns to extend

### Secondary (MEDIUM confidence)
- `D:/claude-code/investiq/.planning/phases/21-screener-de-acoes/21-CONTEXT.md` — locked decisions, specifics
- `D:/claude-code/investiq/.planning/STATE.md` — confirmed migration head 0023, test counts, deploy pattern

## Metadata

**Confidence breakdown:**
- Standard Stack: HIGH — all libraries already in use, no new dependencies
- Migration pattern: HIGH — copied from 0023 with sqlite dialect analysis
- BrapiClient `52WeekChange`: MEDIUM — standard Yahoo Finance field, but brapi tier behavior unconfirmed; column is nullable so failure is safe
- Architecture: HIGH — all patterns verified against production files
- Pitfalls: HIGH — identified from actual code gaps (missing column, missing directory, DY decimal)
- Validation tests: HIGH — patterns from existing test files

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable stack — 30-day window)
