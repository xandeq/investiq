# Phase 19: Opportunity Detector Page — Research

**Researched:** 2026-04-04
**Domain:** FastAPI backend (new router + SQLAlchemy model + Alembic migration) + Next.js 15 frontend page (React Query + client-side filters)
**Confidence:** HIGH — all findings from direct code inspection of the live codebase

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OPDET-01 | Usuário acessa /opportunity-detector e vê lista de oportunidades detectadas com histórico, filtros e possibilidade de marcar como acompanhada | Backend: new `detected_opportunities` table + `GET /opportunity-detector/history` + `PATCH /opportunity-detector/{id}/follow` endpoints; Frontend: new page at `/opportunity-detector` + `OpportunityDetectorContent` component with type/period filters |
</phase_requirements>

---

## Summary

Phase 19 adds persistence and a frontend page for opportunities that the existing Opportunity Detector scanner already detects and dispatches. The scanner (`scanner.py`) currently detects drops in stocks, crypto, and Tesouro Direto rates via Celery Beat tasks, runs them through a 4-agent AI pipeline (`analyzer.py`), and dispatches alerts via Telegram + email + in-app insight (`alert_engine.py`). What is missing is a dedicated DB table for opportunity history and an API + frontend page to surface this history.

The backend work is purely additive: create a new `detected_opportunities` table (migration 0022), hook the `dispatch_opportunity` function to persist before dispatching, add a new `opportunity_detector` module with router + schemas, and register it in `main.py`. The frontend follows the identical pattern established in Phase 17 (`/fii/screener` page): a `page.tsx` shell, a `features/opportunity_detector/` feature directory with api.ts + types.ts + hooks + a client component with filters using `useMemo`.

The critical design decision is where to persist: the `dispatch_opportunity` call in `alert_engine.py` is the single choke point — all three scanner tasks call it. Adding a `save_opportunity_to_db` call inside `dispatch_opportunity` ensures every detected opportunity is persisted regardless of asset type.

**Primary recommendation:** Add `detected_opportunities` global table (no tenant_id — admin-only page), persist in `dispatch_opportunity`, expose `GET /opportunity-detector/history` with `?type=` and `?days=` query params, add `PATCH /opportunity-detector/{id}/follow` for marking, protect `/opportunity-detector` in middleware PROTECTED_PATHS.

---

## Section 1: Opportunity Detector Backend — Current State

**File:** `backend/app/modules/opportunity_detector/`

### What Already Exists

| File | Purpose |
|------|---------|
| `scanner.py` | 3 Celery Beat tasks: `scan_acoes_opportunities`, `scan_crypto_opportunities`, `scan_fixed_income_opportunities` |
| `analyzer.py` | `OpportunityReport` dataclass + `run_analysis()` 4-agent pipeline |
| `alert_engine.py` | `dispatch_opportunity(report)` — calls Telegram + email + `save_in_app_insight()` |
| `config.py` | Thresholds, asset lists, `TELEGRAM_CHAT_ID = "721438452"` (hardcoded default) |
| `agents/` | `cause.py`, `fundamentals.py`, `risk.py`, `recommendation.py` — AI agents |

### OpportunityReport Fields (the data generated per detection)

```python
@dataclass
class OpportunityReport:
    ticker: str           # e.g. "VALE3", "BTCUSDT", "Tesouro IPCA+ 2035"
    asset_type: str       # "acao" | "crypto" | "renda_fixa"
    drop_pct: float       # e.g. -22.0 (negative = drop; 0.0 for renda_fixa)
    period: str           # "diario" | "semanal" | "renda_fixa"
    current_price: float  # market price at detection time
    currency: str         # "BRL" | "USD"
    cause: CauseResult    # category, is_systemic, explanation, confidence
    fundamentals: FundamentalsResult  # quality, summary
    risk: RiskResult      # level ("baixo"|"medio"|"alto"|"evitar"), is_opportunity, rationale
    recommendation: Optional[RecommendationResult]  # suggested_amount_brl, target_upside_pct, timeframe_days, stop_loss_pct, action_summary
```

### Telegram Message Content (what the page must mirror)

The `alert_message()` method produces:
- Ticker + drop percentage + period
- Current price (R$ or US$)
- Cause explanation
- Fundamentals summary (if available)
- Risk level + rationale
- Recommendation suggestion (if `is_opportunity=True`): suggested amount BRL, target upside %, timeframe days, stop-loss %

### Dispatch Entry Point

