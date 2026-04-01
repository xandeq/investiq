# Phase 12 Research: Foundation (Legal + Cost Control + Async Architecture)

**Project:** InvestIQ v1.2 — AI Analysis Engine
**Phase:** 12 (Foundation)
**Milestone Scope:** Phase 12–16 (v1.2 roadmap)
**Research Completed:** 2026-03-31
**Confidence:** HIGH (technical architecture) / MEDIUM (CVM regulatory specifics)

---

## Executive Summary

Phase 12 establishes the operational and legal foundation for v1.2's analysis features before any analysis code ships. The phase addresses four critical pitfalls identified in v1.2 research:

1. **Legal liability:** Unaudited AI analysis can trigger CVM adviser registration requirements if positioned as recommendations. Phase 12 includes a legal audit and CVM-compliant disclaimer architecture.

2. **Cost explosion:** Uncontrolled LLM requests scale from $2.5K/month (10 users) to $150K+/month (5K users) without per-user quotas. Phase 12 implements hard rate limiting and cost tracking.

3. **Data staleness:** Screener shows live quotes, analysis uses yesterday's fundamentals. Phase 12 mandates data versioning (`data_version_id` + `data_timestamp`) on all analyses.

4. **Async blocking:** Synchronous LLM calls in request handlers block other users. Phase 12 establishes async infrastructure (Celery job reuse from wizard) and provider fallback chains.

**Key Decisions:**
- Reuse wizard's Celery async pattern (return job ID immediately, WebSocket notification on completion)
- Multi-tier quotas: Free 0/month, Pro 50/month, Enterprise 500/month
- LLM provider chain: OpenRouter → Groq → fallback (tested in staging before production)
- Data versioning: All analyses tagged with source, timestamp, version ID (visible in API responses)
- Cost tracking: Per-analysis-type (DCF, earnings, dividend, sector) with ops dashboard

**Deliverables:**
1. Legal audit memo + CVM disclaimer component
2. Quota enforcement schema + rate limiting middleware
3. Data versioning system (schema + API layer)
4. Async job infrastructure (Celery tasks + tests)
5. LLM provider fallback testing suite
6. Cost tracking dashboard

---

## Section 1: Legal & Compliance Framework

### 1.1 CVM Registration Threshold

**Current Understanding (MEDIUM confidence):**
CVM Resolução 19/2021 (investment advice regulation) and Res. 30/2021 (suitability requirements) regulate who must register as an "adviser" (consultor). The line between "analysis" (educational) and "recommendation" (advice) is contextual:

- **Educational:** Presenting historical data, calculation methodologies, general principles without specific ticker suggestions
- **Recommendation:** Naming specific securities + justifying choice for specific person + ongoing monitoring

**InvestIQ's Position:**
- Analysis output: DCF valuation, earnings metrics, dividend analysis, peer comparisons — all presented as historical/calculated data
- LLM narrative: Plain-English interpretation of numbers, key risks, caveats — positioned as educational summary, not personalized advice
- Explicit disclaimer: "Análise informativa, não constitui recomendação de investimento pessoal (CVM Res. 19/2021)"

**Research Action (Phase 12):**
Consult a CVM compliance lawyer on the exact registration threshold:
1. **User count trigger:** At what user count does InvestIQ cross from "information tool" to "financial services provider"?
2. **Analysis positioning:** Is our "educational analysis" framing sufficient, or do we need explicit anti-recommendation language in the disclaimer?
3. **Documentation requirements:** What audit trail must we maintain (usage logs, disclaimers shown, etc.) to defend our educational positioning if challenged?

**Placeholder Disclaimer (to be reviewed by counsel):**

```
Análise informativa, não constitui recomendação de investimento pessoal.
O conteúdo é apresentado unicamente para fins educacionais e informativos,
baseado em dados históricos e metodologias de valuation amplamente reconhecidas.
Cada investidor tem sua própria situação financeira, tolerância ao risco e
objetivos — qualquer decisão de investimento deve considerar estes fatores
pessoais. Consulte um assessor financeiro registrado na CVM se precisar de
recomendação customizada. (CVM Res. 19/2021, Res. 30/2021)
```

### 1.2 Disclaimer Component Architecture

**Design Principle:**
Disclaimer must be visible *before* analysis results render — not hidden in TOS, not as a footnote after scrolling, not dynamically toggled off.

**Implementation Pattern (React component):**

```typescript
// frontend/src/components/analysis/AnalysisDisclaimer.tsx

export const AnalysisDisclaimer: React.FC = () => (
  <Alert className="mb-6 border-yellow-200 bg-yellow-50">
    <AlertTitle className="text-yellow-900 font-semibold">
      Análise Informativa - Não é Recomendação Pessoal
    </AlertTitle>
    <AlertDescription className="text-yellow-800 text-sm mt-2">
      <p>
        Este conteúdo é apresentado unicamente para fins educacionais e informativos,
        baseado em dados históricos e metodologias de valuation. Não constitui
        recomendação de investimento pessoal (CVM Res. 19/2021).
      </p>
      <p className="mt-2">
        Consulte um assessor financeiro registrado na CVM antes de tomar decisões
        de investimento com base nesta análise.
      </p>
    </AlertDescription>
  </Alert>
);

// Usage in detail page
<AnalysisDisclaimer />
<DCFValuationSection ticker={ticker} analysisId={analysisId} />
<EarningsSection ticker={ticker} analysisId={analysisId} />
// ... other sections
```

**Backend Enforcement:**
- API responses include `disclaimer_required: true` flag for analysis endpoints
- Frontend must render disclaimer before any analysis data is visible
- Integration test confirms disclaimer renders on page load (not behind scroll)

### 1.3 Data Attribution & Transparency

**Requirement:** Every analysis must show:
1. Data sources (BRAPI EOD, CVM/B3 filings, etc.)
2. Timestamp (when data was fetched)
3. Version ID (data_version_id for audit trail)

**Example API Response Structure:**

