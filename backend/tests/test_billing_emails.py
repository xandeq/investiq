"""Tests for billing email template functions.

Run with:
    pytest backend/tests/test_billing_emails.py -v
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.modules.billing.email_templates import (
    payment_failed_email,
    payment_received_email,
    subscription_canceled_email,
    welcome_premium_email,
)

SAMPLE_EMAIL = "user@example.com"
SAMPLE_DATE = datetime(2026, 6, 15, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# welcome_premium_email
# ---------------------------------------------------------------------------


class TestWelcomePremiumEmail:
    def test_returns_tuple_of_strings(self) -> None:
        subject, html = welcome_premium_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject_contains_premium(self) -> None:
        subject, _ = welcome_premium_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "Premium" in subject

    def test_html_contains_dashboard_url(self) -> None:
        _, html = welcome_premium_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "dashboard" in html

    def test_html_contains_investiq(self) -> None:
        _, html = welcome_premium_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "InvestIQ" in html

    def test_html_contains_formatted_period_end(self) -> None:
        _, html = welcome_premium_email(SAMPLE_EMAIL, SAMPLE_DATE)
        # 15/06/2026
        assert "15/06/2026" in html

    def test_works_with_period_end_none(self) -> None:
        subject, html = welcome_premium_email(SAMPLE_EMAIL, None)
        assert isinstance(subject, str)
        assert isinstance(html, str)
        # Should show fallback text, not crash
        assert "em breve" in html

    def test_html_is_valid_html_shell(self) -> None:
        _, html = welcome_premium_email(SAMPLE_EMAIL, None)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_subject_is_not_empty(self) -> None:
        subject, _ = welcome_premium_email(SAMPLE_EMAIL, None)
        assert len(subject.strip()) > 0


# ---------------------------------------------------------------------------
# payment_received_email
# ---------------------------------------------------------------------------


class TestPaymentReceivedEmail:
    def test_returns_tuple_of_strings(self) -> None:
        subject, html = payment_received_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject_contains_pagamento(self) -> None:
        subject, _ = payment_received_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "Pagamento" in subject or "pagamento" in subject

    def test_subject_contains_premium(self) -> None:
        subject, _ = payment_received_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "Premium" in subject

    def test_html_contains_dashboard_url(self) -> None:
        _, html = payment_received_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "dashboard" in html

    def test_html_contains_investiq(self) -> None:
        _, html = payment_received_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "InvestIQ" in html

    def test_html_contains_formatted_period_end(self) -> None:
        _, html = payment_received_email(SAMPLE_EMAIL, SAMPLE_DATE)
        assert "15/06/2026" in html

    def test_works_with_period_end_none(self) -> None:
        subject, html = payment_received_email(SAMPLE_EMAIL, None)
        assert isinstance(subject, str)
        assert isinstance(html, str)
        assert "em breve" in html

    def test_html_is_valid_html_shell(self) -> None:
        _, html = payment_received_email(SAMPLE_EMAIL, None)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html


# ---------------------------------------------------------------------------
# payment_failed_email
# ---------------------------------------------------------------------------


class TestPaymentFailedEmail:
    def test_returns_tuple_of_strings(self) -> None:
        subject, html = payment_failed_email(SAMPLE_EMAIL)
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject_contains_problema(self) -> None:
        subject, _ = payment_failed_email(SAMPLE_EMAIL)
        assert "Problema" in subject or "problema" in subject

    def test_subject_contains_investiq(self) -> None:
        subject, _ = payment_failed_email(SAMPLE_EMAIL)
        assert "InvestIQ" in subject

    def test_html_contains_planos_url(self) -> None:
        _, html = payment_failed_email(SAMPLE_EMAIL)
        assert "planos" in html

    def test_html_contains_investiq(self) -> None:
        _, html = payment_failed_email(SAMPLE_EMAIL)
        assert "InvestIQ" in html

    def test_html_contains_warning_about_free_plan(self) -> None:
        _, html = payment_failed_email(SAMPLE_EMAIL)
        # Should warn about downgrade to free plan
        assert "Gratuito" in html or "gratuito" in html

    def test_html_is_valid_html_shell(self) -> None:
        _, html = payment_failed_email(SAMPLE_EMAIL)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_does_not_require_date_argument(self) -> None:
        # payment_failed_email takes only user_email
        subject, html = payment_failed_email("other@test.com")
        assert isinstance(subject, str)
        assert isinstance(html, str)


# ---------------------------------------------------------------------------
# subscription_canceled_email
# ---------------------------------------------------------------------------


class TestSubscriptionCanceledEmail:
    def test_returns_tuple_of_strings(self) -> None:
        subject, html = subscription_canceled_email(SAMPLE_EMAIL)
        assert isinstance(subject, str)
        assert isinstance(html, str)

    def test_subject_contains_cancelada(self) -> None:
        subject, _ = subscription_canceled_email(SAMPLE_EMAIL)
        assert "cancelada" in subject.lower()

    def test_subject_contains_investiq(self) -> None:
        subject, _ = subscription_canceled_email(SAMPLE_EMAIL)
        assert "InvestIQ" in subject

    def test_html_contains_planos_url(self) -> None:
        _, html = subscription_canceled_email(SAMPLE_EMAIL)
        assert "planos" in html

    def test_html_contains_reativar(self) -> None:
        _, html = subscription_canceled_email(SAMPLE_EMAIL)
        # CTA to reactivate
        assert "Reativar" in html or "reativar" in html

    def test_html_contains_free_plan_limits(self) -> None:
        _, html = subscription_canceled_email(SAMPLE_EMAIL)
        # Mentions free plan quota
        assert "50" in html

    def test_html_contains_investiq(self) -> None:
        _, html = subscription_canceled_email(SAMPLE_EMAIL)
        assert "InvestIQ" in html

    def test_html_is_valid_html_shell(self) -> None:
        _, html = subscription_canceled_email(SAMPLE_EMAIL)
        assert "<!DOCTYPE html>" in html
        assert "</html>" in html

    def test_does_not_require_date_argument(self) -> None:
        subject, html = subscription_canceled_email("another@test.com")
        assert isinstance(subject, str)
        assert isinstance(html, str)


# ---------------------------------------------------------------------------
# Cross-template structural checks
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fn,args",
    [
        (welcome_premium_email, (SAMPLE_EMAIL, SAMPLE_DATE)),
        (welcome_premium_email, (SAMPLE_EMAIL, None)),
        (payment_received_email, (SAMPLE_EMAIL, SAMPLE_DATE)),
        (payment_received_email, (SAMPLE_EMAIL, None)),
        (payment_failed_email, (SAMPLE_EMAIL,)),
        (subscription_canceled_email, (SAMPLE_EMAIL,)),
    ],
)
def test_all_templates_have_footer(fn, args) -> None:
    _, html = fn(*args)
    assert "2026 InvestIQ" in html


@pytest.mark.parametrize(
    "fn,args",
    [
        (welcome_premium_email, (SAMPLE_EMAIL, None)),
        (payment_received_email, (SAMPLE_EMAIL, None)),
        (payment_failed_email, (SAMPLE_EMAIL,)),
        (subscription_canceled_email, (SAMPLE_EMAIL,)),
    ],
)
def test_all_templates_have_header_logo(fn, args) -> None:
    _, html = fn(*args)
    # Header should include the "IQ" logo box
    assert ">IQ<" in html


@pytest.mark.parametrize(
    "fn,args",
    [
        (welcome_premium_email, (SAMPLE_EMAIL, None)),
        (payment_received_email, (SAMPLE_EMAIL, None)),
        (payment_failed_email, (SAMPLE_EMAIL,)),
        (subscription_canceled_email, (SAMPLE_EMAIL,)),
    ],
)
def test_all_templates_are_non_empty_html(fn, args) -> None:
    subject, html = fn(*args)
    assert len(html) > 500  # Sanity: not accidentally returning a stub
    assert len(subject) > 5