`dispatch_opportunity(report)` in `alert_engine.py` is called by all three scanner tasks after deduplication. This is the correct place to add persistence — it already has access to the full `OpportunityReport`.

### What Does NOT Exist Yet

- A `detected_opportunities` DB table (no model, no migration)
- Any FastAPI router for `opportunity-detector`
- No existing router in `main.py` for this module

---

## Section 2: DB Patterns

### Migration Numbering

Latest migration: `0021_add_fii_score_columns` (down_revision: `0020_add_analysis_tables`).
Phase 19 migration must be: `0022_add_detected_opportunities`.

### Migration File Pattern (from 0021)

```python
# File: backend/alembic/versions/0022_add_detected_opportunities.py
"""add_detected_opportunities

Revision ID: 0022_add_detected_opportunities
Revises: 0021_add_fii_score_columns
Create Date: 2026-04-04
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_add_detected_opportunities"
down_revision = "0021_add_fii_score_columns"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table(
        "detected_opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("asset_type", sa.String(20), nullable=False),
        sa.Column("drop_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("period", sa.String(20), nullable=False),
        sa.Column("current_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("currency", sa.String(5), nullable=False),
        sa.Column("risk_level", sa.String(20), nullable=True),
        sa.Column("is_opportunity", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("cause_category", sa.String(50), nullable=True),
        sa.Column("cause_explanation", sa.Text, nullable=True),
        sa.Column("risk_rationale", sa.Text, nullable=True),
        sa.Column("recommended_amount_brl", sa.Numeric(12, 2), nullable=True),
        sa.Column("target_upside_pct", sa.Numeric(8, 2), nullable=True),
        sa.Column("telegram_message", sa.Text, nullable=True),
        sa.Column("followed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_detected_opportunities_ticker", "detected_opportunities", ["ticker"])
    op.create_index("ix_detected_opportunities_asset_type", "detected_opportunities", ["asset_type"])
    op.create_index("ix_detected_opportunities_detected_at", "detected_opportunities", ["detected_at"])

def downgrade() -> None:
    op.drop_table("detected_opportunities")
```

### SQLAlchemy Model Pattern (from AnalysisJob / FIIMetadata)

- Use `Mapped` + `mapped_column` (SQLAlchemy 2.x declarative style)
- Inherit from `app.modules.auth.models.Base`
- `id` = `String(36)` with `default=lambda: str(uuid.uuid4())`
- Global table = no `tenant_id` (same as `FIIMetadata`, `ScreenerSnapshot`)
- Use `get_global_db` dependency in the router (NOT `get_authed_db`)

### Global vs Tenant Decision

The detected opportunities are admin-level data (Phase 1 design in `alert_engine.py`). The existing `save_in_app_insight()` saves to `user_insights` with a hardcoded admin `tenant_id`. Phase 19 should store to a global table (no `tenant_id`) and the frontend page is admin-only. This is consistent with the "Phase 1: single destination" comment in `alert_engine.py`.

---

## Section 3: FastAPI Router Pattern

### How to Add a New Router (from main.py)

```python
# In main.py — add import:
from app.modules.opportunity_detector.router import router as opportunity_detector_router

# Add registration:
# Phase 19: Opportunity Detector history API
app.include_router(opportunity_detector_router, prefix="/opportunity-detector", tags=["opportunity-detector"])
```

### Router Pattern (from fii_screener/router.py — closest match)

```python
# backend/app/modules/opportunity_detector/router.py
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_global_db
from app.core.limiter import limiter
from app.core.security import get_current_user
from app.modules.opportunity_detector.models import DetectedOpportunity
from app.modules.opportunity_detector.schemas import OpportunityHistoryResponse

router = APIRouter()

@router.get("/history", response_model=OpportunityHistoryResponse, tags=["opportunity-detector"])
@limiter.limit("30/minute")
async def get_opportunity_history(
    request: Request,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
    asset_type: str | None = Query(default=None),
    days: int = Query(default=30, ge=1, le=365),
) -> OpportunityHistoryResponse:
    ...

@router.patch("/{opportunity_id}/follow", tags=["opportunity-detector"])
async def mark_as_followed(
    opportunity_id: str,
    current_user: dict = Depends(get_current_user),
    global_db: AsyncSession = Depends(get_global_db),
) -> dict:
    ...
```

### Auth Pattern

All endpoints use `current_user: dict = Depends(get_current_user)` — this validates the JWT and extracts `user_id` / `tenant_id`. No additional plan gate needed (history is informational). `get_global_db` bypasses RLS since `detected_opportunities` is a global table.