```json
{
  "analysis_id": "...",
  "analysis_type": "dcf_valuation",
  "ticker": "PETR4",
  "status": "completed",
  "result": {
    "fair_value": 28.50,
    "fair_value_range": [26.00, 31.00],
    "current_price": 27.80,
    "upside_pct": 2.4,
    "...": "..."
  },
  "data_metadata": {
    "data_timestamp": "2026-03-31T16:30:00Z",
    "data_version_id": "brapi_eod_20260331_v1.2",
    "data_sources": [
      { "source": "BRAPI", "type": "fundamentals", "freshness": "1d" },
      { "source": "B3/CVM", "type": "financial_statements", "freshness": "1q" }
    ],
    "cache_hit": false,
    "cache_ttl_seconds": 86400
  },
  "disclaimer": "Análise informativa, não constitui recomendação de investimento pessoal (CVM Res. 19/2021)",
  "disclaimer_shown_at": "2026-03-31T16:30:00Z"
}
```

**Frontend Display:**

```
Fair Value: R$ 28.50 (range R$ 26.00 — R$ 31.00)

Data freshness: Analysis as of 2026-03-31 16:30 BRT
Sources: BRAPI EOD (daily), B3/CVM (quarterly)
```

---

## Section 2: Cost Control Architecture

### 2.1 Per-User Quota System

**Design:** Hard quota enforcement at Celery task submission time. Users cannot request more analyses once quota exhausted.

**Quota Tiers (monthly, resets on 1st of month UTC):**

| Tier | Monthly Quota | Cost per Analysis | Use Case |
|------|---------------|------------------|----------|
| Free | 0 | N/A | Trial, no analysis access |
| Pro | 50 | ~$0.30–0.50 | Active investors, 1–2 analyses/week |
| Enterprise | 500 | ~$0.10–0.20 (bulk) | Institutional, 10–15 analyses/week |

**Quota Tracking Schema:**

```python
# backend/app/modules/billing/models.py (new)

class AnalysisQuotaLog(Base):
    """Per-tenant, per-month quota usage tracking."""

    __tablename__ = "analysis_quota_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    year_month: Mapped[str] = mapped_column(String(7), nullable=False)  # "2026-03"
    plan_tier: Mapped[str] = mapped_column(String(20), nullable=False)  # "free" | "pro" | "enterprise"
    quota_limit: Mapped[int] = mapped_column(Integer, nullable=False)    # e.g. 50
    quota_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    __table_args__ = (
        Index("ix_quota_tenant_month", "tenant_id", "year_month"),
    )
```

**Celery Task Guard (before running analysis):**

```python
# backend/app/modules/analysis/tasks.py (pseudocode)

@shared_task(name="analysis.run_dcf", bind=True, max_retries=0)
def run_dcf(self, job_id: str, tenant_id: str, ticker: str) -> None:
    """Run DCF analysis for a ticker."""

    # 1. Check quota
    with get_sync_db_session(tenant_id) as session:
        quota = session.execute(
            select(AnalysisQuotaLog)
            .where(
                AnalysisQuotaLog.tenant_id == tenant_id,
                AnalysisQuotaLog.year_month == date.today().strftime("%Y-%m"),
            )
        ).scalar_one()

        if quota.quota_used >= quota.quota_limit and quota.quota_limit > 0:
            # Quota exhausted
            _update_job(job_id, "failed", error="Analysis quota exhausted for this month")
            return

    # 2. Increment quota_used
    _increment_quota_used(tenant_id, year_month)

    # 3. Run analysis (rest of task logic)
    try:
        # ... DCF calculation ...
        _update_job(job_id, "completed", result_json=result)
    except Exception as exc:
        _update_job(job_id, "failed", error=str(exc)[:500])
```

### 2.2 Rate Limiting Middleware

**Pattern:** Reuse from v1.1 screener rate limiting, extend to per-user per-minute requests.

**Rate Limit Rules:**
- Free tier: 1 analysis request per 5 minutes (can stack up to quota limit per month)
- Pro tier: 1 analysis request per 1 minute
- Enterprise: No per-request rate limiting (but monthly quota enforced)

**Implementation:**

```python
# backend/app/core/rate_limit.py (new)

from functools import wraps
from datetime import datetime, timedelta
import redis as sync_redis

_redis_client = None

def get_rate_limit_redis():
    global _redis_client
    if _redis_client is None:
        _redis_client = sync_redis.from_url(
            os.environ.get("REDIS_URL", "redis://redis:6379/0"),
            decode_responses=True
        )
    return _redis_client

async def check_analysis_rate_limit(tenant_id: str, plan_tier: str) -> bool:
    """Check if user can submit a new analysis request."""

    r = get_rate_limit_redis()
    now = datetime.utcnow()
    key = f"analysis:rate_limit:{tenant_id}"

    # Allow-per-minute mapping
    limits = {"free": 1, "pro": 1, "enterprise": 100}
    window_seconds = {"free": 300, "pro": 60, "enterprise": 60}

    current_count = int(r.get(key) or 0)
    ttl = r.ttl(key)

    if plan_tier == "enterprise" or current_count < limits.get(plan_tier, 1):
        # Allowed
        r.incr(key)
        if ttl == -1:
            r.expire(key, window_seconds.get(plan_tier, 60))
        return True
    else:
        # Rate limited
        return False

# Usage in router
@router.post("/analysis/dcf")
async def request_dcf_analysis(
    body: DCFRequest,
    tenant: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Check rate limit
    plan_tier = tenant.subscription.plan_tier
    if not await check_analysis_rate_limit(tenant.tenant_id, plan_tier):
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Free tier: 1 request per 5 min. Pro: 1 per minute."
        )

    # Submit job
    job_id = str(uuid4())
    # ... rest of logic
    return {"job_id": job_id, "status": "pending"}
```

### 2.3 Cost Tracking per Analysis Type

**Design:** Log each analysis completion with LLM token count, provider used, duration. Dashboard sums by type.

**Cost Tracking Schema:**

```python
# backend/app/modules/logs/models.py (new/extended)

class AnalysisCostLog(Base):
    """Track cost per analysis type for operations."""

    __tablename__ = "analysis_cost_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_id: Mapped[str] = mapped_column(String(36), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "dcf" | "earnings" | "dividend" | "sector"
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)

    llm_provider: Mapped[str] = mapped_column(String(50), nullable=True)  # "openrouter" | "groq" | etc.
    llm_model: Mapped[str] = mapped_column(String(100), nullable=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=True)
    estimated_cost_usd: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=True)

    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # "completed" | "failed"

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    __table_args__ = (
        Index("ix_cost_tenant_month", "tenant_id", func.date_trunc('month', created_at)),
        Index("ix_cost_analysis_type", "analysis_type"),
    )
```

