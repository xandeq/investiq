---
phase: 21-screener-de-acoes
verified: 2026-04-12T15:00:00Z
status: passed
score: 11/11 must-haves verified
---

# Phase 21: Screener de Acoes — Verification Report

**Phase Goal:** Usuário pode explorar e filtrar o universo completo de ações brasileiras por fundamentos diretamente na plataforma
**Verified:** 2026-04-12
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | /acoes/screener page exists with 8-column sortable table | VERIFIED | `frontend/app/acoes/screener/page.tsx` exists; AcoesUniverseContent renders 7 `<th>` headers (Ticker+Nome merged in one cell per plan design decision, all 8 data fields present) |
| 2 | Client-side filters: DY min, P/L max, Setor dropdown, Market Cap buttons via useMemo | VERIFIED | AcoesUniverseContent.tsx line 74: `const filtered = useMemo(...)` with all 4 filter branches implemented; thresholds 2_000_000_000 and 10_000_000_000 confirmed |
| 3 | Ticker links navigate to /stock/[ticker] | VERIFIED | Line 362: `href={\`/stock/${row.ticker}\`}` via Next.js Link |
| 4 | Client-side pagination PAGE_SIZE=50 | VERIFIED | Line 7: `const PAGE_SIZE = 50`; lines 138-139: totalPages + pageRows slice |
| 5 | GET /screener/universe endpoint returns all tickers from latest snapshot | VERIFIED | router.py lines 122-140; service.py lines 367-399 with latest_date logic |
| 6 | variacao_12m_pct in DB pipeline (migration + model + brapi + Celery) | VERIFIED | All 4 files confirmed; brapi.py line 167 extracts "52WeekChange"; tasks.py lines 242+291 persist it |

**Score:** 6/6 truths verified

---

## Required Artifacts

### Plan 01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/alembic/versions/0024_add_variacao_12m_pct.py` | Migration adding variacao_12m_pct column | VERIFIED | Contains `op.add_column`, `revision="0024_add_variacao_12m_pct"`, `down_revision="0023_add_swing_trade_operations"` |
| `backend/app/modules/market_universe/models.py` | ScreenerSnapshot model with variacao_12m_pct | VERIFIED | Line 45: `variacao_12m_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 6), nullable=True)` |
| `backend/app/modules/market_data/adapters/brapi.py` | 52WeekChange extraction | VERIFIED | Line 167: `"variacao_12m": _extract(key_stats, "52WeekChange")` |
| `backend/app/modules/market_universe/tasks.py` | variacao_12m_pct in row dict and set_() | VERIFIED | Line 291 (row dict) and line 242 (set_ clause) both confirmed |

### Plan 02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/app/modules/screener_v2/schemas.py` | ScreenerUniverseRow and ScreenerUniverseResponse schemas | VERIFIED | Lines 81-98: both classes present with correct 8 fields |
| `backend/app/modules/screener_v2/service.py` | query_screener_universe async function | VERIFIED | Lines 367-399: full implementation with latest_date logic and market_cap ordering |
| `backend/app/modules/screener_v2/router.py` | GET /screener/universe endpoint | VERIFIED | Lines 122-140: endpoint with auth + 30/minute rate limit |
| `backend/tests/test_screener_universe.py` | 4 test functions | VERIFIED | 4 tests: auth 401, empty dataset, latest-snapshot-only, schema validation |