### Rate Limiter Pattern

Always import `from app.core.limiter import limiter` and decorate with `@limiter.limit("30/minute")` for GET endpoints. The `request: Request` parameter is required when using the limiter.

---

## Section 4: Frontend Page Pattern (Phase 17/18)

### Established Pattern

**Page file location:** `frontend/app/{route}/page.tsx` — this is the Next.js App Router root. Note: Next.js appDir is at `frontend/app/` (NOT `frontend/src/app/`). This was confirmed in STATE.md decisions.

**Feature directory location:** `frontend/src/features/{feature_name}/` — contains `api.ts`, `types.ts`, `hooks/`, `components/`.

### Page Shell (from /fii/screener/page.tsx)

```tsx
// frontend/app/opportunity-detector/page.tsx
import type { Metadata } from "next";
import { AppNav } from "@/components/AppNav";
import { OpportunityDetectorContent } from "@/features/opportunity_detector/components/OpportunityDetectorContent";

export const metadata: Metadata = {
  title: "Oportunidades Detectadas — InvestIQ",
  description: "Histórico de oportunidades detectadas pelo scanner automático",
};

export default function OpportunityDetectorPage() {
  return (
    <>
      <AppNav />
      <main className="min-h-screen bg-background">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          <OpportunityDetectorContent />
        </div>
      </main>
    </>
  );
}
```

### API Client Pattern (from fii_screener/api.ts)

```ts
// src/features/opportunity_detector/api.ts
import { apiClient } from "@/lib/api-client";
import type { OpportunityHistoryResponse } from "./types";

export async function getOpportunityHistory(params?: {
  asset_type?: string;
  days?: number;
}): Promise<OpportunityHistoryResponse> {
  const qs = new URLSearchParams();
  if (params?.asset_type) qs.set("asset_type", params.asset_type);
  if (params?.days) qs.set("days", String(params.days));
  return apiClient<OpportunityHistoryResponse>(`/opportunity-detector/history?${qs}`);
}

export async function markAsFollowed(id: string): Promise<void> {
  return apiClient(`/opportunity-detector/${id}/follow`, { method: "PATCH" });
}
```

### React Query Hook Pattern (from useFIIScreener.ts)

```ts
// src/features/opportunity_detector/hooks/useOpportunityHistory.ts
import { useQuery } from "@tanstack/react-query";
import { getOpportunityHistory } from "../api";

export function useOpportunityHistory(filters: { asset_type?: string; days?: number }) {
  return useQuery({
    queryKey: ["opportunity-history", filters],
    queryFn: () => getOpportunityHistory(filters),
    staleTime: 1000 * 60 * 5, // 5min — opportunities are near-realtime
  });
}
```

### Client Component with Filters Pattern (from FIIScoredScreenerContent.tsx)

The Phase 17 screener component pattern to replicate:
- `"use client"` directive at top
- `useState` for filter values (`assetTypeFilter`, `periodFilter`, `daysFilter`)
- `useMemo` for client-side filtering (avoids API roundtrips for type/period)
- Server-side `days` param (affects how much history to load — call API with this)
- Loading skeleton: `Array.from({ length: 8 }).map(...)` with `animate-pulse` divs
- Error state: `rounded-lg bg-red-50 border border-red-100` div
- Empty state: centered `text-sm text-gray-500` in table cell

---

## Section 5: Auth / PROTECTED_PATHS

### Current PROTECTED_PATHS (middleware.ts)

```ts
const PROTECTED_PATHS = ["/dashboard", "/portfolio", "/analysis", "/stock"];
```

**Action required:** Add `"/opportunity-detector"` to PROTECTED_PATHS in `frontend/middleware.ts`.

### How Auth Works

Middleware checks for `access_token` cookie. If missing, redirects to `/login?redirect={pathname}`. Backend enforces actual token validity on every API call via `Depends(get_current_user)`.

**Note from middleware.ts comments:** Middleware-only auth is intentionally insufficient (defense-in-depth). The backend's JWT validation is the real gate. The middleware only provides UX redirect.

### Adding Protected Path

```ts
// frontend/middleware.ts — change:
const PROTECTED_PATHS = ["/dashboard", "/portfolio", "/analysis", "/stock", "/fii", "/opportunity-detector"];
```

Note: `/fii` is also not in current PROTECTED_PATHS despite being a protected feature. Both should be added together in Phase 19 (low-risk addition).