**Cost Estimation Function:**

```python
# backend/app/modules/analysis/cost.py (new)

def estimate_llm_cost(provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    """Estimate LLM cost in USD."""

    # Pricing as of 2026-03 (update periodically)
    pricing = {
        "openrouter/openai/gpt-4o-mini": {
            "input": 0.000150,
            "output": 0.000600,
        },
        "openrouter/deepseek/deepseek-chat": {
            "input": 0.000014,
            "output": 0.000056,
        },
        "groq/llama-3.3-70b-versatile": {
            "input": 0.0,
            "output": 0.0,  # Groq free tier
        },
        "groq/llama-3.1-8b-instant": {
            "input": 0.0,
            "output": 0.0,
        },
    }

    model_key = f"{provider}/{model}"
    rates = pricing.get(model_key, {"input": 0, "output": 0})

    return (input_tokens * rates["input"]) + (output_tokens * rates["output"])
```

**Cost Dashboard Endpoint (admin-only):**

```python
# backend/app/modules/admin/router.py (new)

@router.get("/admin/analysis-costs/summary")
async def get_cost_summary(
    month: str = Query(...),  # "2026-03"
    analysis_type: str | None = None,
    current_user: User = Depends(get_current_user),
):
    """Summary of analysis costs by type."""

    # Auth: admin only
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin only")

    with get_sync_db_session() as session:
        query = select(
            AnalysisCostLog.analysis_type,
            func.count(AnalysisCostLog.id).label("count"),
            func.sum(AnalysisCostLog.estimated_cost_usd).label("total_cost"),
            func.avg(AnalysisCostLog.duration_ms).label("avg_duration_ms"),
        ).where(
            func.date_trunc('month', AnalysisCostLog.created_at) == f"{month}-01",
        )

        if analysis_type:
            query = query.where(AnalysisCostLog.analysis_type == analysis_type)

        query = query.group_by(AnalysisCostLog.analysis_type)

        results = session.execute(query).all()
        return {
            "month": month,
            "total_cost_usd": sum(r.total_cost or 0 for r in results),
            "by_type": [
                {
                    "analysis_type": r.analysis_type,
                    "count": r.count,
                    "total_cost_usd": float(r.total_cost or 0),
                    "avg_duration_ms": int(r.avg_duration_ms or 0),
                }
                for r in results
            ]
        }
```

---

## Section 3: Data Versioning Strategy

### 3.1 Schema Design

**Principle:** Every analysis must be tagged with a data version ID and timestamp so we can:
1. Regenerate old analyses if methodology improves
2. Audit which version of fundamentals produced which valuation
3. Invalidate analyses when new earnings data arrives

**Data Versioning Fields (all analyses):**

```python
# backend/app/modules/analysis/models.py (new)

class AnalysisBase(Base):
    """Abstract base for all analysis job records."""

    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "dcf" | "earnings" | etc.
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)

    # Data versioning
    data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_version_id: Mapped[str] = mapped_column(String(100), nullable=False)  # "brapi_eod_20260331_v1.2"
    data_sources: Mapped[str] = mapped_column(Text, nullable=True)  # JSON array of sources

    # Job lifecycle
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_analysis_tenant_ticker", "tenant_id", "ticker"),
        Index("ix_analysis_data_version", "data_version_id"),
    )
```

**Data Source Tracking:**

```python
# backend/app/modules/analysis/versioning.py (new)

def build_data_version_id() -> str:
    """Generate a data_version_id combining source names and timestamp."""
    now = datetime.utcnow()
    return f"brapi_eod_{now.strftime('%Y%m%d')}_v1.2"

def get_data_sources() -> list[dict]:
    """Return list of data sources for this analysis run."""
    return [
        {
            "source": "BRAPI",
            "type": "fundamentals",
            "freshness": "1d",
            "timestamp": datetime.utcnow().isoformat(),
        },
        {
            "source": "B3/CVM",
            "type": "financial_statements",
            "freshness": "1q",
            "timestamp": None,  # From snapshot, not real-time
        },
    ]
```

### 3.2 API Response Layer

**Requirement:** All analysis API responses include data metadata.

```python
# backend/app/modules/analysis/schemas.py (new)

class DataMetadata(BaseModel):
    """Data versioning metadata for audit trail."""
    data_timestamp: datetime
    data_version_id: str
    data_sources: list[dict]  # [{"source": "BRAPI", "type": "fundamentals", "freshness": "1d"}, ...]
    cache_hit: bool
    cache_ttl_seconds: int

class AnalysisResponse(BaseModel):
    """Standard analysis response with versioning."""
    analysis_id: str
    analysis_type: str  # "dcf_valuation" | "earnings_analysis" | etc.
    ticker: str
    status: str  # "pending" | "running" | "completed" | "failed"
    result: dict | None  # Analysis-specific result payload
    data_metadata: DataMetadata
    error_message: str | None = None
```

### 3.3 Cache Invalidation Triggers

**Design:** When new earnings arrive, automatically invalidate cached analyses for that ticker.

**Invalidation Events:**

```python
# backend/app/modules/analysis/invalidation.py (new)

async def on_earnings_release(ticker: str, filing_date: datetime) -> None:
    """Called when new earnings announced. Invalidate all cached analyses for ticker."""

    with get_sync_db_session() as session:
        # Mark analyses as "stale" if older than filing_date
        session.execute(
            update(AnalysisBase)
            .where(
                AnalysisBase.ticker == ticker,
                AnalysisBase.completed_at < filing_date,
                AnalysisBase.status == "completed",
            )
            .values(status="stale", error_message="New earnings released; please refresh")
        )
        session.commit()

        # Clear from cache
        r = get_rate_limit_redis()
        r.delete(f"analysis:cache:{ticker}")

        logger.info(f"Invalidated analyses for {ticker} due to earnings release")

# Trigger from Celery task
@shared_task(name="analysis.check_earnings_releases")
def check_earnings_releases():
    """Daily task to check BRAPI for earnings and invalidate stale analyses."""

    from app.modules.market_data.adapters.brapi import brapi_client

    # Get list of tickers from portfolio universe
    tickers = get_analyzed_tickers_recent_7d()

    for ticker in tickers:
        try:
            earnings_data = brapi_client.get_earnings_dates(ticker)
            if earnings_data.get("last_earnings_date"):
                # Compare with analysis timestamps
                # If earnings > oldest analysis, invalidate
                asyncio.run(on_earnings_release(ticker, earnings_data["last_earnings_date"]))
        except Exception as exc:
            logger.warning(f"Failed to check earnings for {ticker}: {exc}")
```

