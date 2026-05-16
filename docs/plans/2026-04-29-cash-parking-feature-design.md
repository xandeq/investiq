# Cash Parking Advisor — Design Doc

**Date:** 2026-04-29
**Author:** @xandeq (with Claude)
**Status:** Approved scope; ready for `writing-plans` to break into atomic tasks
**Related:** [InvestIQ memory: diax-crm-integration](../../../C:/Users/acq20/.claude/projects/d--claude-code-investiq/memory/diax-crm-integration.md), [DIAX memory: project_investiq-integration.md](../../../C:/Users/acq20/.claude/projects/D--claude-code-diax-crm/memory/project_investiq-integration.md)

---

## 1. Problem

User has cash parked at Santander conta-corrente / DIAX-tracked accounts and needs to know **where to park it for short windows** (often <30 days) with returns better than poupança and daily liquidity.

Current InvestIQ comparator/wizard hardcode `HOLDING_PERIODS = {"6m": 180, "1a": 365, "2a": 730, "5a": 1825}` — minimum 6 months, ignores **IOF regressivo** (which dominates returns under 30 days, eating up to 96% of the rendimento on day 1) and the **poupança aniversário rule** (rendimento only credits on the monthly anniversary — withdrawing 1 day before pays zero).

DIAX CRM owns the user's full cash flow (Income, Expense, RecurringTransaction, MonthlySimulation, CashFlowProjection) but InvestIQ has no read access to it, so it cannot recommend cash parking based on real upcoming bills.

## 2. Goal

Allow the user to ask InvestIQ "where should I park my available cash?" and get an automatic, ranked recommendation that:
- Pulls available cash + projected outflows from DIAX
- Computes net return (after IR regressivo + IOF regressivo) for each instrument
- Handles the poupança aniversário pegadinha
- Surfaces the recommendation in the Action Inbox + a dedicated page

## 3. Non-goals

- Not a multi-user/multi-tenant feature — single-user S2S integration with one DIAX instance
- Not a full personal-finance app — DIAX remains source of truth for cash flow
- No automated execution (no API to broker) — recommendation only
- No LCI/LCA in v1 (carência ≥ 90d makes them irrelevant for <30-day parking)
- No fundos DI by individual fund — only "Fundo DI 95% CDI sintético" as a class proxy

## 4. Architecture decision: pull from DIAX (Variant A — approved)

InvestIQ pulls cash flow projection from DIAX on-demand when user opens `/caixa` or the Action Inbox card. Both sides cache 1h in their own layer (DIAX `IMemoryCache`, InvestIQ Redis).

Rejected alternatives:
- **Pre-pull via Celery beat** — 24 useless calls/day, complexity not justified
- **Push via webhook** — cash flow is not time-critical; webhooks add idempotency/ordering complexity

## 5. Data flow

```
User opens InvestIQ /caixa or Action Inbox
        │
        ▼
InvestIQ /advisor/cash-parking (FastAPI)
        │  cache miss?
        ▼
InvestIQ DiaxClient.get_cash_flow_projection()
        │  HTTP GET, X-Integration-Key
        ▼
DIAX /api/v1/integrations/cash-flow-projection
        │  uses CashFlowProjectionService (existing)
        │  + PersonalControlSummary calc (existing)
        ▼
{ currentBalance, dailyProjection[], availableToInvest, nextBigOutflow }
        │
        ▼
InvestIQ CashParkingService:
        - Reads CDI/Selic from Redis market:macro:*
        - Computes holding_days = min(nextBigOutflow.date - today, 90)
        - For each instrument: gross_pct → IR (TaxEngine) → IOF (new IOFEngine) → poupança rule
        - Ranks by net return
        ▼
GET /advisor/cash-parking → JSON
        ▼
Frontend: ranked table + recommendation card
```

## 6. New components

### 6.1 DIAX side (.NET 8)

**File:** `api-core/src/Diax.Api/Controllers/V1/IntegrationsController.cs`
**Route:** `GET /api/v1/integrations/cash-flow-projection?fromDate=&toDate=`
**Auth:** `[AllowAnonymous]` + middleware/dependency check on `X-Integration-Key` header against `Integrations:InvestIQKey` config
**Tenant resolution:** `Integrations:DefaultUserId` (single-user)

**File:** `api-core/src/Diax.Application/Integrations/CashFlowProjectionIntegrationService.cs`
- Reuses existing `CashFlowProjectionService.ProjectDailyBalances(...)` — do NOT reimplement
- Reuses existing `PersonalControlSummary.availableToInvest` calculation logic
- DTO: `CashFlowProjectionResponse { currentBalance, dailyProjection[], availableToInvest, nextBigOutflow }`

**Config:** `appsettings.json`
```json
"Integrations": {
  "InvestIQKey": "<set in user-secrets / GH secret>",
  "DefaultUserId": "<guid>"
}
```

### 6.2 InvestIQ side — IOF engine (Python)

**File:** `backend/app/modules/market_universe/iof_engine.py`
- Implements Decreto 6.306/2007, Anexo (tabela regressiva 30 dias)
- API: `IOFEngine.rate_for_days(days: int) -> Decimal` returns IOF rate (0.0–0.96) on rendimento
- Day 1 → 0.96, Day 30+ → 0.0
- Tested with all 30 entries from official table

### 6.3 InvestIQ side — cash flow advisor module (Python)

**Path:** `backend/app/modules/cash_flow_advisor/`

```
cash_flow_advisor/
├── __init__.py
├── client.py       # DiaxClient — httpx async, X-Integration-Key, Redis cache 3600s
├── service.py      # CashParkingService.rank_options(...) — ranking logic
├── schemas.py      # Pydantic DTOs
└── router.py       # GET /advisor/cash-parking
```

