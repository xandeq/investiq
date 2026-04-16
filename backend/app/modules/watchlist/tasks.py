"""Price alert checks — runs every 15 min during market hours.

Logic:
  - Query all watchlist_items with price_alert_target IS NOT NULL
  - Batch-read current prices from Redis via MGET pipeline (single round-trip)
  - Alert when |current_price - target| / target <= 2% (price "reached" target)
  - Dedup via Redis key price_alert:sent:{tenant_id}:{ticker} (TTL 23h)
  - On alert: send email via Brevo (sync) + save UserInsight + update alert_triggered_at in DB

Redis key schema:
  market:quote:{TICKER}              — live price cache (written by refresh_quotes)
  price_alert:sent:{tenant_id}:{ticker} — dedup flag, TTL 23h

Notes:
  - Uses psycopg2 (sync) — never asyncpg inside Celery tasks
  - Email is sync httpx call (not the async brevo_email_sender from auth)
  - target comparison: ±2% tolerance so a target of 30.00 triggers at 29.40–30.60
  - MGET batching: all Redis reads happen in a single pipeline call (O(1) round-trips)
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import redis as sync_redis
from celery import shared_task
from sqlalchemy import text

from app.core.email import send_price_alert_email

logger = logging.getLogger(__name__)

# Price reaches target when within this % band (e.g., 0.02 = 2%)
_ALERT_TOLERANCE = Decimal("0.02")
# Dedup TTL: 23h — prevents re-alerting until next day even if task runs at midnight
_DEDUP_TTL_SECONDS = 23 * 3600


def _get_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _parse_price_from_raw(raw: str | None) -> Decimal | None:
    """Parse price from Redis quote JSON. Returns None on cache miss or parse error."""
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
    """Send price alert email via core/email.py (Resend primary, Brevo fallback)."""
    send_price_alert_email(
        to=to_email,
        ticker=ticker,
        target=str(target),
        current_price=str(current_price),
    )


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
                "title": f"Alerta de preco atingido: {ticker}",
                "body": (
                    f"{ticker} {direction} R$ {current_price:.2f}, "
                    f"proximo do seu alvo de R$ {target:.2f}."
                ),
                "sev": "info",
                "ticker": ticker,
                "now": datetime.now(tz=timezone.utc),
            })
    except Exception as exc:
        logger.error("Failed to save price alert insight for %s/%s: %s", tenant_id, ticker, exc)


def _update_alert_triggered_at(tenant_id: str, ticker: str, triggered_at: datetime) -> None:
    """Write alert_triggered_at to watchlist_items for frontend display."""
    try:
        from app.core.db_sync import get_sync_db_session
        with get_sync_db_session() as session:
            session.execute(text(
                "UPDATE watchlist_items "
                "SET alert_triggered_at = :ts "
                "WHERE tenant_id = :tid AND ticker = :ticker"
            ), {"ts": triggered_at, "tid": tenant_id, "ticker": ticker})
    except Exception as exc:
        logger.error("Failed to update alert_triggered_at for %s/%s: %s", tenant_id, ticker, exc)


@shared_task(name="app.modules.watchlist.tasks.check_price_alerts")
def check_price_alerts() -> None:
    """Check all watchlist price targets and fire alerts when price is within tolerance.

    Performance: all Redis reads are batched via MGET pipeline (single round-trip
    regardless of how many watchlist items exist).
    """
    items = _get_watchlist_items_with_alerts()
    if not items:
        logger.debug("check_price_alerts: no items with price_alert_target")
        return

    r = _get_redis()

    # ── Batch-read all quotes in ONE Redis round-trip ─────────────────────────
    unique_tickers = list({item["ticker"] for item in items})
    keys = [f"market:quote:{t.upper()}" for t in unique_tickers]
    raw_values = r.mget(keys)  # single MGET call — O(1) network round-trips
    price_map: dict[str, Decimal | None] = {
        ticker: _parse_price_from_raw(raw)
        for ticker, raw in zip(unique_tickers, raw_values)
    }

    # ── Batch-check dedup flags in ONE pipeline ───────────────────────────────
    dedup_keys = [f"price_alert:sent:{item['tenant_id']}:{item['ticker']}" for item in items]
    dedup_exists = r.mget(dedup_keys)  # 1 = exists (dedup), None = new alert allowed
    dedup_map = {key: val is not None for key, val in zip(dedup_keys, dedup_exists)}

    alerted = 0
    now = datetime.now(tz=timezone.utc)

    for item in items:
        tenant_id = item["tenant_id"]
        ticker = item["ticker"]
        target = item["target"]

        current_price = price_map.get(ticker)
        if current_price is None:
            logger.debug("check_price_alerts: no cached quote for %s, skipping", ticker)
            continue

        if target <= 0:
            continue

        # Check if price is within ±2% of target
        diff_pct = abs(current_price - target) / target
        if diff_pct > _ALERT_TOLERANCE:
            continue

        # Dedup check
        dedup_key = f"price_alert:sent:{tenant_id}:{ticker}"
        if dedup_map.get(dedup_key):
            logger.debug("check_price_alerts: dedup hit for %s/%s", tenant_id, ticker)
            continue

        # Set dedup flag BEFORE sending — prevents duplicate sends on task retry
        r.set(dedup_key, "1", ex=_DEDUP_TTL_SECONDS)

        # Persist triggered_at to DB (non-fatal if it fails)
        _update_alert_triggered_at(tenant_id, ticker, now)

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