---

## Section 4: Async Analysis Queue Architecture

### 4.1 Job Lifecycle Pattern (Reuse from Wizard)

**Flow:**

```
1. User POST /analysis/dcf with {ticker, assumptions, ...}
2. Router creates job record (status="pending"), returns {job_id, status, expires_at}
3. Celery task enqueued (checks quota, runs analysis)
4. Job status transitions: pending → running → completed | failed
5. WebSocket notifies frontend on completion
6. Frontend polls GET /analysis/{job_id} to retrieve results
```

**Job Status Schema (reuse from wizard):**

```python
class AnalysisJob(Base):
    """Async job for analysis requests. Reuse structure from WizardJob."""

    __tablename__ = "analysis_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    analysis_type: Mapped[str] = mapped_column(String(50), nullable=False)  # "dcf" | "earnings" | etc.
    ticker: Mapped[str] = mapped_column(String(10), nullable=False)

    # Data versioning
    data_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_version_id: Mapped[str] = mapped_column(String(100), nullable=False)

    # Job lifecycle (same as WizardJob)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_analysis_tenant_status", "tenant_id", "status"),
        Index("ix_analysis_created", "created_at"),
    )
```

### 4.2 Celery Task Pattern

**Template (DCF Analysis Example):**

```python
# backend/app/modules/analysis/tasks.py (new)

from celery import shared_task
from app.core.db_sync import get_sync_db_session, get_superuser_sync_db_session
from app.modules.ai.provider import call_llm, set_ai_context
from datetime import datetime, timezone

@shared_task(name="analysis.run_dcf", bind=True, max_retries=0)
def run_dcf(
    self,
    job_id: str,
    tenant_id: str,
    ticker: str,
    assumptions: dict | None = None,
) -> None:
    """Run DCF analysis for a ticker.

    Steps:
    1. Verify quota not exceeded
    2. Set job status → running
    3. Fetch fundamentals (BRAPI, CVM)
    4. Calculate DCF valuation
    5. Call LLM for narrative (with fallback)
    6. Build result JSON with data_version_id + data_timestamp
    7. Store result and mark completed/failed
    """

    logger.info(f"DCF analysis started: job={job_id} ticker={ticker}")

    # 1. Check quota
    try:
        quota = _check_analysis_quota(tenant_id)
        if not quota:
            _update_job(job_id, "failed", error="Analysis quota exhausted for this month")
            return
    except Exception as exc:
        _update_job(job_id, "failed", error=f"Quota check failed: {exc}")
        return

    # 2. Set job status → running
    _update_job(job_id, "running")

    # 3. Set AI context for logging
    set_ai_context(tenant_id=tenant_id, job_id=job_id, tier="paid")

    try:
        # 4. Fetch fundamentals
        fundamentals = _fetch_fundamentals(ticker)

        # 5. Calculate DCF
        data_timestamp = datetime.now(timezone.utc)
        dcf_result = _calculate_dcf(ticker, fundamentals, assumptions or {})

        # 6. Call LLM for narrative (with fallback)
        llm_narrative = None
        try:
            prompt = _build_dcf_narrative_prompt(ticker, fundamentals, dcf_result)
            llm_narrative = asyncio.run(call_llm(
                prompt,
                system="You are a financial analyst. Provide a brief, factual interpretation.",
                tier="paid",
                max_tokens=300,
            ))
        except Exception as exc:
            logger.warning(f"LLM narrative failed for {ticker}: {exc}, using fallback")
            llm_narrative = f"DCF analysis complete. Fair value: {dcf_result['fair_value']:.2f}. See detailed metrics above."

        # 7. Build result with data_version_id + data_timestamp
        result = {
            "ticker": ticker,
            "fair_value": float(dcf_result["fair_value"]),
            "fair_value_range": [float(dcf_result["low"]), float(dcf_result["high"])],
            "current_price": float(fundamentals["current_price"]),
            "upside_pct": float(dcf_result["upside_pct"]),
            "assumptions": {
                "growth_rate": dcf_result.get("growth_rate", 0),
                "discount_rate": dcf_result.get("discount_rate", 0),
                "terminal_growth": dcf_result.get("terminal_growth", 0),
            },
            "narrative": llm_narrative,
            "data_version_id": f"brapi_eod_{data_timestamp.strftime('%Y%m%d')}_v1.2",
            "data_timestamp": data_timestamp.isoformat(),
            "data_sources": [
                {"source": "BRAPI", "type": "fundamentals", "freshness": "1d"},
                {"source": "B3/CVM", "type": "filings", "freshness": "1q"},
            ],
        }

        # 8. Store result
        _update_job(job_id, "completed", result_json=json.dumps(result))
        _log_cost(tenant_id, job_id, "dcf", ticker, duration_ms=..., status="completed")

    except Exception as exc:
        logger.error(f"DCF task failed for {ticker}: {exc}", exc_info=True)
        _update_job(job_id, "failed", error=str(exc)[:500])
        _log_cost(tenant_id, job_id, "dcf", ticker, duration_ms=..., status="failed")

def _check_analysis_quota(tenant_id: str) -> bool:
    """Check if tenant has quota remaining."""
    with get_sync_db_session(tenant_id) as session:
        quota = session.execute(
            select(AnalysisQuotaLog)
            .where(
                AnalysisQuotaLog.tenant_id == tenant_id,
                AnalysisQuotaLog.year_month == date.today().strftime("%Y-%m"),
            )
        ).scalar_one_or_none()

        if not quota:
            # First time this month; create quota record
            plan = session.execute(
                select(User).where(User.tenant_id == tenant_id)
            ).scalar_one().subscription.plan_tier

            quota = AnalysisQuotaLog(
                tenant_id=tenant_id,
                year_month=date.today().strftime("%Y-%m"),
                plan_tier=plan,
                quota_limit=QUOTA_LIMITS.get(plan, 0),
                quota_used=0,
            )
            session.add(quota)
            session.commit()

        return quota.quota_used < quota.quota_limit

def _update_job(job_id: str, status: str, result_json: str | None = None, error: str | None = None) -> None:
    """Update job status and results."""
    with get_superuser_sync_db_session() as session:
        values = {"status": status}
        if result_json is not None:
            values["result_json"] = result_json
        if error is not None:
            values["error_message"] = error[:500]
        if status in ("completed", "failed"):
            values["completed_at"] = datetime.now(timezone.utc)

        session.execute(update(AnalysisJob).where(AnalysisJob.id == job_id).values(**values))
        session.commit()
```

