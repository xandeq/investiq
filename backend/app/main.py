import traceback as tb_mod
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import engine, async_session_factory
from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import configure_logging
from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.security import get_current_user
from app.modules.auth.router import router as auth_router
from app.modules.portfolio.router import router as portfolio_router
from app.modules.market_data.router import router as market_data_router
from app.modules.dashboard.router import router as dashboard_router
from app.modules.ai.router import router as ai_router
from app.modules.imports.router import router as imports_router
from app.modules.billing.router import router as billing_router
from app.modules.logs.router import router as logs_router
from app.modules.ai.usage_router import router as ai_usage_router
from app.modules.profile.router import router as profile_router
from app.modules.watchlist.router import router as watchlist_router
from app.modules.insights.router import router as insights_router
from app.modules.screener.router import router as screener_router
from app.modules.ir_helper.router import router as ir_helper_router
from app.modules.screener_v2.router import router as screener_v2_router
from app.modules.comparador.router import router as comparador_router
from app.modules.simulador.router import router as simulador_router
from app.modules.wizard.router import router as wizard_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield
    await engine.dispose()


app = FastAPI(
    title="InvestIQ API",
    description="Investment portfolio management and analysis platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
)


@app.middleware("http")
async def capture_unhandled_exceptions(request: Request, call_next):
    """Catches any unhandled 500 exception and persists it to app_logs."""
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        tb_text = tb_mod.format_exc()
        try:
            async with async_session_factory() as session:
                await session.execute(
                    sa_text(
                        """
                        INSERT INTO app_logs
                            (id, level, title, message, traceback,
                             request_path, request_method, created_at)
                        VALUES
                            (:id, :level, :title, :message, :traceback,
                             :request_path, :request_method, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "level": "ERROR",
                        "title": f"{type(exc).__name__}: {str(exc)[:200]}",
                        "message": str(exc),
                        "traceback": tb_text,
                        "request_path": str(request.url.path),
                        "request_method": request.method,
                        "created_at": datetime.now(tz=timezone.utc),
                    },
                )
                await session.commit()
        except Exception:
            pass  # Never let logging break the error response
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(portfolio_router, prefix="/portfolio", tags=["portfolio"])
app.include_router(market_data_router, prefix="/market-data", tags=["market-data"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(ai_router, prefix="/ai", tags=["ai"])
app.include_router(imports_router, prefix="/imports", tags=["imports"])
app.include_router(billing_router, prefix="/billing", tags=["billing"])
app.include_router(logs_router, prefix="/admin/logs", tags=["admin"])
app.include_router(ai_usage_router, prefix="/admin/ai-usage", tags=["admin"])
app.include_router(profile_router, prefix="/profile", tags=["profile"])
app.include_router(watchlist_router, prefix="/watchlist", tags=["watchlist"])
app.include_router(insights_router, prefix="/insights", tags=["insights"])
app.include_router(screener_router, prefix="/screener", tags=["screener"])
app.include_router(ir_helper_router, prefix="/ir-helper", tags=["ir-helper"])
# Phase 8: Snapshot-based screener + renda fixa catalog (no external API calls per request)
app.include_router(screener_v2_router, prefix="/screener", tags=["screener-v2"])
app.include_router(screener_v2_router, prefix="/renda-fixa", tags=["renda-fixa"])
# Phase 9: Comparador RF vs RV
app.include_router(comparador_router, prefix="/comparador", tags=["comparador"])
# Phase 10: Simulador de Alocação
app.include_router(simulador_router, prefix="/simulador", tags=["simulador"])
# Phase 11: Wizard Onde Investir
app.include_router(wizard_router, prefix="/wizard", tags=["wizard"])


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.ENVIRONMENT}


@app.get("/me")
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
):
    """Returns the authenticated user's profile including plan and admin status."""
    from sqlalchemy import select as sa_select
    from app.modules.auth.models import User

    from datetime import datetime, timezone as _tz

    user_id = current_user["user_id"]
    result = await db.execute(sa_select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    plan = user.plan if user else "free"
    email = user.email if user else ""
    is_admin = email in settings.ADMIN_EMAILS

    # Trial state
    is_trial = False
    days_remaining = 0
    trial_ends_at = None
    if user and user.plan == "free" and user.trial_ends_at is not None:
        now = datetime.now(tz=_tz.utc)
        # Normalize to aware datetimes for comparison (SQLite returns naive datetimes)
        trial_ends = user.trial_ends_at
        if trial_ends.tzinfo is None:
            trial_ends = trial_ends.replace(tzinfo=_tz.utc)
        if trial_ends > now:
            is_trial = True
            days_remaining = max(0, (trial_ends - now).days)
            trial_ends_at = trial_ends.isoformat()
            plan = "pro"  # effective plan during trial

    return {
        "user_id": current_user["user_id"],
        "tenant_id": current_user["tenant_id"],
        "plan": plan,
        "email": email,
        "is_admin": is_admin,
        "is_trial": is_trial,
        "days_remaining": days_remaining,
        "trial_ends_at": trial_ends_at,
    }
