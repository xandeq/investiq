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
            # Phase 39: fan out to per-user Telegram chat_ids (pro + trial users only)
            try:
                from app.modules.telegram_bot.tasks import notify_users_for_signal
                notify_users_for_signal.delay(new_signals)
            except Exception as exc:
                # Never let fan-out failure break the scan itself
                logger.warning("signal_engine: failed to dispatch notify_users_for_signal: %s", exc)
            logger.info("signal_engine: %d new A+ signal(s) found and alerted", len(new_signals))
        else:
            logger.info("signal_engine: no new A+ signals in this scan")
        return {"status": "ok", "new_signals": len(new_signals)}
    except Exception as exc:
        logger.error("signal_engine.scan_signals failed: %s", exc)
        return {"status": "error", "error": str(exc)}


def _get_user_email_sync(tenant_id: str) -> str | None:
    """Fetch user email from users table by tenant_id."""
    from sqlalchemy import text as sa_text
    from app.core.db_sync import get_superuser_sync_db_session
    try:
        with get_superuser_sync_db_session() as db:
            row = db.execute(
                sa_text("SELECT email FROM users WHERE id = :uid LIMIT 1"),
                {"uid": tenant_id},
            ).fetchone()
            return row[0] if row else None
    except Exception as exc:
        logger.error("check_stop_loss: failed to get email for %s: %s", tenant_id, exc)
        return None


def _save_swing_alert_insight(
    tenant_id: str, ticker: str, alert_type: str,
    trigger_price: float, current_price: float,
) -> None:
    """Persist stop/target alert as UserInsight."""
    import uuid as _uuid
    from datetime import datetime, timezone
    from sqlalchemy import text as sa_text
    from app.core.db_sync import get_superuser_sync_db_session
    try:
        if alert_type == "stop":
            title = f"Stop atingido: {ticker}"
            body = (
                f"{ticker} caiu para R$ {current_price:.2f}, "
                f"abaixo do seu stop de R$ {trigger_price:.2f}. Considere encerrar a operacao."
            )
            severity = "alert"
        else:
            title = f"Alvo atingido: {ticker}"
            body = (
                f"{ticker} subiu para R$ {current_price:.2f}, "
                f"atingindo seu alvo de R$ {trigger_price:.2f}. Considere realizar o lucro."
            )
            severity = "info"

        with get_superuser_sync_db_session() as db:
            db.execute(sa_text(
                "INSERT INTO user_insights "
                "(id, tenant_id, type, title, body, severity, ticker, seen, created_at) "
                "VALUES (:id, :tid, :type, :title, :body, :sev, :ticker, false, :now)"
            ), {
                "id": str(_uuid.uuid4()),
                "tid": tenant_id,
                "type": f"swing_{alert_type}_alert",
                "title": title,
                "body": body,
                "sev": severity,
                "ticker": ticker,
                "now": datetime.now(tz=timezone.utc),
            })
    except Exception as exc:
        logger.error("Failed to save swing alert insight for %s/%s: %s", tenant_id, ticker, exc)


def _send_swing_alert_email(
    tenant_id: str, ticker: str, alert_type: str,
    trigger_price: float, current_price: float,
) -> None:
    """Send stop-loss or target-hit email to user."""
    from app.core.email import send_email
    email = _get_user_email_sync(tenant_id)
    if not email:
        return

    if alert_type == "stop":
        subject = f"InvestIQ — Stop atingido: {ticker} a R$ {current_price:.2f}"
        body_pt = (
            f"<p>O preco de <strong>{ticker}</strong> caiu para "
            f"<strong>R$ {current_price:.2f}</strong>, abaixo do seu stop configurado de "
            f"R$ {trigger_price:.2f}.</p>"
            f"<p>Considere encerrar a operacao para proteger seu capital.</p>"
        )
    else:
        subject = f"InvestIQ — Alvo atingido: {ticker} a R$ {current_price:.2f}"
        body_pt = (
            f"<p>O preco de <strong>{ticker}</strong> subiu para "
            f"<strong>R$ {current_price:.2f}</strong>, atingindo seu alvo de "
            f"R$ {trigger_price:.2f}.</p>"
            f"<p>Considere realizar o lucro.</p>"
        )

    html = (
        f"<h2>{subject}</h2>{body_pt}"
        "<p style='color:#888;font-size:12px'>InvestIQ — Copiloto de Investimentos</p>"
    )
    try:
        send_email(to=email, subject=subject, html=html)
    except Exception as exc:
        logger.warning("check_stop_loss: email send failed for %s/%s: %s", tenant_id, ticker, exc)


