# Phase 6: Monetization - Research

**Researched:** 2026-03-16
**Domain:** Stripe subscriptions, plan enforcement, freemium gating (FastAPI + Next.js 15)
**Confidence:** HIGH

---

## Summary

This phase adds Stripe subscription billing in BRL (cartão de crédito), enforces plan tiers at the API and UI layers, and provides an admin subscriber dashboard. The project already has the foundational pieces in place: the `User.plan` field exists in the `users` table, the `PremiumGate` component exists in the AI feature, and the `/me` endpoint returns plan status. Phase 6 adds the Stripe integration layer that drives `User.plan` transitions, the plans/pricing page, and the admin view.

**Key constraint identified:** PIX does not support recurring subscriptions in Stripe. Phase 6 uses cartão de crédito only. PIX recurring is deferred to v2 (PAY-01 via Asaas/Pagar.me). Credit cards work correctly for BRL subscriptions on Stripe.

**Stripe Brazil account note:** CPF/CNPJ requirements apply to the *merchant Stripe account* (the business account receiving payouts), not to customer checkout. No CPF collection is required from end customers for standard card payments.

**Primary recommendation:** Use stripe-python 14.x with the new `StripeClient` pattern and `HTTPXClient` for async. Use Stripe Checkout (hosted redirect) for the subscription flow — lowest complexity (2/5), handles SCA/3DS automatically, no custom card form needed for v1. Store `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, and `current_period_end` on the existing `users` table or a new `subscriptions` table within the tenant schema.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MON-01 | Two plans: Gratuito (carteira básica, sem IA) and Premium (análise IA completa) — enforced at API and UI | Plan enforcement via FastAPI Depends(_require_premium) already used in AI module; needs to be formalized and applied to all premium endpoints |
| MON-02 | User can subscribe to Premium via Stripe (cartão de crédito, BRL) — webhook drives plan status | Stripe Checkout (hosted) + subscription webhooks; `checkout.session.completed` + `invoice.paid` → set `User.plan = "pro"` |
| MON-03 | Free-tier users see blocked premium features with preview + contextual upgrade CTA | PremiumGate component already built; needs `/planos` page as CTA destination and plan enforcement extended to any new premium endpoints |
| MON-04 | Admin can view subscribers, plan, and payment status — no manual DB query | Stripe `subscriptions.list()` + local DB query; admin endpoint at `/admin/subscribers` |
</phase_requirements>

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| stripe | 14.4.1 | Stripe Python SDK — checkout sessions, webhooks, billing portal, subscriptions list | Official SDK; v14 is current as of 2026-03. Use `StripeClient` (new instance pattern, not global `stripe.api_key`) |
| httpx | 0.27.2 (already installed) | Async HTTP client for stripe-python | Already in requirements; stripe uses `HTTPXClient` for async calls |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Stripe CLI | latest | Local webhook testing via `stripe listen --forward-to` | Dev only — not a Python package, installed separately |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Stripe Checkout (hosted) | Stripe Payment Element (embedded) | Payment Element requires custom form; Checkout handles 3DS/SCA automatically. Use Checkout for v1 |
| Credit card only | PIX | PIX does not support recurring subscriptions in Stripe. PIX is one-time only. Deferred to v2 |
| Storing subscription data in `users` table | Separate `subscriptions` table | For v1 single-plan freemium, adding columns to `users` is simpler. If multiple plans/history needed, use separate table. Recommend separate `billing` table for cleanliness |

**Installation:**
```bash
pip install stripe==14.4.1
```

Frontend: Stripe.js is loaded via CDN in the checkout redirect — no npm package needed for hosted Checkout.

---

## Architecture Patterns

### Recommended Project Structure

```
backend/app/modules/billing/    # new module
├── __init__.py
├── models.py                   # SubscriptionRecord (optional — mirrors webhook state)
├── router.py                   # /billing/checkout, /billing/portal, /billing/webhook
├── schemas.py
└── service.py                  # BillingService — Stripe calls + DB updates

