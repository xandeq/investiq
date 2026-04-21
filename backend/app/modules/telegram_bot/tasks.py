"""Celery tasks for the Telegram bot."""
from __future__ import annotations

import logging
import os

from app.celery_app import celery_app

logger = logging.getLogger(__name__)


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