### 4.3 WebSocket Notification Pattern

**Pattern (reuse from wizard):**

```python
# backend/app/modules/analysis/router.py (new)

from fastapi import WebSocket

@router.websocket("/ws/analysis/{job_id}")
async def websocket_analysis_updates(websocket: WebSocket, job_id: str):
    """WebSocket subscription for analysis job completion."""

    await websocket.accept()

    try:
        while True:
            # Check job status every 2 seconds
            with get_sync_db_session() as session:
                job = session.execute(
                    select(AnalysisJob).where(AnalysisJob.id == job_id)
                ).scalar_one_or_none()

            if not job:
                await websocket.send_json({"error": "Job not found"})
                await websocket.close()
                break

            if job.status in ("completed", "failed"):
                # Send final result and close
                await websocket.send_json({
                    "status": job.status,
                    "result": json.loads(job.result_json) if job.result_json else None,
                    "error": job.error_message,
                })
                await websocket.close()
                break
            else:
                # Send status update
                await websocket.send_json({
                    "status": job.status,
                    "message": f"Analysis in progress... ({job.status})"
                })

            await asyncio.sleep(2)

    except Exception as exc:
        logger.warning(f"WebSocket error for {job_id}: {exc}")
        await websocket.close()
```

**Frontend Usage:**

```typescript
// frontend/src/hooks/useAnalysisWebSocket.ts

export function useAnalysisWebSocket(jobId: string) {
  const [status, setStatus] = useState<'pending' | 'running' | 'completed' | 'failed'>('pending');
  const [result, setResult] = useState(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(`wss://api.investiq.com.br/ws/analysis/${jobId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setStatus(data.status);
      if (data.result) setResult(data.result);
      if (data.error) setError(data.error);
    };

    ws.onerror = (err) => {
      setError('WebSocket connection failed');
    };

    return () => ws.close();
  }, [jobId]);

  return { status, result, error };
}
```

---

## Section 5: LLM Provider Fallback Chain

### 5.1 Fallback Strategy for Analysis (Unlike Wizard)

**Difference from Wizard:** Wizard uses any-model-works approach (JSON is parsed the same way regardless of model). Analysis needs specific model capabilities for quality output.

**Fallback Chain (for analysis narratives):**

1. **Primary:** OpenRouter (Claude/GPT-4o-mini via OpenRouter) — high quality, $0.30–0.50 per analysis
2. **Fallback:** Groq (Llama 70b or DeepSeek) — medium quality, free tier
3. **Last Resort:** Return cached result with `outdated` flag + "Contact support to refresh" message

**Do NOT fall back to analysis silence.** If LLM quota exhausted, serve the most recent cached analysis with explicit "outdated" badge rather than breaking the feature.

### 5.2 Provider Configuration

```python
# backend/app/modules/analysis/providers.py (new)

ANALYSIS_LLM_CHAIN = [
    {
        "provider": "openrouter",
        "model": "openai/gpt-4o-mini",
        "cost_usd_per_1k_tokens": {
            "input": 0.15,
            "output": 0.60,
        },
        "timeout_seconds": 30,
        "max_retries": 1,
    },
    {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "cost_usd_per_1k_tokens": {
            "input": 0.0,
            "output": 0.0,
        },
        "timeout_seconds": 20,
        "max_retries": 1,
    },
]

async def call_analysis_llm(prompt: str, max_tokens: int = 300) -> tuple[str, dict]:
    """Call LLM with fallback chain.

    Returns:
        (response_text, metadata) where metadata = {
            "provider_used": "openrouter" | "groq",
            "model": "...",
            "success": true | false,
        }
    """

    for i, config in enumerate(ANALYSIS_LLM_CHAIN):
        try:
            logger.info(f"Attempting analysis LLM call {i+1}/{len(ANALYSIS_LLM_CHAIN)}: {config['provider']}")

            response = await asyncio.wait_for(
                _call_llm_provider(config, prompt, max_tokens),
                timeout=config["timeout_seconds"],
            )

            return response, {
                "provider_used": config["provider"],
                "model": config["model"],
                "success": True,
            }

        except asyncio.TimeoutError:
            logger.warning(f"LLM provider {config['provider']} timed out")
            continue

        except Exception as exc:
            logger.warning(f"LLM provider {config['provider']} failed: {exc}")
            continue

    # All providers failed
    raise AIProviderError("All analysis LLM providers exhausted")

