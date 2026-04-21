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
    """Send morning briefing at 08h30 BRT (Mon-Fri)."""
    import redis.asyncio as aioredis

    async def _run() -> str:
        from app.modules.telegram_bot.briefings import build_morning_briefing

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            return await build_morning_briefing(redis_client)
        finally:
            try:
                await redis_client.aclose()
            except Exception:
                pass

    try:
        message = asyncio.run(_run())
        _send_message(message)
        logger.info("telegram_bot.send_morning_briefing: sent")
        return {"status": "ok"}
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
