"""Celery tasks for auto-closing signal outcomes after market close.

Runs at 18h30 BRT Mon-Fri (30min after B3 closes at 17h30).
For each open signal_outcome, checks current price against stop and target.
Closes automatically if stop or target_1 was hit during the day.
Sends Telegram notification per auto-closed outcome.
"""

import logging
import os
from decimal import Decimal
from datetime import date

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_last_price_sync(ticker: str) -> Decimal | None:
    """Fetch last known close price from Redis market data cache."""
    import json
    import redis as sync_redis

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    try:
        r = sync_redis.from_url(redis_url, decode_responses=True)
        # market:data:{ticker} is populated by refresh_quotes task
        raw = r.get(f"market:data:{ticker}")
        r.close()
        if raw:
            data = json.loads(raw)
            price = data.get("regularMarketPrice") or data.get("price") or data.get("last")
            return Decimal(str(price)) if price else None
    except Exception as exc:
        logger.debug("auto_close: price lookup failed for %s: %s", ticker, exc)
    return None


def _send_telegram_notification(message: str) -> None:
    """Send auto-close notification via Telegram."""
    import requests as req

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        return
    try:
        req.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            json={"chat_id": chat_id, "text": message, "parse_mode": "HTML"},
            timeout=8,
        )
    except Exception as exc:
        logger.debug("auto_close: telegram notify failed: %s", exc)


@celery_app.task(name="outcome_tracker.auto_close_outcomes")
def auto_close_outcomes() -> dict:
    """Auto-close open signal outcomes at market close based on last price.

    Checks stop_price and target_1 against last known Redis price.
    Closes as 'stopped' or 'closed' accordingly. Notifies via Telegram.
    """
    import asyncio
    import psycopg2

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("auto_close_outcomes: DATABASE_URL not set")
        return {"status": "error", "error": "no DATABASE_URL"}

    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("asyncpg://", "postgresql://")

    closed_count = 0
    stopped_count = 0

    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                # Fetch all open outcomes
                cur.execute(
                    """
                    SELECT id, tenant_id, ticker, direction, entry_price, stop_price,
                           target_1, signal_grade
                    FROM signal_outcomes
                    WHERE status = 'open'
                    ORDER BY created_at ASC
                    """
                )
                open_outcomes = cur.fetchall()

                logger.info("auto_close_outcomes: checking %d open positions", len(open_outcomes))

                today = date.today()
                notifications: list[str] = []

                for row in open_outcomes:
                    oid, tenant_id, ticker, direction, entry_price, stop_price, target_1, signal_grade = row
                    entry_price = Decimal(str(entry_price))
                    stop_price = Decimal(str(stop_price))
                    target_1 = Decimal(str(target_1)) if target_1 else None

                    current_price = _get_last_price_sync(ticker)
                    if current_price is None:
                        logger.debug("auto_close: no price for %s — skipping", ticker)
                        continue

                    risk = abs(entry_price - stop_price)
                    if risk == 0:
                        continue

                    new_status: str | None = None
                    exit_price = current_price

                    if direction == "long":
                        if current_price <= stop_price:
                            new_status = "stopped"
                        elif target_1 and current_price >= target_1:
                            new_status = "closed"
                    else:  # short
                        if current_price >= stop_price:
                            new_status = "stopped"
                        elif target_1 and current_price <= target_1:
                            new_status = "closed"

                    if new_status is None:
                        continue  # still open, no trigger

                    # Calculate R-multiple
                    if direction == "long":
                        r_multiple = (exit_price - entry_price) / risk
                    else:
                        r_multiple = (entry_price - exit_price) / risk
                    r_multiple = r_multiple.quantize(Decimal("0.0001"))

                    cur.execute(
                        """
                        UPDATE signal_outcomes
                        SET status = %s,
                            exit_price = %s,
                            exit_date = %s,
                            r_multiple = %s,
                            updated_at = NOW()
                        WHERE id = %s AND status = 'open'
                        """,
                        (new_status, float(exit_price), today, float(r_multiple), oid),
                    )

                    if new_status == "stopped":
                        stopped_count += 1
                        emoji = "🛑"
                        result_txt = f"stop atingido — R={r_multiple:+.2f}"
                    else:
                        closed_count += 1
                        emoji = "✅"
                        result_txt = f"target atingido — R={r_multiple:+.2f}"

                    notifications.append(
                        f"{emoji} <b>Auto-fechamento</b> {ticker} [{signal_grade or '?'}]\n"
                        f"Entrada: {entry_price} → Saída: {exit_price:.2f}\n"
                        f"{result_txt}"
                    )

        conn.close()

        for msg in notifications:
            _send_telegram_notification(msg)

        logger.info(
            "auto_close_outcomes: closed=%d stopped=%d",
            closed_count,
            stopped_count,
        )
        return {"status": "ok", "closed": closed_count, "stopped": stopped_count}

    except Exception as exc:
        logger.error("auto_close_outcomes failed: %s", exc)
        return {"status": "error", "error": str(exc)}