---

## Section 6: Reusable Components

### From Phase 17 Screener (HIGH reuse potential)

| Component | Location | Reuse in Phase 19 |
|-----------|----------|--------------------|
| Filter bar layout | `FIIScoredScreenerContent.tsx` lines 133–174 | Identical layout: `grid grid-cols-1 sm:grid-cols-3 gap-3` with `select` + `input` + clear button |
| Loading skeleton | Lines 212–222 | Same `animate-pulse` pattern for table rows |
| Error state | Lines 189–193 | Same `bg-red-50` div |
| Empty state | Lines 225–233 | Same `colSpan` centered text |
| Table structure | Lines 196–239 | Similar `rounded-lg border` white card with `overflow-x-auto` |
| `fmt()` helper | Lines 22–27 | Direct copy for numeric formatting |

### From Phase 18 Detail Page

| Component | Location | Reuse in Phase 19 |
|-----------|----------|--------------------|
| `FIIAnalysisCard` | `src/features/fii_detail/components/FIIAnalysisCard.tsx` | Risk level badge pattern (baixo/medio/alto/evitar color coding) |
| KPICard pattern | `FIIDetailContent.tsx` lines 75+ | For showing drop %, risk level, suggested amount in opportunity cards |

### AppNav Component

`@/components/AppNav` — import as-is in the page shell. No changes needed.

### Tailwind Color Map for Risk Levels

From `alert_engine.py` risk levels → badge colors (establish in Phase 19):

```tsx
const RISK_COLORS = {
  baixo: "bg-green-100 text-green-700",
  medio: "bg-yellow-100 text-yellow-700",
  alto: "bg-red-100 text-red-700",
  evitar: "bg-gray-900 text-white",
};
```

---

## Section 7: Implementation Recommendations

### Backend — Model

Create `backend/app/modules/opportunity_detector/models.py`:

```python
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from app.modules.auth.models import Base
import uuid
from datetime import datetime, timezone

class DetectedOpportunity(Base):
    __tablename__ = "detected_opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(20), nullable=False)  # acao|crypto|renda_fixa
    drop_pct: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    period: Mapped[str] = mapped_column(String(20), nullable=False)  # diario|semanal|renda_fixa
    current_price: Mapped[float] = mapped_column(Numeric(18, 6), nullable=False)
    currency: Mapped[str] = mapped_column(String(5), nullable=False)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_opportunity: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    cause_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cause_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    recommended_amount_brl: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    target_upside_pct: Mapped[float | None] = mapped_column(Numeric(8, 2), nullable=True)
    telegram_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    followed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
```

### Backend — Persistence Hook

Modify `alert_engine.py`'s `dispatch_opportunity()` to call `save_opportunity_to_db(report)` BEFORE dispatching to Telegram/email. Use `get_superuser_sync_db_session` (same pattern as `save_in_app_insight`).

```python
def save_opportunity_to_db(report) -> bool:
    """Persist detected opportunity to detected_opportunities table."""
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.opportunity_detector.models import DetectedOpportunity
        with get_superuser_sync_db_session() as session:
            opp = DetectedOpportunity(
                ticker=report.ticker,
                asset_type=report.asset_type,
                drop_pct=report.drop_pct,
                period=report.period,
                current_price=report.current_price,
                currency=report.currency,
                risk_level=report.risk.level if report.risk else None,
                is_opportunity=report.risk.is_opportunity if report.risk else False,
                cause_category=report.cause.category if report.cause else None,
                cause_explanation=report.cause.explanation if report.cause else None,
                risk_rationale=report.risk.rationale if report.risk else None,
                recommended_amount_brl=report.recommendation.suggested_amount_brl if report.recommendation else None,
                target_upside_pct=report.recommendation.target_upside_pct if report.recommendation else None,
                telegram_message=report.alert_message(),
                followed=False,
                detected_at=datetime.now(timezone.utc),
            )
            session.add(opp)
            session.commit()
        return True
    except Exception as exc:
        logger.error("save_opportunity_to_db failed: %s", exc)
        return False
```

### Backend — API Shape

