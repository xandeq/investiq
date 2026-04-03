"""Alert Engine — dispatches opportunity reports via Telegram and Email.

Phase 1: single destination (admin).
Phase 2: per-user destinations from DB (gated by Stripe plan).

Both channels are best-effort — failure in one does NOT block the other.
"""
from __future__ import annotations

import logging

import httpx

from app.core.config import settings
from app.modules.opportunity_detector.config import (
    ALERT_EMAIL,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

logger = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/{method}"


def send_telegram(message: str, chat_id: str | None = None) -> bool:
    """Send message via Telegram Bot API. Returns True on success."""
    target_chat_id = chat_id or TELEGRAM_CHAT_ID
    if not target_chat_id:
        logger.warning(
            "TELEGRAM_CHAT_ID not configured. "
            "Message your bot @alexandrequeiroz_marketing_bot and run "
            "setup_telegram_chat_id() to capture your chat ID."
        )
        return False
    if not TELEGRAM_BOT_TOKEN:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping Telegram alert.")
        return False

    url = _TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(url, json={
                "chat_id": target_chat_id,
                "text": message,
                "parse_mode": "Markdown",
            })
            resp.raise_for_status()
            logger.info("Telegram alert sent to chat_id=%s", target_chat_id)
            return True
    except Exception as exc:
        logger.error("Telegram alert failed: %s", exc)
        return False


def send_email(subject: str, html_body: str, to_email: str | None = None) -> bool:
    """Send email via Brevo (same client as watchlist/tasks.py). Returns True on success."""
    target = to_email or ALERT_EMAIL
    if not settings.BREVO_API_KEY:
        logger.warning("BREVO_API_KEY not set — skipping email alert.")
        return False

    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": settings.BREVO_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {
                        "name": settings.BREVO_FROM_NAME,
                        "email": settings.BREVO_FROM_EMAIL,
                    },
                    "to": [{"email": target}],
                    "subject": subject,
                    "htmlContent": html_body,
                },
            )
            resp.raise_for_status()
            logger.info("Email alert sent to %s: %s", target, subject)
            return True
    except Exception as exc:
        logger.error("Email alert failed: %s", exc)
        return False


def dispatch_opportunity(report) -> dict[str, bool]:
    """Dispatch an OpportunityReport to all configured channels.

    Returns dict of channel → success status.
    """
    from app.modules.opportunity_detector.analyzer import OpportunityReport
    assert isinstance(report, OpportunityReport)

    results = {}

    # Telegram
    telegram_msg = report.alert_message()
    results["telegram"] = send_telegram(telegram_msg)

    # Email
    subject = f"InvestIQ — Oportunidade: {report.ticker} caiu {abs(report.drop_pct):.1f}%"
    html = report.alert_html()
    results["email"] = send_email(subject, html)

    if not any(results.values()):
        logger.error(
            "ALL alert channels failed for opportunity %s — report: %s",
            report.ticker, telegram_msg
        )

    return results


def setup_telegram_chat_id() -> str | None:
    """Utility: fetch chat_id from getUpdates after user messages the bot.

    Instructions:
    1. Open Telegram and search for @alexandrequeiroz_marketing_bot
    2. Send any message (e.g., /start)
    3. Call this function — it returns your chat_id
    4. Set TELEGRAM_CHAT_ID env var or add to ~/.claude/.secrets.env
    """
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not configured.")
        return None

    url = _TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN, method="getUpdates")
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(url, params={"limit": 5, "offset": -5})
            resp.raise_for_status()
            data = resp.json()
            updates = data.get("result", [])
            if not updates:
                logger.warning(
                    "No messages found. Send a message to @alexandrequeiroz_marketing_bot first."
                )
                return None
            chat_id = str(updates[-1]["message"]["chat"]["id"])
            logger.info("Found chat_id: %s", chat_id)
            return chat_id
    except Exception as exc:
        logger.error("setup_telegram_chat_id failed: %s", exc)
        return None