async def _call_llm_provider(config: dict, prompt: str, max_tokens: int) -> str:
    """Call a specific LLM provider."""

    if config["provider"] == "openrouter":
        from app.modules.ai.provider import call_llm
        return await call_llm(
            prompt,
            system="You are a financial analyst. Be concise and factual.",
            tier="paid",
            max_tokens=max_tokens,
        )

    elif config["provider"] == "groq":
        import httpx
        api_key = os.environ.get("GROQ_API_KEY")

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": config["model"],
                    "messages": [
                        {"role": "system", "content": "You are a financial analyst."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    else:
        raise ValueError(f"Unknown provider: {config['provider']}")
```

### 5.3 Graceful Degradation

**When LLM quota exhausted:**

```python
def _get_cached_analysis_with_outdated_badge(job_id: str, ticker: str) -> dict:
    """Return most recent cached analysis with 'outdated' status."""

    with get_sync_db_session() as session:
        # Find most recent completed analysis for this ticker
        old_job = session.execute(
            select(AnalysisJob)
            .where(
                AnalysisJob.ticker == ticker,
                AnalysisJob.status == "completed",
                AnalysisJob.analysis_type == "dcf",  # or current analysis type
            )
            .order_by(AnalysisJob.completed_at.desc())
            .limit(1)
        ).scalar_one_or_none()

    if not old_job:
        # No cached version available
        raise AIProviderError("Analysis LLM quota exhausted and no cached version available")

    result = json.loads(old_job.result_json)
    result["_outdated"] = True
    result["_outdated_reason"] = "Analysis LLM quota exhausted. Results are from {old_job.completed_at}. Contact support to refresh."

    return result
```

---

## Section 6: Validation Architecture — Nyquist Verification

### 6.1 Purpose

Nyquist verification ensures the system maintains data quality and cost control under realistic usage. Key validations:

1. **Quota enforcement:** Users cannot exceed monthly limits
2. **Data versioning:** All analyses tagged with data_version_id + timestamp
3. **Async completion:** Job submitted instantly, completed without blocking
4. **Fallback switching:** Provider fallback triggers on timeout/failure
5. **Cost tracking:** Cost per analysis logged accurately

### 6.2 Unit Test Suite (Phase 12 Deliverable)

```python
# backend/tests/test_phase12_foundation.py (new)

import pytest
from datetime import datetime, timezone
from unittest.mock import patch, AsyncMock
import asyncio

# ============================================================================
# QUOTA ENFORCEMENT TESTS
# ============================================================================

def test_quota_enforcement_free_tier_blocks_requests(db_session, auth_user_free):
    """Free tier (quota=0) blocks analysis requests."""

    # Setup: Free tier user
    quota = AnalysisQuotaLog(
        tenant_id=auth_user_free.tenant_id,
        year_month=date.today().strftime("%Y-%m"),
        plan_tier="free",
        quota_limit=0,
        quota_used=0,
    )
    db_session.add(quota)
    db_session.commit()

    # Act: Submit DCF analysis request
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_free.access_token}"},
        json={"ticker": "PETR4"},
    )

    # Assert: 402 (Payment required) or similar
    assert response.status_code == 402
    assert "quota" in response.json()["detail"].lower()

def test_quota_enforcement_pro_tier_allows_50_per_month(db_session, auth_user_pro):
    """Pro tier (quota=50) allows up to 50 requests per month."""

    # Setup: Pro tier user with 49 uses remaining
    quota = AnalysisQuotaLog(
        tenant_id=auth_user_pro.tenant_id,
        year_month=date.today().strftime("%Y-%m"),
        plan_tier="pro",
        quota_limit=50,
        quota_used=49,
    )
    db_session.add(quota)
    db_session.commit()

    # Act: Submit 1 more request (should succeed)
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "VALE3"},
    )

    # Assert: 202 Accepted (job queued)
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # Act: Submit 51st request (should fail)
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "BBDC4"},
    )

    # Assert: 402 Quota exceeded
    assert response.status_code == 402

# ============================================================================
# DATA VERSIONING TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_analysis_includes_data_version_id(db_session, auth_user_pro):
    """All completed analyses include data_version_id and data_timestamp."""

    # Act: Submit and wait for DCF analysis
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "PETR4"},
    )
    job_id = response.json()["job_id"]

    # Wait for completion (poll job status)
    completed = False
    for _ in range(60):  # 60 * 1s = 60 second timeout
        result_response = client.get(
            f"/analysis/{job_id}",
            headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        )
        if result_response.json()["status"] == "completed":
            completed = True
            break
        await asyncio.sleep(1)

    assert completed, "Analysis did not complete within 60 seconds"

    # Assert: Response includes data_metadata
    data = result_response.json()
    assert "data_metadata" in data
    assert "data_timestamp" in data["data_metadata"]
    assert "data_version_id" in data["data_metadata"]
    assert "data_sources" in data["data_metadata"]

    # Assert: data_version_id format is reasonable
    version_id = data["data_metadata"]["data_version_id"]
    assert version_id.startswith("brapi_eod_")
    assert "v1.2" in version_id

def test_api_response_includes_disclaimer(db_session, auth_user_pro):
    """Analysis API response includes disclaimer text."""

    # Act: Get completed analysis
    # (assume one exists in DB for this test)
    response = client.get(
        "/analysis/PETR4/latest",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
    )

    # Assert: Response includes disclaimer
    data = response.json()
    assert "disclaimer" in data
    assert "CVM Res. 19/2021" in data["disclaimer"]
    assert "não constitui recomendação" in data["disclaimer"]

# ============================================================================
# ASYNC JOB LIFECYCLE TESTS
# ============================================================================

def test_analysis_request_returns_job_id_immediately(auth_user_pro):
    """POST /analysis/dcf returns job_id immediately (202, not 200)."""

    # Act: Submit DCF analysis
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "PETR4"},
    )

    # Assert: 202 Accepted (not 200 OK)
    assert response.status_code == 202
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "pending"

@pytest.mark.asyncio
async def test_analysis_job_transitions_pending_to_completed(auth_user_pro, monkeypatch):
    """Job status transitions pending → running → completed."""

    # Patch LLM call to return immediately
    async def mock_llm(*args, **kwargs):
        return "DCF fair value analysis complete."

    monkeypatch.setattr("app.modules.analysis.tasks.call_llm", mock_llm)

    # Act: Submit and poll
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "PETR4"},
    )
    job_id = response.json()["job_id"]

    # Poll job status
    status_sequence = []
    for i in range(60):
        result = client.get(
            f"/analysis/{job_id}",
            headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        )
        status = result.json()["status"]
        status_sequence.append(status)

        if status == "completed":
            break

        await asyncio.sleep(0.5)

    # Assert: Status progression observed
    assert "pending" in status_sequence
    assert "completed" in status_sequence

    # Verify "pending" appears before "completed"
    assert status_sequence.index("pending") < status_sequence.index("completed")

# ============================================================================
# FALLBACK PROVIDER TESTS
# ============================================================================

@pytest.mark.asyncio
async def test_llm_fallback_switches_on_timeout(monkeypatch):
    """If OpenRouter times out, Groq fallback is attempted."""

    call_log = []

    async def mock_openrouter_timeout(*args, **kwargs):
        call_log.append("openrouter")
        await asyncio.sleep(2)
        raise asyncio.TimeoutError("OpenRouter timeout")

    async def mock_groq_succeeds(*args, **kwargs):
        call_log.append("groq")
        return "Groq response"

    # Patch
    with patch("app.modules.analysis.providers._call_llm_provider") as mock_call:
        async def side_effect(config, *args, **kwargs):
            if config["provider"] == "openrouter":
                await mock_openrouter_timeout()
            elif config["provider"] == "groq":
                return await mock_groq_succeeds()

        mock_call.side_effect = side_effect

        # Act: Call analysis LLM
        response, metadata = await call_analysis_llm("Test prompt")

        # Assert: Groq was used (fallback triggered)
        assert metadata["provider_used"] == "groq"
        assert "groq" in call_log