frontend/src/features/billing/  # new feature
├── components/
│   ├── PricingCard.tsx         # Plan comparison card
│   └── UpgradeCTA.tsx          # Reusable upgrade call-to-action
├── api.ts                      # createCheckoutSession(), createPortalSession()
└── hooks/
    └── useSubscription.ts

frontend/app/planos/            # new page
└── page.tsx                    # /planos — pricing page with Stripe Checkout trigger
```

### Pattern 1: Stripe Checkout Flow (Backend)

**What:** Backend creates a Checkout Session and returns the URL; frontend redirects the browser to it.
**When to use:** All subscription purchases in v1.

```python
# Source: https://docs.stripe.com/payments/checkout/build-subscriptions
from stripe import StripeClient, HTTPXClient
from app.core.config import settings

_stripe = StripeClient(
    api_key=settings.STRIPE_SECRET_KEY,
    http_client=HTTPXClient(),
)

async def create_checkout_session(
    customer_id: str,
    price_id: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Returns the Stripe Checkout hosted URL."""
    session = await _stripe.checkout.sessions.create_async(
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
```

### Pattern 2: Stripe Customer Portal (Backend)

**What:** Creates a short-lived portal session URL; redirect the user to it for self-service cancellation/payment method update.

```python
# Source: https://docs.stripe.com/customer-management/integrate-customer-portal
async def create_portal_session(customer_id: str, return_url: str) -> str:
    session = await _stripe.billing_portal.sessions.create_async(
        params={
            "customer": customer_id,
            "return_url": return_url,
        }
    )
    return session.url
```

### Pattern 3: Webhook Handler (FastAPI)

**What:** Receives Stripe events, verifies signature, dispatches to idempotent handlers.

**CRITICAL:** Use `await request.body()` BEFORE any JSON parsing. FastAPI's `Request.body()` returns raw bytes without modification. Never use `await request.json()` in the webhook endpoint — it manipulates the payload and breaks signature verification.

```python
# Source: https://docs.stripe.com/webhooks/signature
@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()  # raw bytes — mandatory for signature check
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = _stripe.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except Exception:  # SignatureVerificationError
        raise HTTPException(status_code=400, detail="Invalid signature")

    event_type = event["type"]
    data = event["data"]["object"]

    # Idempotent: check processed events by event ID before acting
    if event_type == "checkout.session.completed":
        await _handle_checkout_completed(data, db)
    elif event_type in ("invoice.paid", "invoice.payment_succeeded"):
        await _handle_invoice_paid(data, db)
    elif event_type == "invoice.payment_failed":
        await _handle_payment_failed(data, db)
    elif event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        await _handle_subscription_changed(data, db)

    return {"status": "ok"}
```

### Pattern 4: Webhook Event Handling (Idempotent)

**What:** Each handler updates the local DB to mirror Stripe's subscription state. Must be idempotent — same event can arrive multiple times.

```python
# Source: Stripe docs — https://docs.stripe.com/billing/subscriptions/webhooks
async def _handle_checkout_completed(session: dict, db: AsyncSession) -> None:
    """checkout.session.completed — subscription created, provision access."""
    stripe_customer_id = session["customer"]
    subscription_id = session["subscription"]

    # Fetch full subscription to get current status
    sub = await _stripe.subscriptions.retrieve_async(subscription_id)

    await db.execute(
        update(User)
        .where(User.stripe_customer_id == stripe_customer_id)
        .values(
            plan="pro",
            stripe_subscription_id=subscription_id,
            subscription_status=sub.status,
            subscription_current_period_end=datetime.fromtimestamp(
                sub.current_period_end, tz=timezone.utc
            ),
        )
    )
    await db.commit()

async def _handle_subscription_changed(sub: dict, db: AsyncSession) -> None:
    """customer.subscription.updated / .deleted — sync status."""
    new_plan = "pro" if sub["status"] in ("active", "trialing") else "free"
    await db.execute(
        update(User)
        .where(User.stripe_subscription_id == sub["id"])
        .values(
            plan=new_plan,
            subscription_status=sub["status"],
            subscription_current_period_end=datetime.fromtimestamp(
                sub["current_period_end"], tz=timezone.utc
            ),
        )
    )
    await db.commit()
```

### Pattern 5: FastAPI Plan Enforcement Dependency

**What:** Reusable Depends() that raises 403 for non-premium users. Already established in `app/modules/ai/router.py` — formalize it as a shared core dependency.

```python
# Move to app/core/plan_gate.py for reuse across modules
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db
from app.core.security import get_current_user
from app.modules.auth.models import User

async def require_premium(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
) -> User:
    """Dependency: raise 403 if user is on free plan.

    Reads plan from DB (not JWT) to avoid stale plan state.
    Return the User object so handlers can access user fields if needed.
    """
    user_id = current_user["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or user.plan == "free":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLAN_UPGRADE_REQUIRED",
                "message": "Recurso exclusivo do plano Premium.",
                "upgrade_url": "/planos",
            },
        )
    return user

# Usage in any premium endpoint:
@router.post("/analyze/{ticker}")
async def request_analysis(
    ticker: str,
    _user: User = Depends(require_premium),  # 403 if free
    ...
):
    ...
```

### Pattern 6: Stripe Customer Creation (first-time checkout)

**What:** Create a Stripe Customer on first checkout; store `stripe_customer_id` in the `users` table for future portal sessions.

```python
async def get_or_create_stripe_customer(user: User) -> str:
    if user.stripe_customer_id:
        return user.stripe_customer_id
    customer = await _stripe.customers.create_async(
        params={"email": user.email, "metadata": {"user_id": user.id}}
    )
    # Persist immediately
    await db.execute(
        update(User).where(User.id == user.id).values(stripe_customer_id=customer.id)
    )
    await db.commit()
    return customer.id
```

### Pattern 7: Admin Subscriber List

**What:** Query the local DB (not Stripe API) for the admin list — DB has all needed fields after webhook sync. Stripe API call is a fallback for data not in the DB.

```python
# admin endpoint: GET /admin/subscribers
# Requires is_admin flag on User model or a hardcoded admin user_id check

@router.get("/subscribers")
async def list_subscribers(
    db: AsyncSession = Depends(get_authed_db),
    _admin: dict = Depends(require_admin),
):
    result = await db.execute(
        select(User)
        .where(User.plan == "pro")
        .order_by(User.created_at.desc())
    )
    users = result.scalars().all()
    return [
        {
            "user_id": u.id,
            "email": u.email,
            "plan": u.plan,
            "subscription_status": u.subscription_status,
            "stripe_customer_id": u.stripe_customer_id,
            "current_period_end": u.subscription_current_period_end,
        }
        for u in users
    ]
```

### Anti-Patterns to Avoid

- **Never trust the JWT for plan status:** The existing codebase already reads plan from DB on each request. This is correct. Never embed plan in the JWT payload — it goes stale when Stripe webhooks update the plan.
- **Never verify webhook from JSON body:** Only use `await request.body()` (raw bytes) for webhook signature verification. Any JSON parsing beforehand will corrupt the payload hash.
- **Never skip idempotency in webhook handlers:** Stripe delivers events at-least-once. Always check if the subscription_id or event has already been processed.
- **Never use `stripe.api_key = ...` global pattern:** The new StripeClient instance pattern is required for async. Global state is incompatible with async frameworks.
- **Never use PIX for subscriptions:** PIX does not support recurring payments in Stripe. BRL card-only for subscriptions in v1.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Card payment form | Custom card input fields | Stripe Checkout (hosted redirect) | PCI compliance, 3DS/SCA handling, BRL formatting all automatic |
| Subscription state machine | Custom status transitions | Stripe webhook events drive DB state | Stripe handles retries, dunning, grace periods, cancellation |
| Customer portal | Custom cancel/update UI | Stripe Billing Portal API | Self-service plan management, payment method updates — hours to configure |
| Webhook signature validation | Custom HMAC logic | `stripe_client.construct_event()` | Constant-time comparison, timing attack prevention built in |
| Retry/dunning logic | Custom payment retry | Stripe Smart Retries (automatic) | Stripe retries failed payments automatically per account settings |
| Invoice management | Custom invoicing | Stripe handles invoices for subscriptions | Invoices created, sent, and tracked automatically |

**Key insight:** Stripe subscriptions are a state machine. Any custom state management that doesn't mirror Stripe's states will diverge from reality. Webhooks are the single source of truth.

---

## Common Pitfalls

### Pitfall 1: Webhook Raw Body Mutation
**What goes wrong:** FastAPI JSON body parsing is called before signature verification; signature check fails with 400 on all events.
**Why it happens:** Developers use `await request.json()` or add `Body()` parameter to webhook endpoint — this parses and re-serializes JSON, changing whitespace/key order.
**How to avoid:** Webhook endpoint must use `payload = await request.body()` (returns raw `bytes`). Never add a Pydantic model as the request body parameter.
**Warning signs:** `stripe.error.SignatureVerificationError` in logs during local testing with Stripe CLI.

### Pitfall 2: Webhook Endpoint Requires Auth
**What goes wrong:** The billing webhook endpoint is accidentally protected by `get_authed_db` or `get_current_user` — Stripe calls return 401/403.
**Why it happens:** Developers apply auth middleware globally and forget to exempt `/billing/webhook`.
**How to avoid:** The webhook route must use `get_db()` (unauthenticated DB session), not `get_authed_db()`. No JWT cookie is present in Stripe's HTTP request. Add to CORS exceptions if needed.
**Warning signs:** Stripe Dashboard shows webhook delivery failures (401/403 responses).

### Pitfall 3: Stale Plan After Checkout
**What goes wrong:** User completes checkout but still sees "free" UI because the checkout session response is used to update the plan instead of waiting for the webhook.
**Why it happens:** The `checkout.session.completed` webhook may arrive seconds after the redirect. The success page loads before the plan is updated in the DB.
**How to avoid:** On the success page, poll `/me` until `plan == "pro"` or show a "Processing..." state for up to 10 seconds. Never update `User.plan` from the redirect — only from webhooks.
**Warning signs:** User reports plan not updating after payment.

### Pitfall 4: Missing Stripe Customer ID on Portal Redirect
**What goes wrong:** Billing portal endpoint fails because `User.stripe_customer_id` is NULL.
**Why it happens:** `stripe_customer_id` is only set during first checkout. A user who never checked out has no customer ID.
**How to avoid:** In the portal endpoint, check for `stripe_customer_id` and return a meaningful error (redirect to pricing) if NULL. Create the customer lazily on portal access if preferred.

### Pitfall 5: Webhook Not Receiving Events Locally
**What goes wrong:** Webhook endpoint never gets triggered during local development.
**Why it happens:** Stripe cannot reach `localhost`. Developers skip Stripe CLI setup.
**How to avoid:** Use `stripe listen --forward-to localhost:8100/billing/webhook`. The CLI prints a `STRIPE_WEBHOOK_SECRET` (`whsec_...`) — use this value only for local dev; production uses the Stripe Dashboard webhook secret.

### Pitfall 6: stripe-python v12+ Breaking Change
**What goes wrong:** Code uses old `stripe.checkout.Session.create()` pattern — breaks on v12+ due to API version `2025-03-31.basil` which changes subscription lifecycle.
**Why it happens:** Tutorials and examples use the old `stripe.Resource.method()` global pattern.
**How to avoid:** Use `StripeClient` instance pattern: `client.checkout.sessions.create_async(params={...})`. Also: in v12+, Checkout Sessions for subscriptions postpone subscription creation until after payment — the `subscription` field in `checkout.session.completed` may be null; retrieve the subscription from the session object instead.

### Pitfall 7: Brazil Merchant Account CPF Requirement (Merchant, Not Customer)
**What goes wrong:** Confusion between CPF requirements for the *Stripe merchant account* (the business) vs CPF for *customers making payments*.
**Why it happens:** Stripe's Brazil docs discuss CPF/CNPJ extensively in the context of account verification.
**How to avoid:** Customer CPF is NOT required for card payments. The merchant Stripe account must be verified with CPF (individual) or CNPJ (company). No need to collect CPF from end users for standard credit card subscriptions.

---

## Code Examples

### Creating Stripe Products and Prices (One-time Setup)

```python
# Run once via script or Stripe Dashboard — not in application code
# Source: https://docs.stripe.com/api/products/create

# Create product
product = await client.products.create_async(params={
    "name": "InvestIQ Premium",
    "description": "Análise IA completa — DCF, valuation, impacto macro",
})

# Create price in BRL, monthly
price = await client.prices.create_async(params={
    "product": product.id,
    "unit_amount": 4990,  # R$49,90 in centavos
    "currency": "brl",
    "recurring": {"interval": "month"},
})
# Store price.id as STRIPE_PREMIUM_PRICE_ID in config/env
```

### Checkout Session — Full FastAPI Endpoint

```python
# Source: Stripe docs + project pattern
@router.post("/checkout")
async def create_checkout_session(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_authed_db),
):
    user_id = current_user["user_id"]
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one()

    # Create Stripe customer if not exists
    customer_id = await billing_service.get_or_create_customer(user, db)

    session = await billing_service.create_checkout_session(
        customer_id=customer_id,
        price_id=settings.STRIPE_PREMIUM_PRICE_ID,
        success_url=f"{settings.APP_URL}/planos/sucesso",
        cancel_url=f"{settings.APP_URL}/planos",
    )
    return {"checkout_url": session}
```

### Subscription Status — Access Control Logic

```python
# Which statuses grant premium access
PREMIUM_STATUSES = {"active", "trialing"}

def user_has_premium_access(subscription_status: str | None, plan: str) -> bool:
    """User has premium access if plan == "pro" AND status is active/trialing.

    The `plan` field on User is the canonical value — updated by webhooks.
    subscription_status is for display/admin only.
    """
    return plan == "pro" and subscription_status in PREMIUM_STATUSES
```

### Next.js Checkout Redirect (Client Component)

```typescript
// Source: project pattern — apiClient calls POST /billing/checkout
async function handleUpgrade() {
  const { checkout_url } = await apiClient<{ checkout_url: string }>("/billing/checkout", {
    method: "POST",
  });
  window.location.href = checkout_url;  // redirect to Stripe hosted page
}
```

### Stripe CLI — Local Development

```bash
# Install Stripe CLI (Windows via scoop or direct download)
# https://docs.stripe.com/stripe-cli

# Terminal 1: forward events to local backend
stripe listen --forward-to localhost:8100/billing/webhook
# Output: "Your webhook signing secret is 'whsec_...'"
# Set STRIPE_WEBHOOK_SECRET=whsec_... in .env for local dev only

# Terminal 2: trigger test events
stripe trigger checkout.session.completed
stripe trigger customer.subscription.updated
stripe trigger invoice.payment_failed
```

---

## Schema Changes Required

The `users` table needs new columns (Alembic migration required):

```python
# Add to User model in auth/models.py
stripe_customer_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
stripe_subscription_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
subscription_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
# current_period_end — when current billing period ends (for grace period / display)
subscription_current_period_end: Mapped[datetime | None] = mapped_column(
    DateTime(timezone=True), nullable=True
)
```

**Why on `users` not a separate `subscriptions` table:** v1 has one subscription per user maximum. The `User.plan` field already exists and is the access-control field. Adding billing columns to `users` avoids a join on every auth check. A `billing` module table is optional for audit history.

**Admin access pattern:** Add `is_admin` boolean to `User` or use a hardcoded admin email list via `settings.ADMIN_EMAILS`. No separate admin user model needed for v1.

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `stripe.api_key = ...` global | `StripeClient(api_key, http_client=HTTPXClient())` instance | stripe-python v8 | Async-safe, testable, no global state |
| `stripe.checkout.Session.create()` | `client.checkout.sessions.create_async(params={...})` | stripe-python v8 | Required for async frameworks |
| Subscription created at Checkout Session creation | Subscription created after payment completes | stripe-python v12 / API 2025-03 | `subscription` field in session may be null; retrieve from subscription_id post-payment |
| Manual plan update after payment | Webhook-driven plan update only | Best practice since 2022 | Prevents race conditions, handles async payment methods |
| Custom cancel page | Stripe Billing Portal | 2020+ | No-code customer self-service |

**Deprecated/outdated:**
- `stripe.Webhook.construct_event()` (old global pattern): Still works but use `client.construct_event()` with StripeClient pattern for consistency.
- `async-stripe` (PyPI): Third-party async wrapper. Unnecessary since stripe-python added native async in v8+.

---

## Open Questions

1. **Admin authentication for `/admin/subscribers`**
   - What we know: No admin role/flag exists on `User` model yet
   - What's unclear: Should admin be a hardcoded email list in `settings.ADMIN_EMAILS`, or a DB flag `User.is_admin`?
   - Recommendation: Use `settings.ADMIN_EMAILS: list[str]` for v1 — no DB change needed, configurable via env var

2. **Stripe Product/Price setup timing**
   - What we know: `STRIPE_PREMIUM_PRICE_ID` must exist before any checkout session can be created
   - What's unclear: Is this a manual dashboard step or automated via script?
   - Recommendation: Manual Stripe Dashboard setup during Wave 0 of the plan; store the price ID in `settings.STRIPE_PREMIUM_PRICE_ID` (env var, fetched from AWS SM)

3. **Success page polling timeout**
   - What we know: Webhook arrives seconds after checkout redirect; plan may be "free" momentarily on the success page
   - What's unclear: How long to poll before showing "contact support"?
   - Recommendation: Poll `/me` every 2 seconds, up to 15 seconds (7 attempts), then show "Seu upgrade está sendo processado" with support contact

4. **Webhook idempotency storage**
   - What we know: Stripe can deliver events multiple times
   - What's unclear: Should we store processed event IDs in Redis or a DB table?
   - Recommendation: For v1, use idempotent DB updates (upsert by `stripe_customer_id`) — a duplicate event is harmless since it writes the same values. No event ID tracking needed unless audit log is required.

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (already installed) |
| Config file | `backend/pyproject.toml` (or `pytest.ini` — check existing) |
| Quick run command | `cd backend && pytest tests/test_billing.py -x -q` |
| Full suite command | `cd backend && pytest tests/ -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MON-01 | Free user gets 403 on premium endpoints | unit | `pytest tests/test_billing.py::test_free_user_blocked -x` | ❌ Wave 0 |
| MON-01 | Pro user passes premium endpoint | unit | `pytest tests/test_billing.py::test_pro_user_allowed -x` | ❌ Wave 0 |
| MON-02 | checkout endpoint returns Stripe URL | unit (mocked Stripe) | `pytest tests/test_billing.py::test_create_checkout_session -x` | ❌ Wave 0 |
| MON-02 | webhook `checkout.session.completed` sets plan=pro | unit | `pytest tests/test_billing.py::test_webhook_checkout_completed -x` | ❌ Wave 0 |
| MON-02 | webhook `customer.subscription.deleted` sets plan=free | unit | `pytest tests/test_billing.py::test_webhook_subscription_deleted -x` | ❌ Wave 0 |
| MON-02 | webhook rejects invalid signature | unit | `pytest tests/test_billing.py::test_webhook_invalid_signature -x` | ❌ Wave 0 |
| MON-03 | `/planos` page renders for free user | smoke (manual) | Manual — Next.js frontend page | N/A |
| MON-04 | admin endpoint lists subscribers with plan=pro | unit | `pytest tests/test_billing.py::test_admin_subscribers_list -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && pytest tests/test_billing.py -x -q`
- **Per wave merge:** `cd backend && pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_billing.py` — all billing unit tests (plan gate, webhook events, checkout, admin)
- [ ] Stripe mock fixture in `conftest.py` — mock `StripeClient` for unit tests without real Stripe calls
- [ ] `settings.STRIPE_SECRET_KEY`, `settings.STRIPE_WEBHOOK_SECRET`, `settings.STRIPE_PREMIUM_PRICE_ID` added to `Settings` class in `app/core/config.py`
- [ ] Alembic migration for new `users` columns: `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, `subscription_current_period_end`

---

## Sources

### Primary (HIGH confidence)
- [Stripe Webhook Docs](https://docs.stripe.com/webhooks) — event handling, signature verification
- [Stripe Subscriptions Webhook Events](https://docs.stripe.com/billing/subscriptions/webhooks) — event lifecycle
- [Stripe Checkout Build Subscriptions](https://docs.stripe.com/payments/checkout/build-subscriptions) — Python code patterns
- [stripe-python StripeClient Migration](https://github.com/stripe/stripe-python/wiki/Migration-guide-for-v8-(StripeClient)) — new async-safe API pattern
- [stripe-python on PyPI](https://pypi.org/project/stripe/) — version 14.4.1 confirmed current
- [stripe-python async support (DeepWiki)](https://deepwiki.com/stripe/stripe-python/6.2-async-support) — HTTPXClient + StripeClient setup
- [Stripe Billing Portal API](https://docs.stripe.com/customer-management/integrate-customer-portal) — portal session creation
- [Stripe Subscription Object](https://docs.stripe.com/api/subscriptions/object) — status values, fields
- [Stripe PIX Docs](https://docs.stripe.com/payments/pix) — confirmed PIX does NOT support recurring subscriptions

### Secondary (MEDIUM confidence)
- [FastAPI Stripe Integration Tutorial (FastSaaS, 2025)](https://www.fast-saas.com/blog/fastapi-stripe-integration/) — `await request.body()` pattern confirmed
- [Stripe Brazil Verification Requirements (2025)](https://support.stripe.com/questions/2025-updates-to-brazil-verification-requirements) — merchant account CPF/CNPJ (not customer-side)
- [Stripe CLI Docs](https://docs.stripe.com/stripe-cli/use-cli) — `stripe listen --forward-to` pattern
- Project codebase: `PremiumGate.tsx`, `AIContent.tsx`, `ai/router.py` — existing patterns to follow/extend

### Tertiary (LOW confidence)
- None — all critical claims verified with official Stripe documentation or project codebase inspection.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — stripe-python 14.4.1 verified on PyPI; httpx already in requirements
- Architecture: HIGH — Stripe Checkout + webhook pattern verified in official docs; PIX limitation confirmed in official docs
- Schema changes: HIGH — existing User model inspected; new columns identified
- Brazil/BRL restrictions: HIGH — PIX limitation confirmed; CPF requirement is merchant-side only (confirmed)
- Pitfalls: HIGH — verified against official docs and project codebase patterns
- Admin dashboard: MEDIUM — pattern is straightforward DB query; admin auth mechanism left as open question

**Research date:** 2026-03-16
**Valid until:** 2026-04-16 (stable — Stripe SDK versioned, PIX subscription status unlikely to change)
