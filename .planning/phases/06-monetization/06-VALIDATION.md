---
phase: 6
slug: monetization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (already installed) |
| **Config file** | `backend/pyproject.toml` |
| **Quick run command** | `cd backend && pytest tests/test_billing.py -x -q` |
| **Full suite command** | `cd backend && pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `cd backend && pytest tests/test_billing.py -x -q`
- **After every plan wave:** Run `cd backend && pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 0 | MON-02 | wave0 | `pytest tests/test_billing.py -x -q` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | MON-02 | unit | `pytest tests/test_billing.py::test_create_checkout_session -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | MON-02 | unit | `pytest tests/test_billing.py::test_webhook_checkout_completed -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | MON-02 | unit | `pytest tests/test_billing.py::test_webhook_subscription_deleted -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | MON-02 | unit | `pytest tests/test_billing.py::test_webhook_invalid_signature -x` | ❌ W0 | ⬜ pending |
| 06-02-01 | 02 | 2 | MON-01 | unit | `pytest tests/test_billing.py::test_free_user_blocked -x` | ❌ W0 | ⬜ pending |
| 06-02-02 | 02 | 2 | MON-01 | unit | `pytest tests/test_billing.py::test_pro_user_allowed -x` | ❌ W0 | ⬜ pending |
| 06-02-03 | 02 | 2 | MON-03 | smoke | Manual — `/planos` page renders | N/A | ⬜ pending |
| 06-02-04 | 02 | 2 | MON-04 | unit | `pytest tests/test_billing.py::test_admin_subscribers_list -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `backend/tests/test_billing.py` — stubs for all billing unit tests (plan gate, webhook events, checkout, admin)
- [ ] `backend/tests/conftest.py` — Stripe mock fixture (`mock_stripe_client`) for unit tests without real Stripe calls
- [ ] `backend/app/core/config.py` — add `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PREMIUM_PRICE_ID` to `Settings`
- [ ] Alembic migration — new `users` columns: `stripe_customer_id`, `stripe_subscription_id`, `subscription_status`, `subscription_current_period_end`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `/planos` upgrade page renders with correct plan CTAs | MON-03 | Next.js frontend page — no automated browser test in scope | Navigate to `/planos` as free user; verify upgrade CTA visible; verify Premium features listed |
| Stripe Customer Portal redirects and loads | MON-02 | External Stripe-hosted page | Click "Gerenciar assinatura"; verify redirect to Stripe portal; verify subscription management visible |
| Free user sees PremiumGate overlay on AI Analysis section | MON-03 | Frontend visual verification | Log in as free user; navigate to AI analysis; verify blurred preview + upgrade CTA visible |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
