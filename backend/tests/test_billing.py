"""Billing tests — Wave 0 stubs. All tests fail RED until 06-01 Task 2 ships.

Tests MON-02 requirements:
- POST /billing/checkout returns Stripe Checkout URL for authenticated user
- POST /billing/webhook processes checkout.session.completed (plan → pro)
- POST /billing/webhook processes customer.subscription.deleted (plan → free)
- POST /billing/webhook rejects invalid signature with 400
- GET /admin/subscribers stub (fully implemented in 06-02)
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient
from sqlalchemy import update
from tests.conftest import register_verify_and_login
from app.modules.auth.models import User


@pytest.mark.asyncio
async def test_create_checkout_session(client: AsyncClient, email_stub, mock_stripe_client):
    """POST /billing/checkout returns Stripe checkout URL."""
    await register_verify_and_login(client, email_stub)
    resp = await client.post("/billing/checkout")
    assert resp.status_code == 200
    data = resp.json()
    assert "checkout_url" in data
    assert data["checkout_url"].startswith("https://checkout.stripe.com/")


@pytest.mark.asyncio
async def test_webhook_checkout_completed(client: AsyncClient, db_session, email_stub, mock_stripe_client):
    """checkout.session.completed webhook sets user.plan='pro'."""
    from sqlalchemy import select, update
    from app.modules.auth.models import User

    user_id = await register_verify_and_login(client, email_stub, email="stripe@test.com")
    # Set up stripe_customer_id on the user so webhook can find them
    # Use flush() not commit() — the fixture's begin() transaction must stay open
    await db_session.execute(
        update(User)
        .where(User.id == user_id)
        .values(stripe_customer_id="cus_test123")
    )
    await db_session.flush()

    # Mock construct_event to return checkout.session.completed
    mock_stripe_client.construct_event.return_value = {
        "id": "evt_checkout_test",
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_test123", "subscription": "sub_test123"}},
    }
    resp = await client.post(
        "/billing/webhook",
        content=b'{"type":"checkout.session.completed"}',
        headers={"stripe-signature": "t=1234,v1=valid_sig"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.plan == "pro"


@pytest.mark.asyncio
async def test_webhook_subscription_deleted(client: AsyncClient, db_session, email_stub, mock_stripe_client):
    """customer.subscription.deleted webhook sets user.plan='free'."""
    from sqlalchemy import select, update
    from app.modules.auth.models import User

    user_id = await register_verify_and_login(client, email_stub, email="cancel@test.com")
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            plan="pro", stripe_subscription_id="sub_test123"
        )
    )
    await db_session.flush()

    mock_stripe_client.construct_event.return_value = {
        "id": "evt_sub_deleted_test",
        "type": "customer.subscription.deleted",
        "data": {"object": {
            "id": "sub_test123", "status": "canceled",
            "current_period_end": 9999999999,
        }},
    }
    resp = await client.post(
        "/billing/webhook",
        content=b'{"type":"customer.subscription.deleted"}',
        headers={"stripe-signature": "t=1234,v1=valid_sig"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.plan == "free"


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client: AsyncClient, mock_stripe_client):
    """Webhook with invalid signature returns 400."""
    mock_stripe_client.construct_event.side_effect = Exception("Invalid signature")
    resp = await client.post(
        "/billing/webhook",
        content=b'{"type":"checkout.session.completed"}',
        headers={"stripe-signature": "t=bad,v1=bad"},
    )
    assert resp.status_code == 400
    # Reset side_effect for other tests
    mock_stripe_client.construct_event.side_effect = None


@pytest.mark.asyncio
async def test_admin_subscribers_list(client: AsyncClient, email_stub, db_session, mock_stripe_client):
    """GET /admin/subscribers returns pro subscribers for admin user."""
    from unittest.mock import patch
    from sqlalchemy import update
    from app.modules.auth.models import User
    from app.core.config import settings

    # Create admin user and a pro subscriber
    admin_id = await register_verify_and_login(client, email_stub, email="admin@investiq.com")
    await client.post("/auth/logout")

    sub_id = await register_verify_and_login(client, email_stub, email="paid@test.com")
    await db_session.execute(
        update(User).where(User.id == sub_id).values(plan="pro", subscription_status="active")
    )
    await db_session.flush()
    await client.post("/auth/logout")

    # Log in as admin
    with patch.object(settings, "ADMIN_EMAILS", ["admin@investiq.com"]):
        await client.post("/auth/login", json={"email": "admin@investiq.com", "password": "SecurePass123!"})
        resp = await client.get("/billing/admin/subscribers")

    assert resp.status_code == 200
    data = resp.json()
    emails = [s["email"] for s in data]
    assert "paid@test.com" in emails
    assert all(s["plan"] != "free" for s in data)


@pytest.mark.asyncio
async def test_admin_subscribers_forbidden_for_non_admin(client: AsyncClient, email_stub):
    """GET /admin/subscribers returns 403 for regular users."""
    await register_verify_and_login(client, email_stub, email="regular@test.com")
    resp = await client.get("/billing/admin/subscribers")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_webhook_idempotency(client: AsyncClient, db_session, email_stub, mock_stripe_client):
    """Same Stripe event_id processed twice: second call is a no-op."""
    from sqlalchemy import select, update
    from app.modules.auth.models import User
    from app.modules.billing.models import StripeEvent

    user_id = await register_verify_and_login(client, email_stub, email="idempotent@test.com")
    await db_session.execute(
        update(User).where(User.id == user_id).values(stripe_customer_id="cus_test123")
    )
    await db_session.flush()

    mock_stripe_client.construct_event.return_value = {
        "id": "evt_idempotency_001",
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_test123", "subscription": "sub_test123"}},
    }

    resp1 = await client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=s"})
    assert resp1.status_code == 200

    resp2 = await client.post("/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=s"})
    assert resp2.status_code == 200

    # Only one StripeEvent row for this event_id
    result = await db_session.execute(
        select(StripeEvent).where(StripeEvent.id == "evt_idempotency_001")
    )
    assert len(result.scalars().all()) == 1


@pytest.mark.asyncio
async def test_billing_metrics(client: AsyncClient, db_session, email_stub, mock_stripe_client):
    """GET /billing/admin/metrics returns correct plan counts."""
    from unittest.mock import patch
    from sqlalchemy import update
    from app.modules.auth.models import User
    from app.core.config import settings

    admin_id = await register_verify_and_login(client, email_stub, email="metrics_admin@test.com")
    await client.post("/auth/logout")

    pro_id = await register_verify_and_login(client, email_stub, email="metrics_pro@test.com")
    await db_session.execute(
        update(User).where(User.id == pro_id).values(plan="pro", subscription_status="active")
    )
    await db_session.flush()
    await client.post("/auth/logout")

    with patch.object(settings, "ADMIN_EMAILS", ["metrics_admin@test.com"]):
        await client.post("/auth/login", json={"email": "metrics_admin@test.com", "password": "SecurePass123!"})
        resp = await client.get("/billing/admin/metrics")

    assert resp.status_code == 200
    data = resp.json()
    assert data["pro_users"] >= 1
    assert data["active_subscriptions"] >= 1
    assert "free_users" in data
    assert "total_conversions" in data


@pytest.mark.asyncio
async def test_plan_gate_returns_structured_error(client: AsyncClient, db_session, email_stub):
    """Import limit 403 returns structured error with code and upgrade_url."""
    import io
    from unittest.mock import patch
    from app.core.plan_gate import FREE_IMPORTS_PER_MONTH

    user_id = await register_verify_and_login(client, email_stub, email="gatelimit@test.com")

    # Expire the trial so user is treated as free (not elevated to pro)
    past = datetime.now(tz=timezone.utc) - timedelta(days=1)
    await db_session.execute(
        update(User).where(User.id == user_id).values(trial_ends_at=past)
    )
    await db_session.flush()

    # Simulate already at limit by patching the constant
    with patch("app.core.plan_gate.FREE_IMPORTS_PER_MONTH", 0):
        fake_pdf = io.BytesIO(b"%PDF-1.4 fake")
        resp = await client.post(
            "/imports/pdf",
            files={"file": ("test.pdf", fake_pdf, "application/pdf")},
        )

    assert resp.status_code == 403
    body = resp.json()
    assert body["detail"]["code"] == "LIMIT_IMPORT"
    assert "upgrade_url" in body["detail"]


# ---------------------------------------------------------------------------
# Upgrade flow: duplicate subscription prevention (hotfix)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_checkout_completed_cancels_prior_subscription(
    client: AsyncClient, db_session, email_stub, mock_stripe_client
):
    """upgrade: prior subscription is canceled in Stripe before new one activates."""
    from unittest.mock import AsyncMock
    from sqlalchemy import select

    user_id = await register_verify_and_login(client, email_stub, email="upgrade@test.com")
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            stripe_customer_id="cus_upgrade",
            stripe_subscription_id="sub_prior_old",
        )
    )
    await db_session.flush()

    mock_stripe_client.subscriptions.cancel_async = AsyncMock()
    mock_stripe_client.construct_event.return_value = {
        "id": "evt_upgrade_001",
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_upgrade", "subscription": "sub_new_checkout"}},
    }

    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=s"},
    )
    assert resp.status_code == 200

    mock_stripe_client.subscriptions.cancel_async.assert_called_once_with("sub_prior_old")

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.stripe_subscription_id == "sub_new_checkout"
    assert user.plan == "pro"


@pytest.mark.asyncio
async def test_checkout_completed_cancel_fails_gracefully(
    client: AsyncClient, db_session, email_stub, mock_stripe_client
):
    """If Stripe cancellation of prior sub fails, new subscription is still created."""
    from unittest.mock import AsyncMock
    from sqlalchemy import select

    user_id = await register_verify_and_login(client, email_stub, email="cancel-fail@test.com")
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            stripe_customer_id="cus_cancelfail",
            stripe_subscription_id="sub_prior_failing",
        )
    )
    await db_session.flush()

    mock_stripe_client.subscriptions.cancel_async = AsyncMock(
        side_effect=Exception("stripe network error")
    )
    mock_stripe_client.construct_event.return_value = {
        "id": "evt_cancel_fail_001",
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_cancelfail", "subscription": "sub_new_despite_err"}},
    }

    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=s"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.stripe_subscription_id == "sub_new_despite_err"
    assert user.plan == "pro"


@pytest.mark.asyncio
async def test_checkout_completed_first_subscription_no_cancellation(
    client: AsyncClient, db_session, email_stub, mock_stripe_client
):
    """First-time subscriber: no Stripe cancellation is attempted (no prior sub)."""
    from unittest.mock import AsyncMock
    from sqlalchemy import select

    user_id = await register_verify_and_login(client, email_stub, email="firstsub@test.com")
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            stripe_customer_id="cus_firstsub",
            # stripe_subscription_id left NULL intentionally
        )
    )
    await db_session.flush()

    mock_stripe_client.subscriptions.cancel_async = AsyncMock()
    mock_stripe_client.construct_event.return_value = {
        "id": "evt_first_sub_001",
        "type": "checkout.session.completed",
        "data": {"object": {"customer": "cus_firstsub", "subscription": "sub_first"}},
    }

    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=s"},
    )
    assert resp.status_code == 200

    mock_stripe_client.subscriptions.cancel_async.assert_not_called()

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.stripe_subscription_id == "sub_first"
    assert user.plan == "pro"


@pytest.mark.asyncio
async def test_invoice_paid_ignores_old_subscription(
    client: AsyncClient, db_session, email_stub, mock_stripe_client
):
    """invoice.paid from an old sub does not overwrite current stripe_subscription_id."""
    from sqlalchemy import select

    user_id = await register_verify_and_login(client, email_stub, email="old-invoice@test.com")
    await db_session.execute(
        update(User).where(User.id == user_id).values(
            stripe_customer_id="cus_oldinv",
            stripe_subscription_id="sub_current",
            plan="pro",
        )
    )
    await db_session.flush()

    mock_stripe_client.construct_event.return_value = {
        "id": "evt_old_invoice_001",
        "type": "invoice.paid",
        "data": {"object": {"customer": "cus_oldinv", "subscription": "sub_old_abandoned"}},
    }

    resp = await client.post(
        "/billing/webhook",
        content=b"{}",
        headers={"stripe-signature": "t=1,v1=s"},
    )
    assert resp.status_code == 200

    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()
    assert user.stripe_subscription_id == "sub_current"  # unchanged
    assert user.plan == "pro"