```
GET /opportunity-detector/history
  Query params:
    - asset_type: str (optional) — "acao"|"crypto"|"renda_fixa"
    - days: int (default=30, max=365)
  Response:
    {
      "total": int,
      "results": [
        {
          "id": "uuid",
          "ticker": "VALE3",
          "asset_type": "acao",
          "drop_pct": -22.0,
          "period": "diario",
          "current_price": 34.0,
          "currency": "BRL",
          "risk_level": "medio",
          "is_opportunity": true,
          "cause_category": "operacional",
          "cause_explanation": "...",
          "risk_rationale": "...",
          "recommended_amount_brl": 2000.0,
          "target_upside_pct": 18.0,
          "telegram_message": "...",
          "followed": false,
          "detected_at": "2026-04-04T10:00:00Z"
        }
      ]
    }

PATCH /opportunity-detector/{id}/follow
  Body: none (toggle — simple flip of `followed` flag)
  Response: { "id": "uuid", "followed": true }
```

### Frontend — Component Tree

```
app/opportunity-detector/page.tsx
  AppNav
  main > div.max-w-7xl
    OpportunityDetectorContent  [src/features/opportunity_detector/components/]
      FilterBar (asset_type select + period select + days select)
      StatusBar (count + last updated)
      OpportunityTable
        OpportunityRow x N
          RiskBadge (color-coded: baixo/medio/alto/evitar)
          FollowButton (toggle `followed` via useMutation)
```

### Frontend — Types

```ts
// src/features/opportunity_detector/types.ts
export interface OpportunityRow {
  id: string;
  ticker: string;
  asset_type: "acao" | "crypto" | "renda_fixa";
  drop_pct: number;
  period: string;
  current_price: number;
  currency: "BRL" | "USD";
  risk_level: string | null;
  is_opportunity: boolean;
  cause_category: string | null;
  cause_explanation: string | null;
  risk_rationale: string | null;
  recommended_amount_brl: number | null;
  target_upside_pct: number | null;
  telegram_message: string | null;
  followed: boolean;
  detected_at: string;  // ISO 8601
}

export interface OpportunityHistoryResponse {
  total: number;
  results: OpportunityRow[];
}
```

---

## Section 8: Validation Architecture

`nyquist_validation: true` in `.planning/config.json` — include full validation section.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio |
| Config file | `backend/pytest.ini` or `backend/pyproject.toml` |
| Quick run command | `cd D:/claude-code/investiq/backend && python -m pytest tests/test_opportunity_detector.py -x -q` |
| Full suite command | `cd D:/claude-code/investiq/backend && python -m pytest -x -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| OPDET-01a | `save_opportunity_to_db` persists all fields correctly | unit | `pytest tests/test_opportunity_detector_history.py::TestSaveOpportunityToDB -x` | Wave 0 |
| OPDET-01b | `GET /opportunity-detector/history` returns list sorted by detected_at desc | integration | `pytest tests/test_opportunity_detector_history.py::TestHistoryEndpoint -x` | Wave 0 |
| OPDET-01c | `GET /opportunity-detector/history?asset_type=acao` filters correctly | integration | `pytest tests/test_opportunity_detector_history.py::TestHistoryFilters -x` | Wave 0 |
| OPDET-01d | `GET /opportunity-detector/history?days=7` returns only last 7 days | integration | `pytest tests/test_opportunity_detector_history.py::TestHistoryDaysFilter -x` | Wave 0 |
| OPDET-01e | `PATCH /opportunity-detector/{id}/follow` toggles `followed` flag | integration | `pytest tests/test_opportunity_detector_history.py::TestFollowEndpoint -x` | Wave 0 |
| OPDET-01f | Unauthenticated request returns 401 | integration | `pytest tests/test_opportunity_detector_history.py::TestAuthRequired -x` | Wave 0 |

### Sampling Rate

- **Per task commit:** `python -m pytest tests/test_opportunity_detector.py tests/test_opportunity_detector_history.py -x -q`
- **Per wave merge:** `python -m pytest -x -q` (full suite, must stay 257+ passing)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_opportunity_detector_history.py` — covers OPDET-01a through OPDET-01f above (new file)
- [ ] `backend/app/modules/opportunity_detector/models.py` — `DetectedOpportunity` SQLAlchemy model
- [ ] `backend/app/modules/opportunity_detector/router.py` — new router file
- [ ] `backend/app/modules/opportunity_detector/schemas.py` — Pydantic schemas
- [ ] `backend/alembic/versions/0022_add_detected_opportunities.py` — migration

Existing test infrastructure in `conftest.py` (SQLite in-memory + fakeredis + JWT key injection) covers all new tests without changes.

---

## Common Pitfalls

### Pitfall 1: Using get_authed_db Instead of get_global_db

