"""BillingService — wraps Stripe API calls.

Uses StripeClient + HTTPXClient for async (not global stripe.api_key).
The module-level _stripe instance is created lazily to allow tests to
patch it via mock_stripe_client fixture before first use.

User constraint: stripe-python v14.4.1 with StripeClient + HTTPXClient instance
pattern. All async Stripe calls use _async methods (create_async, retrieve_async).

Subscription table writes:
- Every webhook handler that changes billing state upserts a Subscription row.
- User.plan remains the canonical access-control field (no join on auth check).
- Subscriptions are written by webhooks only — never from checkout redirect.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.billing.email_templates import (
    payment_failed_email,
    payment_received_email,
    subscription_canceled_email,
    welcome_premium_email,
)

logger = logging.getLogger(__name__)

# Module-level StripeClient — lazy init, patchable in tests
_stripe = None


def _get_stripe():
    global _stripe
    if _stripe is None:
        from stripe import StripeClient, HTTPXClient
        from app.core.config import settings
        _stripe = StripeClient(
            api_key=settings.STRIPE_SECRET_KEY,
            http_client=HTTPXClient(),
        )
    return _stripe


async def _upsert_subscription(
    db: AsyncSession,
    *,
    user_id: str,
    stripe_customer_id: str,
    stripe_subscription_id: str,
    plan: str,
    status: str,
    current_period_end: datetime | None,
) -> None:
    """Insert or update a Subscription record by stripe_subscription_id."""
    from app.modules.billing.models import Subscription

    result = await db.execute(
        select(Subscription).where(
            Subscription.stripe_subscription_id == stripe_subscription_id
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.plan = plan
        existing.status = status
        existing.current_period_end = current_period_end
    else:
        db.add(
            Subscription(
                user_id=user_id,
                stripe_customer_id=stripe_customer_id,
                stripe_subscription_id=stripe_subscription_id,
                plan=plan,
                status=status,
                current_period_end=current_period_end,
            )
        )


class BillingService:
    async def get_or_create_customer(self, user: User, db: AsyncSession) -> str:
        """Return existing Stripe customer ID or create a new one."""
        if user.stripe_customer_id:
            return user.stripe_customer_id
        client = _get_stripe()
        customer = await client.customers.create_async(
            params={"email": user.email, "metadata": {"user_id": user.id}}
        )
        await db.execute(
            update(User).where(User.id == user.id).values(stripe_customer_id=customer.id)
        )
        await db.flush()
        return customer.id

    async def create_checkout_session(
        self,
        customer_id: str,
        price_id: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Return Stripe Checkout hosted URL."""
        client = _get_stripe()
        session = await client.checkout.sessions.create_async(
            params={
                "customer": customer_id,
                "mode": "subscription",
                "line_items": [{"price": price_id, "quantity": 1}],
                "success_url": success_url + "?session_id={CHECKOUT_SESSION_ID}",
                "cancel_url": cancel_url,
                "currency": "brl",
            }
        )
        return session.url

    async def create_portal_session(self, customer_id: str, return_url: str) -> str:
        """Return Stripe Billing Portal URL."""
        client = _get_stripe()
        session = await client.billing_portal.sessions.create_async(
            params={"customer": customer_id, "return_url": return_url}
        )
        return session.url

    async def handle_checkout_completed(self, session_data: dict, db: AsyncSession) -> None:
        """checkout.session.completed — provision premium access and record subscription."""
        stripe_customer_id = session_data.get("customer")
        subscription_id = session_data.get("subscription")
        if not stripe_customer_id or not subscription_id:
            logger.warning("checkout.session.completed missing customer or subscription")
            return

        client = _get_stripe()
        sub = await client.subscriptions.retrieve_async(subscription_id)
        period_end = datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc)

        # Lock user row for the duration of this transaction.
        # WITH FOR UPDATE serializes concurrent checkouts for the same user —
        # prevents the race condition where two simultaneous webhooks both see
        # no prior subscription and both create an active subscription.
        result = await db.execute(
            select(User)
            .where(User.stripe_customer_id == stripe_customer_id)
            .with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            logger.warning("No user found for stripe_customer_id=%s", stripe_customer_id)
            return

        # Cancela assinatura anterior se o usuário está fazendo upgrade
        if user.stripe_subscription_id and user.stripe_subscription_id != subscription_id:
            prior_sub_id = user.stripe_subscription_id
            try:
                await client.subscriptions.cancel_async(prior_sub_id)
                logger.info(
                    "billing.prior_sub_canceled user_id=%s prior_sub=%s...%s new_sub=%s...%s",
                    user.id,
                    prior_sub_id[:8], prior_sub_id[-4:],
                    subscription_id[:8], subscription_id[-4:],
                )
            except Exception as exc:
                logger.error(
                    "billing.prior_sub_cancel_failed user_id=%s prior_sub=%s...%s error=%s",
                    user.id, prior_sub_id[:8], prior_sub_id[-4:], exc,
                )
                # Fail fast — reject webhook, Stripe will retry. Prevents silent duplicate subscriptions
                raise

            # Immediately mark the prior subscription row as canceled in our DB.
            # The Stripe webhook (customer.subscription.deleted) will arrive later to confirm,
            # but acting now closes the window where two rows show status=active simultaneously.
            from app.modules.billing.models import Subscription as SubModel
            await db.execute(
                update(SubModel)
                .where(SubModel.stripe_subscription_id == prior_sub_id)
                .values(status="canceled")
            )

        # Upsert subscription record
        await _upsert_subscription(
            db,
            user_id=user.id,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=subscription_id,
            plan="pro",
            status=sub.status,
            current_period_end=period_end,
        )

        # Update user plan (access-control field)
        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(
                plan="pro",
                stripe_subscription_id=subscription_id,
                subscription_status=sub.status,
                subscription_current_period_end=period_end,
            )
        )
        await db.flush()

        # Observability: alert if duplicate active subscriptions remain in DB
        # This should never fire after the cancellation above, but acts as a canary
        from app.modules.billing.models import Subscription
        from sqlalchemy import func
        active_count = await db.scalar(
            select(func.count()).select_from(Subscription).where(
                Subscription.user_id == user.id,
                Subscription.status.in_(["active", "trialing"]),
            )
        ) or 0
        if active_count > 1:
            logger.warning(
                "billing.duplicate_sub_detected user_id=%s active_count=%d"
                " — investigate immediately",
                user.id, active_count,
            )

        # Send welcome-to-premium email (non-blocking)
        try:
            from app.modules.auth.service import brevo_email_sender
            subject, html = welcome_premium_email(user.email, period_end)
            await brevo_email_sender(user.email, subject, html)
        except Exception as exc:
            logger.warning("Failed to send billing email to %s: %s", user.email, exc)

    async def handle_invoice_paid(self, invoice_data: dict, db: AsyncSession) -> None:
        """invoice.paid / invoice.payment_succeeded — renew access."""
        stripe_customer_id = invoice_data.get("customer")
        subscription_id = invoice_data.get("subscription")
        if not stripe_customer_id:
            return

        # Busca o usuário primeiro para validar a assinatura do invoice
        result = await db.execute(
            select(User).where(User.stripe_customer_id == stripe_customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return

        # Ignora invoices de assinaturas antigas — apenas a assinatura atual é processada
        if subscription_id and subscription_id != user.stripe_subscription_id:
            logger.info(
                "billing.invoice_paid_ignored user_id=%s old_sub=%s...%s current_sub=%s...%s",
                user.id,
                subscription_id[:8], subscription_id[-4:],
                (user.stripe_subscription_id or "")[:8],
                (user.stripe_subscription_id or "")[-4:],
            )
            return

        # Update subscription record status if it exists
        if subscription_id:
            from app.modules.billing.models import Subscription
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == subscription_id
                )
            )
            sub_row = result.scalar_one_or_none()
            if sub_row:
                sub_row.plan = "pro"
                sub_row.status = "active"

        await db.execute(
            update(User)
            .where(User.id == user.id)
            .values(plan="pro", subscription_status="active")
        )
        await db.flush()

        # Send payment-received confirmation (non-blocking)
        try:
            from app.modules.auth.service import brevo_email_sender
            subject, html = payment_received_email(
                user.email, user.subscription_current_period_end
            )
            await brevo_email_sender(user.email, subject, html)
        except Exception as exc:
            logger.warning("Failed to send billing email for customer %s: %s", stripe_customer_id, exc)

    async def handle_payment_failed(self, invoice_data: dict, db: AsyncSession) -> None:
        """invoice.payment_failed — keep plan but update status for display."""
        stripe_customer_id = invoice_data.get("customer")
        subscription_id = invoice_data.get("subscription")
        if not stripe_customer_id:
            return

        if subscription_id:
            from app.modules.billing.models import Subscription
            result = await db.execute(
                select(Subscription).where(
                    Subscription.stripe_subscription_id == subscription_id
                )
            )
            sub_row = result.scalar_one_or_none()
            if sub_row:
                sub_row.status = "past_due"

        await db.execute(
            update(User)
            .where(User.stripe_customer_id == stripe_customer_id)
            .values(subscription_status="past_due")
        )
        await db.flush()

        # Send payment-failed warning (non-blocking)
        try:
            from app.modules.auth.service import brevo_email_sender
            result = await db.execute(
                select(User).where(User.stripe_customer_id == stripe_customer_id)
            )
            failed_user = result.scalar_one_or_none()
            if failed_user:
                subject, html = payment_failed_email(failed_user.email)
                await brevo_email_sender(failed_user.email, subject, html)
        except Exception as exc:
            logger.warning("Failed to send billing email for customer %s: %s", stripe_customer_id, exc)

    async def handle_subscription_changed(self, sub_data: dict, db: AsyncSession) -> None:
        """customer.subscription.updated / .deleted — sync status."""
        subscription_id = sub_data["id"]
        new_status = sub_data.get("status")
        new_plan = "pro" if new_status in ("active", "trialing") else "free"
        period_end = sub_data.get("current_period_end")
        period_end_dt = (
            datetime.fromtimestamp(period_end, tz=timezone.utc) if period_end else None
        )

        # Update subscription record
        from app.modules.billing.models import Subscription
        result = await db.execute(
            select(Subscription).where(
                Subscription.stripe_subscription_id == subscription_id
            )
        )
        sub_row = result.scalar_one_or_none()
        if sub_row:
            sub_row.plan = new_plan
            sub_row.status = new_status or sub_row.status
            sub_row.current_period_end = period_end_dt

        # Update user plan (access-control)
        await db.execute(
            update(User)
            .where(User.stripe_subscription_id == subscription_id)
            .values(
                plan=new_plan,
                subscription_status=new_status,
                subscription_current_period_end=period_end_dt,
            )
        )
        await db.flush()

        # Send cancellation email when plan downgrades to free (non-blocking)
        if new_plan == "free":
            try:
                from app.modules.auth.service import brevo_email_sender
                result = await db.execute(
                    select(User).where(User.stripe_subscription_id == subscription_id)
                )
                changed_user = result.scalar_one_or_none()
                if changed_user:
                    subject, html = subscription_canceled_email(changed_user.email)
                    await brevo_email_sender(changed_user.email, subject, html)
            except Exception as exc:
                logger.warning(
                    "Failed to send cancellation email for subscription %s: %s",
                    subscription_id,
                    exc,
                )


billing_service = BillingService()
