"""alternative.me Fear & Greed Index adapter.

Fetches the Crypto Fear & Greed Index from alternative.me API.
No API key required. Free and publicly available.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

logger = logging.getLogger(__name__)

_URL = "https://api.alternative.me/fng/?limit=1"
_TIMEOUT = 8


def get_fear_greed() -> dict[str, Any] | None:
    """Fetch current Fear & Greed index.

    Returns:
        dict with keys: value (0-100), classification (str), timestamp
        e.g. {"value": 72, "classification": "Greed", "timestamp": "..."}
    """
    try:
        resp = requests.get(_URL, timeout=_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        item = data["data"][0]
        return {
            "value": int(item["value"]),
            "classification": item["value_classification"],
            "timestamp": item["timestamp"],
        }
    except Exception as exc:
        logger.warning("alternativeme: Fear&Greed fetch failed: %s", exc)
        return None