**Endpoint:** `GET /advisor/cash-parking` (no params — pulls all from DIAX)
**Auth:** existing `get_current_user` (user JWT)
**Plan gate:** Pro tier (uses LLM for narrative? → no, pure deterministic; can be free)

**Decision:** Free tier — feature is high-utility and adds zero LLM cost.

**Instruments scored (v1):**
| Instrument | Source of gross rate | IR? | IOF? | Special rule |
|---|---|---|---|---|
| Tesouro Selic | `market:macro:selic` Redis | yes | yes | B3 0% custody up to R$10k position |
| CDB DI 100% CDI | `market:macro:cdi` Redis | yes | yes | — |
| CDB DI 102% CDI | 1.02 × CDI | yes | yes | — |
| CDB DI 110% CDI | 1.10 × CDI | yes | yes | "best case" reference |
| Fundo DI 95% CDI | 0.95 × CDI | yes | yes | come-cotas check (skip if redemption < come-cotas date) |
| Poupança | 0.7 × Selic + TR (when Selic > 8.5%) | no | no | **anniversary rule**: returns 0 if today + holding_days < anniversary date |

**Output schema:**
```python
class CashParkingRow(BaseModel):
    label: str
    gross_annual_pct: Decimal
    holding_days: int
    iof_pct: Decimal           # 0.0–0.96
    ir_pct: Decimal            # 0.0–0.225
    gross_value_brl: Decimal   # rendimento bruto sobre amount
    iof_value_brl: Decimal
    ir_value_brl: Decimal
    net_value_brl: Decimal
    net_pct: Decimal
    rank: int
    note: str | None           # "poupança não rende — antes do aniversário"
```

### 6.4 InvestIQ frontend (Next.js)

**Path:** `frontend/src/features/cash_flow_advisor/`
- `hooks/useCashParking.ts` — TanStack Query hook
- `components/CashParkingTable.tsx` — ranked table (similar visual to comparador)
- `components/CashParkingHero.tsx` — top recommendation card

**New page:** `frontend/src/app/caixa/page.tsx`

**Action Inbox integration:** new source in [advisor/service.py compute_inbox](../../backend/app/modules/advisor/service.py) returns a card when DIAX availableToInvest > R$ 1.000 AND best instrument net return > poupança net return.

## 7. Edge cases

| Case | Handling |
|---|---|
| DIAX unreachable / not configured | Return 503 with clear error; frontend shows "Configure DIAX integration to use this feature" |
| `availableToInvest` ≤ R$ 100 | Return empty result with note "valor disponível abaixo do mínimo" |
| `holding_days` ≤ 1 | Return empty — IOF eats everything |
| `holding_days` > 90 | Cap at 90 (suggest using `/comparador` for longer horizons) |
| Poupança anniversary rule | If `(today + holding_days) % 30 < days_to_anniversary`, return 0 with note |
| Fundo DI come-cotas (last business day of May/Nov) | Skip fund row if redemption < come-cotas date |
| CDI/Selic stale in Redis (> 7h via watchdog) | Show warning banner but still compute |

## 8. Testing strategy

**InvestIQ:**
- Unit: `IOFEngine` (30 entries from table + boundary cases)
- Unit: `CashParkingService` with mocked DIAX client + Redis (golden cases: 17d, 30d, 60d)
- Integration: `/advisor/cash-parking` with FastAPI TestClient + dependency overrides for DiaxClient
- E2E (manual): real DIAX → real InvestIQ on staging

**DIAX:**
- Unit: `CashFlowProjectionIntegrationService` with mocked repos
- Integration: `IntegrationsController` (with/without key, with/without config)

## 9. Rollout plan

1. **Phase 1** — DIAX endpoint + tests + deploy via `update-db.ps1` (no schema change) + GH Actions
2. **Phase 2** — InvestIQ `IOFEngine` + tests
3. **Phase 3** — InvestIQ `cash_flow_advisor` module + tests + Action Inbox integration
4. **Phase 4** — InvestIQ frontend `/caixa` page + Action Inbox card

Each phase commits independently. After Phase 1 deployed, configure `Integrations:InvestIQKey` symmetric to InvestIQ's `INTEGRATION_KEY`. Phases 2-4 can be merged behind a feature flag if needed (none planned for v1).

## 10. Configuration to add

**InvestIQ `~/.claude/.secrets.env`:**
```
DIAX_BASE_URL=https://api.diax-crm.com.br  # or local for dev
DIAX_INTEGRATION_KEY=<symmetric to DIAX's Integrations:InvestIQKey>
```

**InvestIQ `backend/app/core/config.py` settings:**
```python
DIAX_BASE_URL: str | None = None
DIAX_INTEGRATION_KEY: str | None = None
```

**DIAX `appsettings.Production.json` (via SmarterASP env vars `DIAX_*`):**
```
DIAX_Integrations__InvestIQKey=<value>
DIAX_Integrations__DefaultUserId=<user guid>
```

## 11. Estimated effort

| Phase | Hours |
|---|---|
| 1 — DIAX endpoint | 2h |
| 2 — IOF engine | 0.5h |
| 3 — Cash flow advisor module | 3-4h |
| 4 — Frontend | 1-2h |
| **Total** | **6.5-8.5h** |

## 12. Out of scope (future)

- LCI/LCA inclusion (relevant only for ≥ 90d)
- Real-broker rate marketplace integration (XP/BTG API)
- Multi-account routing ("aplicar X na XP, Y no Tesouro")
- Auto-execution (place order on broker)
- Tax simulation export to IR Helper