# ============================================================================
# COST TRACKING TESTS
# ============================================================================

def test_cost_logged_per_analysis_type(db_session, auth_user_pro):
    """Each completed analysis logs cost entry."""

    # Assume: One DCF analysis completed
    # Act: Query cost logs
    with get_sync_db_session() as session:
        logs = session.execute(
            select(AnalysisCostLog)
            .where(
                AnalysisCostLog.tenant_id == auth_user_pro.tenant_id,
                AnalysisCostLog.analysis_type == "dcf",
            )
        ).scalars().all()

    # Assert: Cost log exists with reasonable values
    assert len(logs) > 0
    log = logs[0]
    assert log.estimated_cost_usd > 0
    assert log.duration_ms > 0
    assert log.status == "completed"

def test_cost_dashboard_aggregates_by_type(db_session, auth_user_admin):
    """Admin cost dashboard shows costs by analysis type."""

    # Act: Query cost summary
    response = client.get(
        "/admin/analysis-costs/summary?month=2026-03",
        headers={"Authorization": f"Bearer {auth_user_admin.access_token}"},
    )

    # Assert: Response includes breakdown by type
    assert response.status_code == 200
    data = response.json()
    assert "by_type" in data
    assert "total_cost_usd" in data

    # Check structure
    for item in data["by_type"]:
        assert "analysis_type" in item  # "dcf" | "earnings" | etc.
        assert "count" in item
        assert "total_cost_usd" in item
        assert "avg_duration_ms" in item

# ============================================================================
# RATE LIMITING TESTS
# ============================================================================

def test_rate_limit_free_tier_1_per_5_min(auth_user_free):
    """Free tier limited to 1 request per 5 minutes."""

    # Act: Submit first request (should succeed)
    r1 = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_free.access_token}"},
        json={"ticker": "PETR4"},
    )
    assert r1.status_code == 202

    # Act: Submit second request immediately (should be rate limited)
    r2 = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_free.access_token}"},
        json={"ticker": "VALE3"},
    )

    # Assert: 429 Too Many Requests
    assert r2.status_code == 429
    assert "rate limit" in r2.json()["detail"].lower()

def test_rate_limit_pro_tier_1_per_minute(auth_user_pro):
    """Pro tier limited to 1 request per minute."""

    # Act: Submit first request (should succeed)
    r1 = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "PETR4"},
    )
    assert r1.status_code == 202

    # Act: Submit second request immediately (should be rate limited)
    r2 = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "VALE3"},
    )

    # Assert: 429 Too Many Requests
    assert r2.status_code == 429

# ============================================================================
# INTEGRATION TEST (END-TO-END)
# ============================================================================

@pytest.mark.asyncio
async def test_full_analysis_flow_quota_data_versioning_cost_logging(
    db_session, auth_user_pro, monkeypatch
):
    """End-to-end: quota check → job submission → completion → cost logged → data versioned."""

    # Patch LLM for instant response
    async def mock_llm(*args, **kwargs):
        return "Fair value R$ 28.50"

    monkeypatch.setattr("app.modules.analysis.tasks.call_llm", mock_llm)

    # 1. Verify quota is available
    with get_sync_db_session(auth_user_pro.tenant_id) as session:
        quota = session.execute(
            select(AnalysisQuotaLog)
            .where(
                AnalysisQuotaLog.tenant_id == auth_user_pro.tenant_id,
                AnalysisQuotaLog.year_month == date.today().strftime("%Y-%m"),
            )
        ).scalar_one()
        quota_before = quota.quota_used

    # 2. Submit DCF analysis
    response = client.post(
        "/analysis/dcf",
        headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        json={"ticker": "PETR4"},
    )

    assert response.status_code == 202
    job_id = response.json()["job_id"]

    # 3. Wait for completion
    completed = False
    for _ in range(30):
        result = client.get(
            f"/analysis/{job_id}",
            headers={"Authorization": f"Bearer {auth_user_pro.access_token}"},
        )
        if result.json()["status"] == "completed":
            completed = True
            break
        await asyncio.sleep(1)

    assert completed, "Analysis did not complete"

    # 4. Verify data_version_id present
    data = result.json()
    assert data["data_metadata"]["data_version_id"]
    assert data["data_metadata"]["data_timestamp"]

    # 5. Verify quota incremented
    with get_sync_db_session(auth_user_pro.tenant_id) as session:
        quota = session.execute(
            select(AnalysisQuotaLog)
            .where(
                AnalysisQuotaLog.tenant_id == auth_user_pro.tenant_id,
                AnalysisQuotaLog.year_month == date.today().strftime("%Y-%m"),
            )
        ).scalar_one()
        quota_after = quota.quota_used

    assert quota_after == quota_before + 1

    # 6. Verify cost logged
    with get_sync_db_session() as session:
        costs = session.execute(
            select(AnalysisCostLog)
            .where(AnalysisCostLog.job_id == job_id)
        ).scalars().all()

    assert len(costs) == 1
    assert costs[0].analysis_type == "dcf"
    assert costs[0].ticker == "PETR4"
    assert costs[0].estimated_cost_usd > 0
```

### 6.3 Integration Test: Staging Load Test

**Before Phase 13, validate in staging:**

```bash
# Test 50 concurrent analysis requests with fallback switching
pytest tests/test_phase12_foundation.py::test_concurrent_50_requests_with_fallback -v --tb=short

