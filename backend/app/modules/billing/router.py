"""Billing router — /billing/checkout, /billing/portal, /billing/webhook.

CRITICAL patterns:
- /webhook uses get_db() (no auth — Stripe has no JWT cookie)
- /webhook reads raw bytes via await request.body() BEFORE any JSON parsing
- /checkout and /portal use get_authed_db() (authenticated users only)
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.limiter import limiter
from app.core.middleware import get_authed_db
from app.core.security import decode_token, get_current_user
from app.modules.auth.models import User
from app.modules.billing.schemas import CheckoutResponse, MetricsResponse, PortalResponse, SubscriberInfo, UsageResponse
from app.modules.billing.service import billing_service

router = APIRouter()
logger = logging.getLogger(__name__)


def _checkout_rate_key(request: Request) -> str:
    """Rate-limit key: user_id extracted from JWT cookie. Falls back to IP."""
    token = request.cookies.get("access_token")
    if token:
        try:
            return f"checkout:{decode_token(token)['sub']}"
        except Exception:
            pass
    return request.client.host if request.client else "unknown"


@router.post("/checkout", response_model=CheckoutResponse)
@limiter.limit("3/minute", key_func=_checkout_rate_key)
async def create_checkout_session(
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
) -> CheckoutResponse:
    """Create a Stripe Checkout session for the Premium subscription.

    P1 idempotency: If the frontend sends Idempotency-Key header, we cache
    the response. Duplicate requests with the same key return the cached URL
    without creating a new Stripe session, preventing accidental double-clicks.
    """
    from app.core.config import settings
    from app.modules.billing.models import IdempotentCheckoutRequest

    user_id = current_user["user_id"]
    idempotency_key = request.headers.get("Idempotency-Key")

    # Check cache: if we've seen this idempotency key before, return cached URL
    if idempotency_key:
        result = await db.execute(
            select(IdempotentCheckoutRequest).where(
                IdempotentCheckoutRequest.idempotency_key == idempotency_key
            )
        )
        cached = result.scalar_one_or_none()
        if cached:
            logger.info(
                "billing.checkout_cached user_id=%s idempotency_key=%s",
                user_id, idempotency_key,
            )
            return CheckoutResponse(checkout_url=cached.checkout_url)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    customer_id = await billing_service.get_or_create_customer(user, db)
    url = await billing_service.create_checkout_session(
        customer_id=customer_id,
        price_id=settings.STRIPE_PREMIUM_PRICE_ID,
        success_url=f"{settings.APP_URL}/planos/sucesso",
        cancel_url=f"{settings.APP_URL}/planos",
    )

    # Cache the result if idempotency key was provided
    if idempotency_key:
        db.add(
            IdempotentCheckoutRequest(
                idempotency_key=idempotency_key,
                user_id=user_id,
                checkout_url=url,
            )
        )
        await db.flush()

    logger.info("billing.checkout_started user_id=%s customer_id=%s", user_id, customer_id)
    return CheckoutResponse(checkout_url=url)


@router.post("/portal", response_model=PortalResponse)
async def create_portal_session(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
) -> PortalResponse:
    """Create a Stripe Billing Portal session for subscription management.

    Returns the portal URL. Frontend redirects to it for cancel/update payment method.
    Returns 400 if user has no stripe_customer_id (never subscribed).
    """
    from app.core.config import settings

    user_id = current_user["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nenhuma assinatura encontrada. Assine o plano Premium primeiro.",
        )

    url = await billing_service.create_portal_session(
        customer_id=user.stripe_customer_id,
        return_url=f"{settings.APP_URL}/planos",
    )
    return PortalResponse(portal_url=url)


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),  # NOT get_authed_db — Stripe has no JWT cookie
):
    """Receive and process Stripe webhook events.

    Idempotency: checks stripe_events table by event ID before processing.
    Duplicate events (Stripe retries) are acknowledged immediately without
    re-running handlers, preventing double-billing or duplicate state changes.

    MUST use await request.body() (raw bytes) for signature verification.
    Always returns 200 — Stripe retries on non-200, which we never want.
    """
    from datetime import datetime, timezone
    from app.core.config import settings
    from app.modules.billing.models import StripeEvent
    from app.modules.billing.service import _get_stripe

    payload = await request.body()  # raw bytes — MANDATORY before any parsing
    sig_header = request.headers.get("stripe-signature", "")

    try:
        client = _get_stripe()
        event = client.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")

    event_id = event["id"]
    event_type = event["type"]
    data = event["data"]["object"]

    # --- Idempotency check ---
    existing = await db.execute(select(StripeEvent).where(StripeEvent.id == event_id))
    if existing.scalar_one_or_none():
        logger.info("Stripe event %s (%s) already processed — skipping", event_id, event_type)
        return {"status": "ok"}

    # --- Dispatch handler ---
    handler_status = "success"
    try:
        if event_type == "checkout.session.completed":
            logger.info("billing.checkout_completed customer=%s", data.get("customer"))
            await billing_service.handle_checkout_completed(data, db)
        elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
            logger.info("billing.invoice_paid customer=%s", data.get("customer"))
            await billing_service.handle_invoice_paid(data, db)
        elif event_type == "invoice.payment_failed":
            logger.info("billing.payment_failed customer=%s", data.get("customer"))
            await billing_service.handle_payment_failed(data, db)
        elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
            logger.info("billing.subscription_changed id=%s status=%s", data.get("id"), data.get("status"))
            await billing_service.handle_subscription_changed(data, db)
        else:
            logger.debug("Unhandled Stripe event type: %s", event_type)
    except Exception as exc:
        handler_status = "error"
        logger.error("billing.handler_error event=%s type=%s error=%s", event_id, event_type, exc)

    # --- Record event (always, to prevent re-processing) ---
    db.add(StripeEvent(
        id=event_id,
        event_type=event_type,
        processed_at=datetime.now(tz=timezone.utc),
        status=handler_status,
    ))
    await db.flush()

    return {"status": "ok"}


@router.get("/usage", response_model=UsageResponse)
async def get_usage(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
) -> UsageResponse:
    """Return the current user's usage counters for freemium gates."""
    from datetime import datetime, timezone
    from sqlalchemy import func
    from app.core.plan_gate import FREE_IMPORTS_PER_MONTH, FREE_TRANSACTION_LIMIT
    from app.modules.imports.models import ImportJob
    from app.modules.portfolio.models import Transaction

    user_id = current_user["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    now = datetime.now(tz=timezone.utc)
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    imports_count = await db.scalar(
        select(func.count())
        .select_from(ImportJob)
        .where(ImportJob.created_at >= start_of_month)
    ) or 0

    tx_count = await db.scalar(
        select(func.count()).select_from(Transaction)
    ) or 0

    return UsageResponse(
        imports_this_month=imports_count,
        imports_limit=FREE_IMPORTS_PER_MONTH,
        transactions_total=tx_count,
        transactions_limit=FREE_TRANSACTION_LIMIT,
        plan=user.plan,
    )


@router.get("/admin/metrics", response_model=MetricsResponse, include_in_schema=False)
async def billing_metrics(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> MetricsResponse:
    """Return billing metrics counts. Admin-only."""
    from app.core.config import settings
    from sqlalchemy import func
    from app.modules.billing.models import StripeEvent

    admin_result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    admin_user = admin_result.scalar_one_or_none()
    if not admin_user or admin_user.email not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    from datetime import datetime, timedelta, timezone
    from sqlalchemy import case

    # Single query — no 5 round-trips
    counts_row = (await db.execute(
        select(
            func.sum(case((User.plan == "free", 1), else_=0)).label("free_users"),
            func.sum(case((User.plan == "pro", 1), else_=0)).label("pro_users"),
            func.sum(case((User.subscription_status == "active", 1), else_=0)).label("active_subs"),
            func.sum(case((User.subscription_status == "past_due", 1), else_=0)).label("past_due"),
        )
    )).one()

    free_users = int(counts_row.free_users or 0)
    pro_users = int(counts_row.pro_users or 0)
    active_subs = int(counts_row.active_subs or 0)
    past_due = int(counts_row.past_due or 0)

    # Rolling 30-day churn: cancellation events from Stripe, not snapshot of current status.
    # Source: StripeEvent table — customer.subscription.deleted is the canonical churn signal.
    # Denominator: active now + churned in period = approximate cohort at start of window.
    thirty_days_ago = datetime.now(tz=timezone.utc) - timedelta(days=30)
    churned_last_30d = await db.scalar(
        select(func.count()).select_from(StripeEvent)
        .where(StripeEvent.event_type == "customer.subscription.deleted")
        .where(StripeEvent.processed_at >= thirty_days_ago)
        .where(StripeEvent.status == "success")
    ) or 0

    cohort = active_subs + churned_last_30d
    churn_rate = round(churned_last_30d / cohort * 100, 1) if cohort > 0 else 0.0

    conversions = await db.scalar(
        select(func.count()).select_from(StripeEvent)
        .where(StripeEvent.event_type == "checkout.session.completed")
        .where(StripeEvent.status == "success")
    ) or 0

    return MetricsResponse(
        free_users=free_users,
        pro_users=pro_users,
        active_subscriptions=active_subs,
        past_due_subscriptions=past_due,
        churned_last_30d=churned_last_30d,
        churn_rate_pct=churn_rate,
        total_conversions=conversions,
    )


@router.get("/admin/subscribers", response_model=list[SubscriberInfo], include_in_schema=False)
async def list_subscribers(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),  # Unscoped — admin sees all tenants
) -> list[SubscriberInfo]:
    """Return all paying subscribers. Admin-only endpoint.

    Uses get_db (not get_authed_db) to bypass RLS — admin must see all users,
    not just their own tenant. Caller must be in settings.ADMIN_EMAILS.
    """
    from app.core.config import settings

    # Verify caller is an admin
    admin_result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    admin_user = admin_result.scalar_one_or_none()
    if not admin_user or admin_user.email not in settings.ADMIN_EMAILS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")

    result = await db.execute(
        select(User)
        .where(User.plan != "free")
        .order_by(User.created_at.desc())
    )
    subscribers = result.scalars().all()

    return [
        SubscriberInfo(
            user_id=u.id,
            email=u.email,
            plan=u.plan,
            subscription_status=u.subscription_status,
            stripe_customer_id=u.stripe_customer_id,
            subscription_current_period_end=u.subscription_current_period_end,
            created_at=u.created_at,
        )
        for u in subscribers
    ]