### Plan 03 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `frontend/app/acoes/screener/page.tsx` | Next.js page at /acoes/screener | VERIFIED | 34 lines; imports AppNav + AcoesUniverseContent; max-w-7xl container |
| `frontend/src/features/acoes_screener/types.ts` | AcoesUniverseRow TypeScript type | VERIFIED | 8-field interface: ticker, short_name, sector, regular_market_price, variacao_12m_pct, dy, pl, market_cap |
| `frontend/src/features/acoes_screener/api.ts` | getAcoesUniverse fetch function | VERIFIED | Calls `/screener/universe` via `apiClient` |
| `frontend/src/features/acoes_screener/hooks/useAcoesUniverse.ts` | React Query hook | VERIFIED | useQuery with queryKey `["acoes-universe"]`, staleTime 1h |
| `frontend/src/features/acoes_screener/components/AcoesUniverseContent.tsx` | Main screener component (150+ lines) | VERIFIED | 460 lines; contains useMemo, PAGE_SIZE=50, Link to /stock/[ticker], all 4 filter controls |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `page.tsx` | `AcoesUniverseContent` | component import | VERIFIED | Line 3: `import { AcoesUniverseContent } from "@/features/acoes_screener/components/AcoesUniverseContent"` |
| `AcoesUniverseContent.tsx` | `useAcoesUniverse` hook | hook call | VERIFIED | Line 56: `const { data, isLoading, isError, error } = useAcoesUniverse()` |
| `useAcoesUniverse.ts` | `/screener/universe` API | `getAcoesUniverse` | VERIFIED | api.ts: `apiClient<AcoesUniverseResponse>("/screener/universe")` |
| `AcoesUniverseContent.tsx` | `/stock/[ticker]` | Link href | VERIFIED | Line 362: `href={\`/stock/${row.ticker}\`}` |
| `router.py screener_universe()` | `service.py query_screener_universe()` | async function call | VERIFIED | Line 139: `rows = await query_screener_universe(db=global_db)` |
| `service.py query_screener_universe()` | ScreenerSnapshot model | SQLAlchemy select | VERIFIED | Lines 372-385: `select(ScreenerSnapshot)` with latest_date and market_cap ordering |
| `router.py` | `schemas.py` | response_model | VERIFIED | Line 124: `response_model=ScreenerUniverseResponse` |
| `brapi.py _parse_response()` | `tasks.py row dict` | `fund.get("variacao_12m")` | VERIFIED | tasks.py line 291 reads variacao_12m from brapi adapter output |
| `tasks.py _flush_batch set_()` | screener_snapshots table | `stmt.excluded.variacao_12m_pct` | VERIFIED | Line 242: `"variacao_12m_pct": stmt.excluded.variacao_12m_pct` |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|---------|
| SCRA-01 | 21-01, 21-02, 21-03 | Tabela com Ticker, Nome, Setor, Preco, Var.12m%, DY, P/L, Market Cap — ordenavel | SATISFIED | All 8 data fields present in table (Nome merged under Ticker per plan design; sortable headers for all 7 columns) |
| SCRA-02 | 21-03 | Filtros: DY min, P/L max, Setor dropdown, Market Cap (small/mid/large) via useMemo | SATISFIED | All 4 filters confirmed at lines 79-109 of AcoesUniverseContent.tsx |
| SCRA-03 | 21-03 | Click ticker -> /stock/[ticker] | SATISFIED | Line 362: `href={\`/stock/${row.ticker}\`}` via Next.js Link |
| SCRA-04 | 21-02, 21-03 | Paginacao suportada | SATISFIED | PAGE_SIZE=50, prev/next buttons, totalPages logic confirmed |

---

## Anti-Patterns Found

No blockers or warnings detected.

- `placeholder` appearances in AcoesUniverseContent.tsx (lines 196, 214): These are HTML input placeholder attributes (`placeholder="Ex: 5"`, `placeholder="Ex: 20"`), not stub indicators.
- No TODO/FIXME/XXX comments in any phase 21 files.
- No `return null` or empty implementation stubs.
- No hardcoded empty data arrays returned to the user.

---

## Human Verification Required

### 1. Visual layout at /acoes/screener

**Test:** Log in to InvestIQ, navigate to /acoes/screener
**Expected:** Table renders with 8 data fields (Nome visible below Ticker in same cell), filter bar with DY min input, P/L max input, Setor dropdown, and 3 Market Cap buttons (Small/Mid/Large)
**Why human:** Visual appearance and responsive layout cannot be verified programmatically

### 2. Client-side filter responsiveness

**Test:** Enter "5" in DY min field, select a sector, click "Large >10B"
**Expected:** Table updates instantly (no network call) — results count changes and only matching rows appear
**Why human:** useMemo behavior is verified in code but real-time UX feel requires manual check

### 3. Var. 12m% data population

**Test:** View screener table after a Celery `refresh_screener_universe` run
**Expected:** Var. 12m% column shows non-null values with green/red color badges for most tickers
**Why human:** Column exists in schema and pipeline is wired, but data only populates after Celery task runs with live brapi.dev data

---

## Gaps Summary

No gaps found. All 11 artifacts pass all three verification levels (exists, substantive, wired). All 4 requirement IDs (SCRA-01 through SCRA-04) are satisfied by concrete code evidence. The full data pipeline is wired end-to-end: brapi.dev 52WeekChange extraction -> Celery upsert -> screener_snapshots table -> GET /screener/universe -> React Query -> useMemo filter/sort -> paginated table -> /stock/[ticker] links.

One design note: SCRA-01 lists "Nome" as a separate column but the plan explicitly designed the Ticker cell to show `short_name` as a subtitle below the ticker link. All 8 required data fields are rendered to the user; the column structure is 7 visible `<th>` elements rather than 8. This was an intentional plan decision, not a gap.

---

_Verified: 2026-04-12T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
