"""Celery tasks for the Telegram bot."""
from __future__ import annotations

import asyncio
import logging
import os

import requests

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


def _send_message(text: str) -> None:
    """Send a message to the configured Telegram chat."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not bot_token or not chat_id:
        logger.warning("_send_message: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("_send_message failed: %s", exc)


@celery_app.task(name="telegram_bot.send_morning_briefing")
def send_morning_briefing() -> dict:
    """Send full morning briefing (Briefing Engine v2) at 08h30 BRT (Mon-Fri)."""
    import redis.asyncio as aioredis
    import json

    async def _run() -> list[str]:
        """Build full report and return Telegram chunks."""
        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            from app.modules.briefing_engine.report import build_full_report

            report = await build_full_report(redis_client=redis_client)

            # Cache report for /briefing on-demand
            cache_key = "briefing_engine:latest"
            await redis_client.setex(cache_key, 6 * 3600, json.dumps(report, default=str))

            return report.get("telegram_chunks", [report.get("summary", "Briefing indisponível")])
        finally:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    try:
        chunks = asyncio.run(_run())
        for chunk in chunks:
            _send_message(chunk)
        logger.info("telegram_bot.send_morning_briefing: sent %d chunks", len(chunks))
        return {"status": "ok", "chunks_sent": len(chunks)}
    except Exception as exc:
        logger.error("telegram_bot.send_morning_briefing failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@celery_app.task(name="telegram_bot.send_evening_summary")
def send_evening_summary() -> dict:
    """Send evening summary at 18h30 BRT (Mon-Fri)."""
    import redis.asyncio as aioredis

    async def _run() -> str:
        from app.modules.telegram_bot.briefings import build_evening_summary
        from app.core.db import async_session_factory

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            async with async_session_factory() as db:
                return await build_evening_summary(redis_client, db_session=db)
        finally:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    try:
        message = asyncio.run(_run())
        _send_message(message)
        logger.info("telegram_bot.send_evening_summary: sent")
        return {"status": "ok"}
    except Exception as exc:
        logger.error("telegram_bot.send_evening_summary failed: %s", exc)
        return {"status": "error", "error": str(exc)}


@celery_app.task(name="telegram_bot.run_polling")
def run_bot_polling() -> None:
    """Run the Telegram bot in polling mode.

    This task is blocking and should be run in a dedicated Celery worker.
    Call manually or via: celery -A app.celery_app worker -Q telegram --concurrency=1
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set — cannot start bot polling")
        return

    import asyncio

    from app.modules.telegram_bot.bot import create_application

    application = create_application(token)
    logger.info("Starting Telegram bot in polling mode")
    asyncio.run(application.run_polling(drop_pending_updates=True))


# ─────────────────────────────────────────────────────────────────────────────
# Phase 39: Per-user A+ signal fan-out
# ─────────────────────────────────────────────────────────────────────────────

from app.core.telegram import send_telegram_notification


def _build_signal_message(signals: list[dict]) -> str:
    """Render an HTML-formatted Telegram message body for one or more A+ signals.

    Format matches the admin alert pattern from signal_engine._send_telegram_signals
    but adds a per-ticker link to https://investiq.com.br/stock/{ticker}.
    """
    lines = ["<b>InvestIQ — Novos Setups A+</b>", ""]
    for s in signals:
        ticker = s.get("ticker", "?")
        setup = s.get("setup") or {}
        pattern = setup.get("pattern", "N/D")
        direction = setup.get("direction", "N/D")
        entry = setup.get("entry", "?")
        stop = setup.get("stop", "?")
        target_1 = setup.get("target_1", "?")
        rr = setup.get("rr", "?")
        grade = setup.get("grade") or s.get("grade", "A+")
        link = f"https://investiq.com.br/stock/{ticker}"
        lines.append(
            f"<b><a href=\"{link}\">{ticker}</a></b> — {pattern} ({direction}) — Grau {grade}\n"
            f"  Entrada: R${entry} | Stop: R${stop} | Alvo1: R${target_1} | R/R: {rr}"
        )
    return "\n".join(lines)


@celery_app.task(name="telegram_bot.notify_users_for_signal")
def notify_users_for_signal(signals: list[dict]) -> dict:
    """Fan out A+ signal notifications to all pro users with telegram_chat_id set.

    Called by signal_engine.scan_and_store_signals when new signals are detected.
    Reads users via sync DB session (Celery worker context — never use asyncpg here).
    """
    if not signals:
        return {"status": "ok", "notified": 0}

    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("notify_users_for_signal: TELEGRAM_BOT_TOKEN not set")
        return {"status": "skipped", "notified": 0}

    from sqlalchemy import text as sa_text
    from app.core.db_sync import get_superuser_sync_db_session

    # Pro plan OR active trial — matches _is_pro_or_trial in profile/router.py
    query = sa_text(
        "SELECT telegram_chat_id FROM users "
        "WHERE telegram_chat_id IS NOT NULL "
        "  AND telegram_chat_id != '' "
        "  AND (plan = 'pro' OR (plan = 'free' AND trial_ends_at IS NOT NULL AND trial_ends_at > :now))"
    )
    from datetime import datetime, timezone
    now = datetime.now(tz=timezone.utc)

    try:
        with get_superuser_sync_db_session() as db:
            rows = db.execute(query, {"now": now}).fetchall()
    except Exception as exc:
        logger.error("notify_users_for_signal: DB query failed: %s", exc)
        return {"status": "error", "notified": 0, "error": str(exc)}

    chat_ids = [row[0] for row in rows]
    if not chat_ids:
        return {"status": "ok", "notified": 0}

    message = _build_signal_message(signals)
    notified = 0
    for chat_id in chat_ids:
        ok = send_telegram_notification(chat_id, message)
        if ok:
            notified += 1

    logger.info(
        "notify_users_for_signal: %d/%d users notified for %d signal(s)",
        notified, len(chat_ids), len(signals),
    )
    return {"status": "ok", "notified": notified}
