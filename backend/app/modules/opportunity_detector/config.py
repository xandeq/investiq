"""Opportunity Detector configuration — thresholds, asset lists, destinations.

All values are overridable via environment variables for production tuning.
Phase 1: single alert destination (admin). Phase 2 will add per-user config.
"""
from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# Asset lists — Phase 1 (curated, not user-configurable)
# ---------------------------------------------------------------------------

TOP_30_IBOV: list[str] = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3",
    "B3SA3", "WEGE3", "RENT3", "LREN3", "JBSS3",
    "SUZB3", "BBAS3", "RADL3", "EGIE3", "TOTS3",
    "HAPV3", "BBSE3", "BEEF3", "CSAN3", "PRIO3",
    "RDOR3", "SBSP3", "VBBR3", "BPAC11", "ELET3",
    "ENEV3", "UGPA3", "EMBR3", "CMIN3", "COGN3",
]

# Binance symbol pairs (USDT-quoted)
CRYPTO_PAIRS: list[str] = ["BTCUSDT", "ETHUSDT"]

# Human-friendly ticker → name mapping for alerts
CRYPTO_NAMES: dict[str, str] = {
    "BTCUSDT": "Bitcoin (BTC)",
    "ETHUSDT": "Ethereum (ETH)",
}

# ---------------------------------------------------------------------------
# Drop / opportunity thresholds (overridable via env)
# ---------------------------------------------------------------------------

def _float_env(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except (ValueError, TypeError):
        return default


ACOES_DAILY_DROP_PCT: float = _float_env("OD_ACOES_DAILY_DROP", -15.0)
ACOES_WEEKLY_DROP_PCT: float = _float_env("OD_ACOES_WEEKLY_DROP", -25.0)

CRYPTO_DAILY_DROP_PCT: float = _float_env("OD_CRYPTO_DAILY_DROP", -20.0)
CRYPTO_WEEKLY_DROP_PCT: float = _float_env("OD_CRYPTO_WEEKLY_DROP", -35.0)

# Tesouro Direto: alert when IPCA+ real rate exceeds this threshold
TESOURO_IPCA_REAL_RATE_MIN: float = _float_env("OD_TESOURO_IPCA_MIN", 7.0)
# Alert when Prefixado annual rate exceeds CDI by this spread (pp)
TESOURO_PREFIXADO_CDI_SPREAD_MIN: float = _float_env("OD_TESOURO_PREFIXADO_SPREAD", 2.0)

# ---------------------------------------------------------------------------
# Deduplication TTL
# ---------------------------------------------------------------------------

# How long to suppress repeat alerts for the same ticker (seconds)
DEDUP_TTL_SECONDS: int = int(os.environ.get("OD_DEDUP_TTL_HOURS", "4")) * 3600

# Redis key prefix for dedup flags
REDIS_DEDUP_PREFIX = "opportunity_detector:sent"

# ---------------------------------------------------------------------------
# Alert destinations — Phase 1 hardcoded
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN: str = os.environ.get("TELEGRAM_BOT_TOKEN", "")
# Set after first /start message to the bot — see setup instructions in README
TELEGRAM_CHAT_ID: str = os.environ.get("TELEGRAM_CHAT_ID", "")

ALERT_EMAIL: str = os.environ.get("OPPORTUNITY_ALERT_EMAIL", "xandeq@gmail.com")

# ---------------------------------------------------------------------------
# External API endpoints
# ---------------------------------------------------------------------------

BRAPI_BASE_URL = "https://brapi.dev/api"
BINANCE_TICKER_URL = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BCB_CDI_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.12/dados/ultimos/1?formato=json"