**What goes wrong:** `get_authed_db` injects `SET LOCAL rls.tenant_id` — `detected_opportunities` has no RLS policy, but the dependency imports `get_current_tenant_id` which may fail for admin users without a tenant.
**How to avoid:** Use `get_global_db` in the router (same as `fii_screener/router.py`).

### Pitfall 2: Forgetting to Add Route to PROTECTED_PATHS

**What goes wrong:** `/opportunity-detector` is accessible without login since middleware only protects listed paths.
**How to avoid:** Add to `PROTECTED_PATHS` array in `frontend/middleware.ts` BEFORE testing the frontend page.

### Pitfall 3: Using async SQLAlchemy in Celery Tasks

**What goes wrong:** `save_opportunity_to_db` will be called from Celery worker context (sync). Using `async with async_session_factory()` in a sync Celery context raises `RuntimeError: no running event loop`.
**How to avoid:** Use `get_superuser_sync_db_session` (same pattern as `save_in_app_insight` in `alert_engine.py`). This is a sync session factory already in use.

### Pitfall 4: Model Not Imported Before Alembic autogenerate

**What goes wrong:** If `DetectedOpportunity` model is not imported when `alembic/env.py` runs, the table won't appear in `alembic revision --autogenerate`.
**How to avoid:** Check `alembic/env.py` imports — add `from app.modules.opportunity_detector.models import DetectedOpportunity` or ensure the module's `__init__.py` exports the model. Alternatively, write the migration manually (Phase 17/18 pattern uses manual migrations).

### Pitfall 5: `drop_pct` is 0.0 for renda_fixa opportunities

**What goes wrong:** Frontend showing "caiu 0%" for fixed income opportunities looks wrong.
**How to avoid:** In the frontend component, detect `asset_type === "renda_fixa"` and render the `cause_explanation` field instead of drop percentage for these rows.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| No persistence | `DetectedOpportunity` table with `save_opportunity_to_db` hook | Enables history page |
| Alert-only (Telegram + email) | Alert + persist + in-app page | Closes the loop — user sees history in app |

---

## Sources

### Primary (HIGH confidence — direct code inspection)

- `D:/claude-code/investiq/backend/app/modules/opportunity_detector/scanner.py` — Celery tasks, detection logic
- `D:/claude-code/investiq/backend/app/modules/opportunity_detector/analyzer.py` — `OpportunityReport` dataclass fields
- `D:/claude-code/investiq/backend/app/modules/opportunity_detector/alert_engine.py` — dispatch pattern, `save_in_app_insight` sync DB pattern
- `D:/claude-code/investiq/backend/app/modules/fii_screener/router.py` — router pattern to replicate
- `D:/claude-code/investiq/backend/app/main.py` — how to register new router
- `D:/claude-code/investiq/backend/alembic/versions/0021_add_fii_score_columns.py` — migration numbering and pattern
- `D:/claude-code/investiq/backend/app/modules/analysis/models.py` — SQLAlchemy 2.x model pattern
- `D:/claude-code/investiq/backend/app/core/db.py` — `get_global_db` definition
- `D:/claude-code/investiq/frontend/middleware.ts` — PROTECTED_PATHS pattern
- `D:/claude-code/investiq/frontend/app/fii/screener/page.tsx` — page shell pattern
- `D:/claude-code/investiq/frontend/src/features/fii_screener/components/FIIScoredScreenerContent.tsx` — client component with filters pattern
- `D:/claude-code/investiq/frontend/src/features/fii_screener/api.ts` — API client pattern
- `D:/claude-code/investiq/frontend/src/features/fii_screener/hooks/useFIIScreener.ts` — React Query hook pattern
- `D:/claude-code/investiq/.planning/config.json` — `nyquist_validation: true`
- `D:/claude-code/investiq/backend/tests/test_opportunity_detector.py` — existing test patterns to extend
- `D:/claude-code/investiq/backend/tests/conftest.py` — test infrastructure (SQLite in-memory, fakeredis)

---

## Metadata

**Confidence breakdown:**
- Backend model/migration: HIGH — direct inspection of 0021 migration pattern
- Router/API shape: HIGH — direct inspection of fii_screener router
- Frontend page pattern: HIGH — direct inspection of Phase 17 screener components
- Middleware auth: HIGH — middleware.ts read directly
- Persistence hook placement: HIGH — alert_engine.py dispatch flow read directly

**Research date:** 2026-04-04
**Valid until:** 2026-05-04 (stable stack)
