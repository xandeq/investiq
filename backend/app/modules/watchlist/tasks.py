"""Price alert checks — runs every 15 min during market hours.

Logic:
  - Query all watchlist_items with price_alert_target IS NOT NULL
  - Read current price from Redis (market:quote:{TICKER})
  - Alert when |current_price - target| / target <= 2% (price "reached" target)
  - Dedup via Redis key price_alert:sent:{tenant_id}:{ticker} (TTL 24h)
  - On alert: send email via Brevo (sync) + save UserInsight record

Redis key schema:
  market:quote:{TICKER}              — live price cache (written by refresh_quotes)
  price_alert:sent:{tenant_id}:{ticker} — dedup flag, TTL 23h

Notes:
  - Uses psycopg2 (sync) — never asyncpg inside Celery tasks
  - Email is sync httpx call (not the async brevo_email_sender from auth)
  - target comparison: ±2% tolerance so a target of 30.00 triggers at 29.40–30.60
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import httpx
import redis as sync_redis
from celery import shared_task
from sqlalchemy import text

from app.core.config import settings

logger = logging.getLogger(__name__)

# Price reaches target when within this % band (e.g., 0.02 = 2%)
_ALERT_TOLERANCE = Decimal("0.02")
# Dedup TTL: 23h — prevents re-alerting until next day even if task runs at midnight
_DEDUP_TTL_SECONDS = 23 * 3600


def _get_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _get_current_price(r: sync_redis.Redis, ticker: str) -> Decimal | None:
    """Read latest price from Redis cache. Returns None if quote not cached."""
    raw = r.get(f"market:quote:{ticker.upper()}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
        price = data.get("regularMarketPrice") or data.get("price")
        return Decimal(str(price)) if price is not None else None
    except Exception:
        return None


def _get_watchlist_items_with_alerts() -> list[dict]:
    """Return all watchlist items that have price_alert_target set."""
    try:
        from app.core.db_sync import get_sync_db_session
        with get_sync_db_session() as session:
            rows = session.execute(text(
                "SELECT tenant_id, ticker, price_alert_target "
                "FROM watchlist_items "
                "WHERE price_alert_target IS NOT NULL"
            )).fetchall()
            return [{"tenant_id": r[0], "ticker": r[1], "target": Decimal(str(r[2]))} for r in rows]
    except Exception as exc:
        logger.error("check_price_alerts: failed to query watchlist: %s", exc)
        return []


def _get_user_email(tenant_id: str) -> str | None:
    """Fetch user email from users table by tenant_id (tenant_id == user.id)."""
    try:
        from app.core.db_sync import get_sync_db_session
        with get_sync_db_session() as session:
            row = session.execute(
                text("SELECT email FROM users WHERE id = :uid LIMIT 1"),
                {"uid": tenant_id},
            ).fetchone()
            return row[0] if row else None
    except Exception as exc:
        logger.error("check_price_alerts: failed to get user email for %s: %s", tenant_id, exc)
        return None


def _send_alert_email(to_email: str, ticker: str, target: Decimal, current_price: Decimal) -> None:
    """Send price alert email via Brevo (sync HTTP call)."""
    try:
        direction = "subiu para" if current_price >= target else "caiu para"
        html = f"""
        <div style="font-family:sans-serif;max-width:480px;margin:auto;padding:24px;">
          <h2 style="color:#1a1a2e;margin-bottom:8px;">🎯 Alerta de Preço — {ticker}</h2>
          <p style="color:#555;font-size:15px;line-height:1.6;">
            O ativo <strong>{ticker}</strong> {direction}
            <strong>R$ {current_price:.2f}</strong>,
            próximo do seu alvo de <strong>R$ {target:.2f}</strong>.
          </p>
          <a href="https://investiq.com.br/watchlist"
             style="display:inline-block;margin-top:16px;padding:12px 24px;
                    background:#6c63ff;color:#fff;border-radius:8px;
                    text-decoration:none;font-weight:600;">
            Ver Watchlist
          </a>
          <p style="margin-top:24px;color:#999;font-size:12px;">
            Para remover este alerta, acesse a Watchlist e limpe o preço-alvo do ativo.
          </p>
        </div>
        """
        with httpx.Client(timeout=10.0) as client:
            resp = client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={"api-key": settings.BREVO_API_KEY, "Content-Type": "application/json"},
                json={
                    "sender": {"name": settings.BREVO_FROM_NAME, "email": settings.BREVO_FROM_EMAIL},
                    "to": [{"email": to_email}],
                    "subject": f"InvestIQ — Alerta de preço: {ticker} atingiu R$ {current_price:.2f}",
                    "htmlContent": html,
                },
            )
            resp.raise_for_status()
            logger.info("Price alert email sent: %s → %s (R$ %.2f)", ticker, to_email, current_price)
    except Exception as exc:
        logger.error("Failed to send price alert email for %s: %s", ticker, exc)


def _save_alert_insight(tenant_id: str, ticker: str, target: Decimal, current_price: Decimal) -> None:
    """Persist price alert as a UserInsight so it appears in /insights."""
    try:
        from app.core.db_sync import get_sync_db_session
        direction = "subiu para" if current_price >= target else "caiu para"
        with get_sync_db_session(tenant_id) as session:
            session.execute(text(
                "INSERT INTO user_insights "
                "(id, tenant_id, type, title, body, severity, ticker, seen, created_at) "
                "VALUES (:id, :tid, :type, :title, :body, :sev, :ticker, false, :now)"
            ), {
                "id": str(uuid.uuid4()),
                "tid": tenant_id,
                "type": "price_alert",
                "title": f"Alerta de preço atingido: {ticker}",
                "body": (
                    f"{ticker} {direction} R$ {current_price:.2f}, "
                    f"próximo do seu alvo de R$ {target:.2f}."
                ),
                "sev": "info",
                "ticker": ticker,
                "now": datetime.now(tz=timezone.utc),
            })
    except Exception as exc:
        logger.error("Failed to save price alert insight for %s/%s: %s", tenant_id, ticker, exc)


@shared_task(name="app.modules.watchlist.tasks.check_price_alerts")
def check_price_alerts() -> None:
    """Check all watchlist price targets and fire alerts when price is within tolerance."""
    items = _get_watchlist_items_with_alerts()
    if not items:
        logger.debug("check_price_alerts: no items with price_alert_target")
        return

    r = _get_redis()
    alerted = 0

    for item in items:
        tenant_id = item["tenant_id"]
        ticker = item["ticker"]
        target = item["target"]

        current_price = _get_current_price(r, ticker)
        if current_price is None:
            logger.debug("check_price_alerts: no cached quote for %s, skipping", ticker)
            continue

        # Check if price is within ±2% of target
        if target <= 0:
            continue
        diff_pct = abs(current_price - target) / target
        if diff_pct > _ALERT_TOLERANCE:
            continue

        # Dedup: skip if already alerted today for this tenant+ticker
        dedup_key = f"price_alert:sent:{tenant_id}:{ticker}"
        if r.exists(dedup_key):
            logger.debug("check_price_alerts: dedup hit for %s/%s", tenant_id, ticker)
            continue

        # Set dedup flag BEFORE sending to avoid duplicate sends on retry
        r.set(dedup_key, "1", ex=_DEDUP_TTL_SECONDS)

        email = _get_user_email(tenant_id)
        if email:
            _send_alert_email(email, ticker, target, current_price)

        _save_alert_insight(tenant_id, ticker, target, current_price)
        alerted += 1
        logger.info(
            "Price alert fired: tenant=%s ticker=%s target=%.2f current=%.2f",
            tenant_id, ticker, target, current_price,
        )

    logger.info("check_price_alerts complete: %d alert(s) fired out of %d items", alerted, len(items))
