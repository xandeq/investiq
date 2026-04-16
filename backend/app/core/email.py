"""Transactional email module — provider-agnostic interface.

Uses Resend as primary provider (resend.com — 3k free emails/month, best DX).
Falls back to Brevo if RESEND_API_KEY is not set (legacy support).

Usage (sync — safe inside Celery tasks):
    from app.core.email import send_email

    send_email(
        to="user@example.com",
        subject="Alerta de preco: VALE3",
        html="<p>...</p>",
    )

Provider selection (at call time, not import time):
  1. RESEND_API_KEY set → Resend API
  2. BREVO_API_KEY set  → Brevo API (legacy)
  3. Neither set        → log warning, no-op (dev/test environments)

Both providers: sync httpx call — never use async inside Celery tasks.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Defaults — overridden by env in production
_FROM_EMAIL = "noreply@investiq.com.br"
_FROM_NAME = "InvestIQ"
_APP_URL = "https://investiq.com.br"


def _from_email() -> str:
    try:
        from app.core.config import settings
        return settings.BREVO_FROM_EMAIL or _FROM_EMAIL
    except Exception:
        return _FROM_EMAIL


def _from_name() -> str:
    try:
        from app.core.config import settings
        return settings.BREVO_FROM_NAME or _FROM_NAME
    except Exception:
        return _FROM_NAME


def _send_via_resend(api_key: str, to: str, subject: str, html: str) -> None:
    """Send via Resend API (resend.com). Simple, fast, 3k/mo free tier."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{_from_name()} <{_from_email()}>",
                "to": [to],
                "subject": subject,
                "html": html,
            },
        )
        resp.raise_for_status()
        logger.info("Email sent via Resend to %s: %s", to, subject)


def _send_via_brevo(api_key: str, to: str, subject: str, html: str) -> None:
    """Send via Brevo API (legacy — used when RESEND_API_KEY not configured)."""
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={"api-key": api_key, "Content-Type": "application/json"},
            json={
                "sender": {"name": _from_name(), "email": _from_email()},
                "to": [{"email": to}],
                "subject": subject,
                "htmlContent": html,
            },
        )
        resp.raise_for_status()
        logger.info("Email sent via Brevo to %s: %s", to, subject)


def send_email(to: str, subject: str, html: str) -> None:
    """Send transactional email. Provider selected from environment.

    Non-fatal: logs errors instead of raising, so a broken email provider
    never crashes a Celery task that has other side-effects (DB writes, etc.).
    """
    resend_key = os.environ.get("RESEND_API_KEY", "")
    brevo_key = ""
    try:
        from app.core.config import settings
        brevo_key = settings.BREVO_API_KEY or ""
    except Exception:
        brevo_key = os.environ.get("BREVO_API_KEY", "")

    try:
        if resend_key:
            _send_via_resend(resend_key, to, subject, html)
        elif brevo_key:
            _send_via_brevo(brevo_key, to, subject, html)
        else:
            logger.warning(
                "No email provider configured (set RESEND_API_KEY or BREVO_API_KEY). "
                "Email to %s suppressed: %s",
                to, subject,
            )
    except Exception as exc:
        logger.error("Failed to send email to %s (%s): %s", to, subject, exc)


# ── Pre-built templates ────────────────────────────────────────────────────────

def send_price_alert_email(
    to: str,
    ticker: str,
    target: str,
    current_price: str,
    watchlist_url: str | None = None,
) -> None:
    """Send price alert notification email.

    Args:
        to: recipient email
        ticker: asset ticker (e.g. "VALE3")
        target: configured alert target price as string (e.g. "68.50")
        current_price: current market price as string (e.g. "68.90")
        watchlist_url: deep link to watchlist page (defaults to APP_URL/watchlist)
    """
    try:
        from app.core.config import settings
        app_url = settings.APP_URL
    except Exception:
        app_url = _APP_URL

    url = watchlist_url or f"{app_url}/watchlist"
    target_f = float(target)
    current_f = float(current_price)
    direction = "subiu para" if current_f >= target_f else "caiu para"
    diff_pct = abs(current_f - target_f) / target_f * 100

    subject = f"InvestIQ \u2014 Alerta de preco: {ticker} atingiu R$ {current_f:.2f}"
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f8fafc;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="padding:40px 0;">
    <tr><td align="center">
      <table width="480" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;border:1px solid #e2e8f0;overflow:hidden;">

        <!-- Header -->
        <tr>
          <td style="background:#1a1a2e;padding:24px 32px;">
            <p style="margin:0;color:#fff;font-size:18px;font-weight:700;letter-spacing:-0.5px;">
              InvestIQ
            </p>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 8px;font-size:28px;">&#128276;</p>
            <h1 style="margin:0 0 8px;font-size:22px;font-weight:700;color:#1a1a2e;">
              Alerta de preco atingido
            </h1>
            <p style="margin:0 0 24px;font-size:15px;color:#64748b;">
              O ativo <strong style="color:#1a1a2e;">{ticker}</strong>
              {direction}
              <strong style="color:#1a1a2e;">R$&nbsp;{current_f:.2f}</strong>
              &mdash; a {diff_pct:.1f}% do seu alvo de
              <strong style="color:#1a1a2e;">R$&nbsp;{target_f:.2f}</strong>.
            </p>

            <!-- Price card -->
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="background:#f8fafc;border-radius:8px;border:1px solid #e2e8f0;margin-bottom:24px;">
              <tr>
                <td style="padding:16px 20px;">
                  <table width="100%" cellpadding="0" cellspacing="0">
                    <tr>
                      <td>
                        <p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#94a3b8;">
                          Preco atual
                        </p>
                        <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:#6366f1;font-variant-numeric:tabular-nums;">
                          R$&nbsp;{current_f:.2f}
                        </p>
                      </td>
                      <td align="right">
                        <p style="margin:0;font-size:11px;text-transform:uppercase;letter-spacing:0.5px;color:#94a3b8;">
                          Seu alvo
                        </p>
                        <p style="margin:4px 0 0;font-size:24px;font-weight:700;color:#1a1a2e;font-variant-numeric:tabular-nums;">
                          R$&nbsp;{target_f:.2f}
                        </p>
                      </td>
                    </tr>
                  </table>
                </td>
              </tr>
            </table>

            <a href="{url}"
               style="display:inline-block;padding:14px 28px;background:#6366f1;color:#fff;
                      border-radius:8px;text-decoration:none;font-weight:600;font-size:15px;">
              Ver Watchlist
            </a>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:20px 32px;border-top:1px solid #e2e8f0;background:#f8fafc;">
            <p style="margin:0;font-size:12px;color:#94a3b8;line-height:1.5;">
              Voce recebeu este email porque configurou um alerta de preco para
              <strong>{ticker}</strong> na sua Watchlist InvestIQ.
              Para remover o alerta, acesse a Watchlist e limpe o campo &ldquo;Alerta&rdquo; do ativo.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""
    send_email(to=to, subject=subject, html=html)