def _run_check_stop_loss() -> list[str]:
    """Check all open swing trade operations for stop-loss and target-price hits.

    Fixes vs original:
    - Redis key: market:quote:{TICKER} (was: quote:{ticker} — wrong namespace)
    - Also checks target_price (not only stop_price)
    - Sends email to user (not only Telegram)
    - Saves UserInsight for in-app notification
    - Joins tenant_id so per-user emails work
    """
    from sqlalchemy import text as sa_text
    from app.core.db_sync import get_superuser_sync_db_session

    r_sync = _get_sync_redis()
    today_str = date.today().isoformat()
    triggered: list[str] = []

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")

    with get_superuser_sync_db_session() as db:
        rows = db.execute(
            sa_text(
                "SELECT id, tenant_id, ticker, stop_price, target_price "
                "FROM swing_trade_operations "
                "WHERE status = 'open' AND deleted_at IS NULL "
                "  AND (stop_price IS NOT NULL OR target_price IS NOT NULL)"
            )
        ).fetchall()

    if not rows:
        return []

    # Batch-fetch all quotes in one Redis MGET (O(1) round-trips)
    unique_tickers = list({row[2].upper() for row in rows})
    keys = [f"market:quote:{t}" for t in unique_tickers]
    raw_values = r_sync.mget(keys)
    price_map: dict[str, float | None] = {}
    for ticker, raw in zip(unique_tickers, raw_values):
        if not raw:
            price_map[ticker] = None
            continue
        try:
            data = json.loads(raw)
            p = data.get("regularMarketPrice") or data.get("price") or data.get("close")
            price_map[ticker] = float(p) if p else None
        except Exception:
            price_map[ticker] = None

    for row in rows:
        op_id, tenant_id, ticker, stop_price, target_price = (
            row[0], row[1], row[2], row[3], row[4]
        )
        ticker_upper = ticker.upper()
        current_price = price_map.get(ticker_upper)
        if not current_price or current_price <= 0:
            logger.debug("check_stop_loss: no cached quote for %s, skipping", ticker)
            continue

        # Check stop-loss
        if stop_price is not None and current_price <= float(stop_price):
            dedup_key = f"{_STOP_DEDUP_PREFIX}:stop:{tenant_id}:{ticker}:{today_str}"
            if not r_sync.exists(dedup_key):
                r_sync.setex(dedup_key, _STOP_DEDUP_TTL, "1")
                triggered.append(f"STOP:{ticker}")
                _send_swing_alert_email(tenant_id, ticker, "stop", float(stop_price), current_price)
                _save_swing_alert_insight(tenant_id, ticker, "stop", float(stop_price), current_price)
                if bot_token and chat_id:
                    import requests as _req
                    try:
                        _req.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": (
                                    f"🔴 STOP HIT: <b>{ticker}</b> — "
                                    f"R$ {current_price:.2f} ≤ stop R$ {float(stop_price):.2f}"
                                ),
                                "parse_mode": "HTML",
                            },
                            timeout=10,
                        )
                    except Exception as exc:
                        logger.warning("Telegram stop alert failed for %s: %s", ticker, exc)
                logger.info("Stop hit: tenant=%s ticker=%s price=%.2f stop=%.2f",
                            tenant_id, ticker, current_price, float(stop_price))

        # Check target-price
        if target_price is not None and current_price >= float(target_price):
            dedup_key = f"{_STOP_DEDUP_PREFIX}:target:{tenant_id}:{ticker}:{today_str}"
            if not r_sync.exists(dedup_key):
                r_sync.setex(dedup_key, _STOP_DEDUP_TTL, "1")
                triggered.append(f"TARGET:{ticker}")
                _send_swing_alert_email(tenant_id, ticker, "target", float(target_price), current_price)
                _save_swing_alert_insight(tenant_id, ticker, "target", float(target_price), current_price)
                if bot_token and chat_id:
                    import requests as _req
                    try:
                        _req.post(
                            f"https://api.telegram.org/bot{bot_token}/sendMessage",
                            json={
                                "chat_id": chat_id,
                                "text": (
                                    f"🟢 ALVO ATINGIDO: <b>{ticker}</b> — "
                                    f"R$ {current_price:.2f} ≥ alvo R$ {float(target_price):.2f}"
                                ),
                                "parse_mode": "HTML",
                            },
                            timeout=10,
                        )
                    except Exception as exc:
                        logger.warning("Telegram target alert failed for %s: %s", ticker, exc)
                logger.info("Target hit: tenant=%s ticker=%s price=%.2f target=%.2f",
                            tenant_id, ticker, current_price, float(target_price))

    try:
        r_sync.close()
    except Exception:
        pass
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
        triggered = _run_check_stop_loss()
        logger.info("check_stop_loss: %d stop(s) triggered", len(triggered))
        return {"status": "ok", "triggered": triggered}
    except Exception as exc:
        logger.error("signal_engine.check_stop_loss failed: %s", exc)
        return {"status": "error", "error": str(exc)}
