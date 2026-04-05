"""Alert Engine — dispatches opportunity reports via Telegram, Email, and in-app.

Phase 1: single destination (admin xandeq@gmail.com).
Phase 2: per-user destinations from DB (gated by Stripe plan).

All channels are best-effort — failure in one does NOT block the others.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

import httpx
from sqlalchemy import text

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


def save_opportunity_to_db(report) -> bool:
    """Persist detected opportunity to detected_opportunities table.

    Uses get_superuser_sync_db_session (sync) because this runs inside a
    Celery task — async sessions are NOT allowed in synchronous Celery workers.
    """
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.opportunity_detector.models import DetectedOpportunity
        from datetime import datetime, timezone

        with get_superuser_sync_db_session() as session:
            opp = DetectedOpportunity(
                ticker=report.ticker,
                asset_type=report.asset_type,
                drop_pct=report.drop_pct,
                period=report.period,
                current_price=report.current_price,
                currency=report.currency,
                risk_level=report.risk.level if report.risk else None,
                is_opportunity=report.risk.is_opportunity if report.risk else False,
                cause_category=report.cause.category if report.cause else None,
                cause_explanation=report.cause.explanation if report.cause else None,
                risk_rationale=report.risk.rationale if report.risk else None,
                recommended_amount_brl=(
                    report.recommendation.suggested_amount_brl
                    if report.recommendation
                    else None
                ),
                target_upside_pct=(
                    report.recommendation.target_upside_pct
                    if report.recommendation
                    else None
                ),
                telegram_message=report.alert_message(),
                followed=False,
                detected_at=datetime.now(timezone.utc),
            )
            session.add(opp)
            session.commit()
        logger.info("save_opportunity_to_db: persisted %s to detected_opportunities", report.ticker)
        return True
    except Exception as exc:
        logger.error("save_opportunity_to_db failed for %s: %s", report.ticker, exc)
        return False


def _get_admin_tenant_id() -> str | None:
    """Look up tenant_id for the admin email from the DB (superuser session)."""
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        admin_email = settings.ADMIN_EMAILS[0] if settings.ADMIN_EMAILS else "xandeq@gmail.com"
        with get_superuser_sync_db_session() as session:
            row = session.execute(
                text("SELECT id FROM users WHERE email = :email LIMIT 1"),
                {"email": admin_email},
            ).fetchone()
            return str(row[0]) if row else None
    except Exception as exc:
        logger.error("_get_admin_tenant_id failed: %s", exc)
        return None


def save_in_app_insight(report) -> bool:
    """Save opportunity as a UserInsight for the admin user (in-app dashboard alert)."""
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        tenant_id = _get_admin_tenant_id()
        if not tenant_id:
            logger.warning("save_in_app_insight: admin tenant_id not found — skipping in-app alert")
            return False

        risk_level = report.risk.level if report.risk else "medio"
        severity = {"baixo": "info", "medio": "warning", "alto": "critical", "evitar": "critical"}.get(risk_level, "warning")
        drop_str = f"{abs(report.drop_pct):.1f}%" if report.drop_pct else ""
        title = f"Oportunidade detectada: {report.ticker}" + (f" -{drop_str}" if drop_str else "")

        body_parts = []
        if report.cause:
            body_parts.append(f"Causa: {report.cause.explanation}")
        if report.risk:
            body_parts.append(f"Risco: {report.risk.level} — {report.risk.rationale}")
        if report.recommendation and report.risk and report.risk.is_opportunity:
            rec = report.recommendation
            body_parts.append(
                f"Sugestão: aportar R$ {rec.suggested_amount_brl:,.0f}, "
                f"target +{rec.target_upside_pct:.0f}% em {rec.timeframe_days}d."
            )

        with get_superuser_sync_db_session() as session:
            session.execute(
                text(
                    "INSERT INTO user_insights "
                    "(id, tenant_id, type, title, body, severity, ticker, seen, created_at) "
                    "VALUES (:id, :tid, :type, :title, :body, :sev, :ticker, false, :now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "tid": tenant_id,
                    "type": "opportunity_alert",
                    "title": title,
                    "body": " | ".join(body_parts) or "Oportunidade detectada pelo scanner.",
                    "sev": severity,
                    "ticker": report.ticker,
                    "now": datetime.now(timezone.utc),
                },
            )
            session.commit()
        logger.info("In-app insight saved for %s (tenant=%s)", report.ticker, tenant_id)
        return True
    except Exception as exc:
        logger.error("save_in_app_insight failed for %s: %s", report.ticker, exc)
        return False


def dispatch_opportunity(report) -> dict[str, bool]:
    """Dispatch an OpportunityReport to all configured channels.

    Returns dict of channel → success status.
    """
    from app.modules.opportunity_detector.analyzer import OpportunityReport
    assert isinstance(report, OpportunityReport)

    results = {}

    # Persist to DB first (before any channel dispatch)
    results["db"] = save_opportunity_to_db(report)

    # Telegram
    telegram_msg = report.alert_message()
    results["telegram"] = send_telegram(telegram_msg)

    # Email
    subject = f"InvestIQ — Oportunidade: {report.ticker} caiu {abs(report.drop_pct):.1f}%"
    html = report.alert_html()
    results["email"] = send_email(subject, html)

    # In-app dashboard insight
    results["in_app"] = save_in_app_insight(report)

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
