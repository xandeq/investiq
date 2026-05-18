"""Shared Telegram sender used by Celery tasks.

Single-message send to a specific chat_id. Never raises — Celery fan-out
tasks must continue for other users even if one chat fails. All errors
are logged at WARNING level and the function returns False.
"""
from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)


def send_telegram_notification(chat_id: str, text: str) -> bool:
    """Send a Telegram message to a specific chat_id.

    Returns True on HTTP 200, False on any failure (missing token,
    network error, non-2xx response). Never raises.
    """
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("send_telegram_notification: TELEGRAM_BOT_TOKEN not set")
        return False
    if not chat_id:
        logger.warning("send_telegram_notification: empty chat_id")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as exc:
        logger.warning(
            "send_telegram_notification failed for chat_id=%s: %s", chat_id, exc
        )
        return False