# Expected: All 50 complete within 5 minutes, mix of OpenRouter and Groq, cost tracking accurate
```

---

## Section 7: Implementation Roadmap (Phase 12 Plans)

Phase 12 breaks into 3 consecutive plans:

### Plan 12-01: Legal Audit + Disclaimer Component
**Duration:** 3–5 days
**Deliverables:**
1. CVM lawyer consultation (2–3 hours, async via email + Slack)
2. Disclaimer component (React) + backend API flag
3. Integration test confirming disclaimer renders before analysis

### Plan 12-02: Quota System + Rate Limiting
**Duration:** 5–7 days
**Deliverables:**
1. `AnalysisQuotaLog` schema + migrations
2. Rate limiting middleware (Redis-backed)
3. Quota enforcement in Celery task guard
4. Admin cost dashboard endpoint
5. Unit tests for quota enforcement + rate limiting

### Plan 12-03: Data Versioning + Async Infrastructure
**Duration:** 5–7 days
**Deliverables:**
1. `AnalysisJob` schema + data_versioning fields + migrations
2. Celery task template (DCF example + docstring)
3. WebSocket handler for job completion notifications
4. LLM provider fallback chain (OpenRouter → Groq)
5. Cost logging + dashboard
6. Full test suite (50+ test cases)
7. Staging integration test (50 concurrent requests)

**Total Phase 12 Duration:** 13–19 days (2–3 weeks)

---

## Section 8: Success Criteria (Phase 12 Gating)

Phase 12 is complete when:

1. ✅ Legal audit memo signed off (CVM registration threshold documented)
2. ✅ Disclaimer component renders on all analysis endpoints (integration test passes)
3. ✅ Quota enforcement test passes (free=0, pro=50, enterprise=500)
4. ✅ Data versioning test passes (all responses include data_version_id + data_timestamp)
5. ✅ Async job lifecycle test passes (pending → running → completed in <30s for simple DCF)
6. ✅ Fallback provider test passes (OpenRouter timeout triggers Groq attempt)
7. ✅ Cost tracking test passes (cost logged accurately per analysis type)
8. ✅ Rate limiting test passes (free=1 per 5min, pro=1 per 1min)
9. ✅ Staging load test passes (50 concurrent requests, p95 <30s, no cost_tracking errors)
10. ✅ All 257 existing tests still pass (no regression)

**Gating Rule:** Phase 13 (Core Analysis Engine) cannot start until all 10 criteria pass.

---

## Open Questions (Resolve in Phase 12)

1. **CVM registration threshold:** At what user count / analysis volume does InvestIQ need to register as an adviser?
   - **Action:** Schedule call with CVM lawyer, document threshold, update disclaimer if needed

2. **OpenRouter fallback latency:** Is 10–15s average latency acceptable when Groq fallback fires?
   - **Action:** Load test in staging, measure p95 latency with fallback enabled

3. **Earnings feed timing:** Does BRAPI capture earnings announcements same-day or +1 day?
   - **Action:** Monitor earnings releases during Phase 12, log timing in production

4. **Cost estimation accuracy:** Are pricing tiers accurate as of March 2026?
   - **Action:** Verify pricing at OpenRouter/Groq before Phase 13 launch, update constants if needed

---

## References

### Existing Code Patterns (Reuse)

- **Wizard Celery task:** `backend/app/modules/wizard/tasks.py` (async pattern, retry logic, job status transitions)
- **Wizard models:** `backend/app/modules/wizard/models.py` (WizardJob schema, RLS isolation)
- **AI provider:** `backend/app/modules/ai/provider.py` (fallback chain, cost context setting)
- **Rate limiting:** `backend/app/modules/screener/tasks.py` (brapi.dev rate limit handling)

### External References

- **CVM Resolução 19/2021:** https://www.cvm.gov.br/export/sites/default/atos/resolucoes/resolucoes/2021/20210115/res_19_2021.pdf
- **CVM Resolução 30/2021:** https://www.cvm.gov.br/export/sites/default/atos/resolucoes/resolucoes/2021/20210416/res_30_2021.pdf
- **OpenRouter Pricing:** https://openrouter.ai/docs#pricing
- **Groq API Pricing:** https://console.groq.com/docs/pricing

---

## Appendix: Database Schema (Alembic Migration)

```python
# backend/alembic/versions/0020_phase12_foundation.py

"""Phase 12 Foundation: Quota, Cost Tracking, Data Versioning

Revision ID: 0020
Revises: 0019
Create Date: 2026-03-31

"""
from alembic import op
import sqlalchemy as sa

revision = "0020"
down_revision = "0019"

def upgrade():
    # analysis_quota_logs table
    op.create_table(
        'analysis_quota_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('year_month', sa.String(7), nullable=False),
        sa.Column('plan_tier', sa.String(20), nullable=False),
        sa.Column('quota_limit', sa.Integer(), nullable=False),
        sa.Column('quota_used', sa.Integer(), nullable=False, server_default='0'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_quota_tenant_month', 'analysis_quota_logs', ['tenant_id', 'year_month'])

    # analysis_jobs table
    op.create_table(
        'analysis_jobs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('data_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_version_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('result_json', sa.Text(), nullable=True),
        sa.Column('error_message', sa.String(500), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_analysis_tenant_status', 'analysis_jobs', ['tenant_id', 'status'])
    op.create_index('ix_analysis_created', 'analysis_jobs', ['created_at'])

    # analysis_cost_logs table
    op.create_table(
        'analysis_cost_logs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('tenant_id', sa.String(36), nullable=False),
        sa.Column('job_id', sa.String(36), nullable=False),
        sa.Column('analysis_type', sa.String(50), nullable=False),
        sa.Column('ticker', sa.String(10), nullable=False),
        sa.Column('llm_provider', sa.String(50), nullable=True),
        sa.Column('llm_model', sa.String(100), nullable=True),
        sa.Column('input_tokens', sa.Integer(), nullable=True),
        sa.Column('output_tokens', sa.Integer(), nullable=True),
        sa.Column('estimated_cost_usd', sa.Numeric(10, 4), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cost_analysis_type', 'analysis_cost_logs', ['analysis_type'])

def downgrade():
    op.drop_index('ix_cost_analysis_type')
    op.drop_table('analysis_cost_logs')
    op.drop_index('ix_analysis_created')
    op.drop_index('ix_analysis_tenant_status')
    op.drop_table('analysis_jobs')
    op.drop_index('ix_quota_tenant_month')
    op.drop_table('analysis_quota_logs')
```

---

*Research completed: 2026-03-31*
*Scope: Phase 12 Foundation (Legal, Cost Control, Async, Data Versioning)*
*Confidence: HIGH (technical architecture) / MEDIUM (CVM regulatory specifics)*
*Status: Ready for roadmap approval and Plan 12-01 kickoff*
