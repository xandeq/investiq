"""Signal Engine — Celery tasks.

Tasks:
- scan_and_store_signals: scans universe for A+ setups, stores in Redis,
  sends Telegram alert for new signals.
- check_stop_loss: monitors open swing_trade_operations for stop-loss hits.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import date

import redis as sync_redis
from celery import shared_task

logger = logging.getLogger(__name__)

_STOP_DEDUP_PREFIX = "signal_engine:stop_hit"
_STOP_DEDUP_TTL = 86400  # 24h — one alert per ticker per day


def _get_sync_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _get_async_redis():
    import redis.asyncio as aioredis
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return aioredis.from_url(url, decode_responses=True)


async def _run_scan_and_store() -> list[dict]:
    """Async implementation of scan_and_store_signals."""
    from app.modules.signal_engine.scanner import (
        get_active_signals,
        scan_universe,
        store_signals,
    )

    brapi_token = os.environ.get("BRAPI_TOKEN", "")
    redis_client = _get_async_redis()

    try:
        # Get previously cached signals for deduplication (don't re-alert same signals)
        previous = await get_active_signals(redis_client)
        previous_tickers = {s["ticker"] for s in previous}

        new_signals = await scan_universe(brapi_token=brapi_token, redis_client=redis_client)
        await store_signals(redis_client, new_signals)

        # Return only genuinely new tickers for Telegram alert
        truly_new = [s for s in new_signals if s["ticker"] not in previous_tickers]
        return truly_new
    finally:
        try:
            await redis_client.aclose()
        except Exception:
            pass


def _send_telegram_signals(signals: list[dict]) -> None:
    """Send Telegram alert for new A+ signals."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        logger.warning("check_stop_loss: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return

    import requests

    lines = ["<b>InvestIQ — Novos Setups A+</b>", ""]
    for s in signals:
        setup = s.get("setup") or {}
        lines.append(
            f"<b>{s['ticker']}</b> — {setup.get('pattern', 'N/D')} ({setup.get('direction', 'N/D')})\n"
            f"  Entrada: R${setup.get('entry', '?')} | Stop: R${setup.get('stop', '?')} | "
            f"Alvo1: R${setup.get('target_1', '?')} | R/R: {setup.get('rr', '?')}"
        )

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to send Telegram signal alert: %s", exc)


@shared_task(name="signal_engine.scan_signals")
def scan_and_store_signals() -> dict:
    """Scan universe for A+ setups, store in Redis, alert Telegram for new signals."""
    try:
        new_signals = asyncio.run(_run_scan_and_store())
        if new_signals:
            _send_telegram_signals(new_signals)
            logger.info("signal_engine: %d new A+ signal(s) found and alerted", len(new_signals))
        else:
            logger.info("signal_engine: no new A+ signals in this scan")
        return {"status": "ok", "new_signals": len(new_signals)}
    except Exception as exc:
        logger.error("signal_engine.scan_signals failed: %s", exc)
        return {"status": "error", "error": str(exc)}


async def _run_check_stop_loss() -> list[str]:
    """Async implementation of check_stop_loss. Returns list of tickers that hit stop."""
    from sqlalchemy import select, text as sa_text

    # Import the sync session helper for Celery (following project pattern)
    from app.core.db_sync import get_superuser_sync_db_session  # type: ignore[import]

    r_sync = _get_sync_redis()
    today_str = date.today().isoformat()
    triggered: list[str] = []

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    with get_superuser_sync_db_session() as db:
        rows = db.execute(
            sa_text(
                "SELECT id, ticker, entry_price, stop_price "
                "FROM swing_trade_operations "
                "WHERE status = 'open' AND stop_price IS NOT NULL AND deleted_at IS NULL"
            )
        ).fetchall()

    for row in rows:
        op_id, ticker, entry_price, stop_price = (
            row[0], row[1], float(row[2]), float(row[3])
        )

        # Dedup: one stop alert per ticker per day
        dedup_key = f"{_STOP_DEDUP_PREFIX}:{ticker}:{today_str}"
        if r_sync.exists(dedup_key):
            continue

        # Fetch current price from Redis quotes cache
        quote_key = f"quote:{ticker}"
        raw_quote = r_sync.get(quote_key)
        if not raw_quote:
            logger.debug("check_stop_loss: no cached quote for %s, skipping", ticker)
            continue

        try:
            quote_data = json.loads(raw_quote)
            current_price = float(
                quote_data.get("regularMarketPrice")
                or quote_data.get("price")
                or quote_data.get("close")
                or 0
            )
        except Exception as exc:
            logger.warning("check_stop_loss: failed to parse quote for %s: %s", ticker, exc)
            continue

        if current_price <= 0:
            continue

        # Stop hit when current_price <= stop_price
        if current_price <= stop_price:
            triggered.append(ticker)
            # Mark dedup
            r_sync.setex(dedup_key, _STOP_DEDUP_TTL, "1")

            # Send Telegram alert
            if bot_token and chat_id:
                import requests
                msg = (
                    f"STOP HIT: {ticker} — "
                    f"preco {current_price:.2f} atingiu stop {stop_price:.2f}"
                )
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
                try:
                    requests.post(
                        url,
                        json={"chat_id": chat_id, "text": msg},
                        timeout=10,
                    )
                except Exception as exc:
                    logger.warning("check_stop_loss: Telegram send failed for %s: %s", ticker, exc)

    r_sync.close()
    return triggered


@shared_task(name="signal_engine.recalibrate_patterns")
def recalibrate_patterns() -> dict:
    """Recalibrate pattern weights from real outcomes — runs Sunday 20h BRT.

    Fetches expectancy per pattern from signal_outcomes, updates PATTERN_WEIGHTS
    in-memory and in Redis, and sends a Telegram notification if patterns changed.
    """
    import os

    from app.modules.signal_engine.calibration import recalibrate_and_notify

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    r_sync = _get_sync_redis()

    try:
        # Use sync psycopg2 session (Celery cannot use asyncpg)
        from app.core.db_sync import get_superuser_sync_db_session  # type: ignore[import]

        with get_superuser_sync_db_session() as db:
            report = recalibrate_and_notify(
                redis_client=r_sync,
                telegram_token=bot_token,
                chat_id=chat_id,
                db_session=db,
            )
    except Exception as exc:
        logger.warning(
            "recalibrate_patterns: DB session unavailable (%s) — running without DB", exc
        )
        report = recalibrate_and_notify(
            redis_client=r_sync,
            telegram_token=bot_token,
            chat_id=chat_id,
        )
    finally:
        try:
            r_sync.close()
        except Exception:
            pass

    logger.info(
        "recalibrate_patterns: disabled=%s boosted=%s errors=%s",
        report.get("disabled"),
        report.get("boosted"),
        report.get("errors"),
    )
    return {"status": "ok", "report": report}


@shared_task(name="signal_engine.check_stop_loss")
def check_stop_loss() -> dict:
    """Monitor open swing trade operations for stop-loss hits.

    For each open operation with a stop_price:
    - Fetches current price from Redis quotes cache
    - If price <= stop_price: sends Telegram alert (deduplicated per ticker/day)
    """
    try:
        triggered = asyncio.run(_run_check_stop_loss())
        logger.info("check_stop_loss: %d stop(s) triggered", len(triggered))
        return {"status": "ok", "triggered": triggered}
    except Exception as exc:
        logger.error("signal_engine.check_stop_loss failed: %s", exc)
        return {"status": "error", "error": str(exc)}
