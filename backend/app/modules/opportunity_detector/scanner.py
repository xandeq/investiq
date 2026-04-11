"""Scanner — Celery Beat tasks that monitor assets for opportunities.

Tasks:
- scan_acoes_opportunities: top 30 IBOV via BRAPI, Mon-Fri market hours
- scan_crypto_opportunities: BTC/ETH via Binance API, 24/7
- scan_fixed_income_opportunities: Tesouro Direto rates from Redis, every 6h

Deduplication: Redis key opportunity_detector:sent:{ticker}:{period} TTL=4h
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Optional

import redis as sync_redis
import requests
from celery import shared_task

from app.modules.opportunity_detector.alert_engine import dispatch_opportunity
from app.modules.opportunity_detector.analyzer import run_analysis
from app.modules.opportunity_detector.config import (
    ACOES_DAILY_DROP_PCT,
    ACOES_WEEKLY_DROP_PCT,
    BRAPI_BASE_URL,
    BINANCE_KLINES_URL,
    BINANCE_TICKER_URL,
    BCB_CDI_URL,
    CRYPTO_DAILY_DROP_PCT,
    CRYPTO_NAMES,
    CRYPTO_PAIRS,
    CRYPTO_WEEKLY_DROP_PCT,
    DEDUP_TTL_SECONDS,
    REDIS_DEDUP_PREFIX,
    TESOURO_IPCA_REAL_RATE_MIN,
    TESOURO_PREFIXADO_CDI_SPREAD_MIN,
    TOP_30_IBOV,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Redis helpers
# ---------------------------------------------------------------------------

def _get_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _is_deduped(r: sync_redis.Redis, ticker: str, period: str) -> bool:
    """Return True if an alert was already sent for this ticker+period within TTL."""
    key = f"{REDIS_DEDUP_PREFIX}:{ticker}:{period}"
    return r.exists(key) == 1


def _mark_sent(r: sync_redis.Redis, ticker: str, period: str) -> None:
    key = f"{REDIS_DEDUP_PREFIX}:{ticker}:{period}"
    r.set(key, "1", ex=DEDUP_TTL_SECONDS)


# ---------------------------------------------------------------------------
# BRAPI helpers
# ---------------------------------------------------------------------------

def _get_brapi_token() -> str:
    return os.environ.get("BRAPI_TOKEN", "")


def _fetch_brapi_quote(ticker: str) -> Optional[dict]:
    """Fetch single quote from BRAPI. Returns None on error."""
    token = _get_brapi_token()
    try:
        resp = requests.get(
            f"{BRAPI_BASE_URL}/quote/{ticker}",
            params={"token": token, "range": "5d", "interval": "1d"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", [])
        return results[0] if results else None
    except Exception as exc:
        logger.warning("BRAPI quote error for %s: %s", ticker, exc)
        return None


def _calc_weekly_change(quote: dict) -> Optional[float]:
    """Calculate % change over last 5 trading days from historical data."""
    history = quote.get("historicalDataPrice", [])
    if len(history) < 2:
        return None
    # history is oldest→newest; compare first close to current price
    oldest_close = history[0].get("close")
    current_price = quote.get("regularMarketPrice")
    if not oldest_close or not current_price or oldest_close == 0:
        return None
    return ((current_price - oldest_close) / oldest_close) * 100


# ---------------------------------------------------------------------------
# Binance helpers
# ---------------------------------------------------------------------------

def _fetch_binance_ticker(symbol: str) -> Optional[dict]:
    """Fetch 24h ticker from Binance public API (no auth required)."""
    try:
        resp = requests.get(BINANCE_TICKER_URL, params={"symbol": symbol}, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("Binance ticker error for %s: %s", symbol, exc)
        return None


def _fetch_binance_weekly_change(symbol: str) -> Optional[float]:
    """Fetch 7-day price change from Binance klines."""
    try:
        resp = requests.get(
            BINANCE_KLINES_URL,
            params={"symbol": symbol, "interval": "1d", "limit": 8},
            timeout=10,
        )
        resp.raise_for_status()
        klines = resp.json()
        if len(klines) < 2:
            return None
        # klines[0] = oldest open, klines[-1] = current (incomplete candle)
        oldest_close = float(klines[0][4])
        current_close = float(klines[-1][4])
        if oldest_close == 0:
            return None
        return ((current_close - oldest_close) / oldest_close) * 100
    except Exception as exc:
        logger.warning("Binance klines error for %s: %s", symbol, exc)
        return None


# ---------------------------------------------------------------------------
# BCB CDI helper
# ---------------------------------------------------------------------------

def _get_cdi_annual_rate() -> Optional[float]:
    """Fetch current CDI annual rate from BCB. Returns decimal (e.g. 0.1075 = 10.75%)."""
    try:
        resp = requests.get(BCB_CDI_URL, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # BCB returns daily CDI rate — annualize: (1 + daily)^252 - 1
        daily_rate = float(data[0]["valor"]) / 100
        annual_rate = (1 + daily_rate) ** 252 - 1
        return annual_rate
    except Exception as exc:
        logger.warning("BCB CDI fetch error: %s — using fallback 0.1075", exc)
        return 0.1075  # fallback ~10.75% CDI


# ---------------------------------------------------------------------------
# Celery Tasks
# ---------------------------------------------------------------------------

@shared_task(name="opportunity_detector.scan_acoes")
def scan_acoes_opportunities() -> dict:
    """Scan top 30 IBOV stocks for significant drops. Runs every 15min market hours."""
    r = _get_redis()
    found = []
    skipped_dedup = 0
    errors = 0

    for ticker in TOP_30_IBOV:
        try:
            quote = _fetch_brapi_quote(ticker)
            if not quote:
                errors += 1
                continue

            daily_change = quote.get("regularMarketChangePercent", 0.0)
            weekly_change = _calc_weekly_change(quote)
            current_price = quote.get("regularMarketPrice", 0.0)

            triggered = False
            period = None
            drop_pct = 0.0

            if daily_change <= ACOES_DAILY_DROP_PCT:
                triggered = True
                period = "diario"
                drop_pct = daily_change
            elif weekly_change is not None and weekly_change <= ACOES_WEEKLY_DROP_PCT:
                triggered = True
                period = "semanal"
                drop_pct = weekly_change

            if not triggered:
                continue

            if _is_deduped(r, ticker, period):
                skipped_dedup += 1
                logger.debug("Deduped %s (%s)", ticker, period)
                continue

            logger.info("OPPORTUNITY DETECTED: %s %.1f%% (%s)", ticker, drop_pct, period)
            _mark_sent(r, ticker, period)

            report = asyncio.run(run_analysis(
                ticker=ticker,
                asset_type="acao",
                drop_pct=drop_pct,
                period=period,
                current_price=current_price,
                currency="BRL",
                quote_data=quote,
            ))
            dispatch_opportunity(report)
            found.append({"ticker": ticker, "drop": drop_pct, "period": period})

            # Rate-limit BRAPI calls — free tier has caps
            time.sleep(0.5)

        except Exception as exc:
            logger.error("scan_acoes error for %s: %s", ticker, exc)
            errors += 1

    logger.info(
        "scan_acoes done: %d tickers scanned, %d opportunities, %d deduped, %d errors",
        len(TOP_30_IBOV), len(found), skipped_dedup, errors,
    )
    return {"scanned": len(TOP_30_IBOV), "opportunities": found, "errors": errors}


@shared_task(name="opportunity_detector.scan_crypto")
def scan_crypto_opportunities() -> dict:
    """Scan BTC and ETH for significant drops. Runs every 15min 24/7."""
    r = _get_redis()
    found = []

    for symbol in CRYPTO_PAIRS:
        try:
            ticker_data = _fetch_binance_ticker(symbol)
            if not ticker_data:
                continue

            daily_change = float(ticker_data.get("priceChangePercent", 0))
            current_price = float(ticker_data.get("lastPrice", 0))
            weekly_change = _fetch_binance_weekly_change(symbol)

            triggered = False
            period = None
            drop_pct = 0.0

            if daily_change <= CRYPTO_DAILY_DROP_PCT:
                triggered = True
                period = "diario"
                drop_pct = daily_change
            elif weekly_change is not None and weekly_change <= CRYPTO_WEEKLY_DROP_PCT:
                triggered = True
                period = "semanal"
                drop_pct = weekly_change

            if not triggered:
                continue

            if _is_deduped(r, symbol, period):
                logger.debug("Deduped %s (%s)", symbol, period)
                continue

            logger.info("CRYPTO OPPORTUNITY: %s %.1f%% (%s)", symbol, drop_pct, period)
            _mark_sent(r, symbol, period)

            display_name = CRYPTO_NAMES.get(symbol, symbol)
            report = asyncio.run(run_analysis(
                ticker=display_name,
                asset_type="crypto",
                drop_pct=drop_pct,
                period=period,
                current_price=current_price,
                currency="USD",
                quote_data=ticker_data,
            ))
            dispatch_opportunity(report)
            found.append({"ticker": symbol, "drop": drop_pct, "period": period})

        except Exception as exc:
            logger.error("scan_crypto error for %s: %s", symbol, exc)

    return {"scanned": len(CRYPTO_PAIRS), "opportunities": found}


@shared_task(name="opportunity_detector.scan_fixed_income")
def scan_fixed_income_opportunities() -> dict:
    """Scan Tesouro Direto rates for above-average fixed income opportunities.

    Uses rates already cached in Redis by refresh_tesouro_rates task
    (key prefix: tesouro:rates:*). Runs every 6h.
    """
    r = _get_redis()
    found = []
    cdi_rate = _get_cdi_annual_rate()

    # Collect all Tesouro Direto rates from Redis
    tesouro_keys = r.keys("tesouro:rates:*")
    if not tesouro_keys:
        logger.warning("No Tesouro Direto rates in Redis — refresh_tesouro_rates may not have run yet.")
        return {"scanned": 0, "opportunities": found}

    for key in tesouro_keys:
        try:
            raw = r.get(key)
            if not raw:
                continue
            bond = json.loads(raw)

            bond_code = bond.get("code", key.replace("tesouro:rates:", ""))
            bond_name = bond.get("name", bond_code)
            annual_rate = bond.get("annual_rate")  # decimal e.g. 0.1350 = 13.5%
            maturity_days = bond.get("maturity_days")  # days until maturity

            if annual_rate is None:
                continue

            triggered = False
            reason = ""

            # IPCA+: alert when real rate > threshold
            if "IPCA" in bond_code.upper() and annual_rate >= (TESOURO_IPCA_REAL_RATE_MIN / 100):
                triggered = True
                reason = f"Taxa real IPCA+ {annual_rate * 100:.2f}% > {TESOURO_IPCA_REAL_RATE_MIN:.1f}% mínimo"

            # Prefixado: alert when rate > CDI + spread (for short maturities)
            elif "PREFIXADO" in bond_code.upper() or "PRE" in bond_code.upper():
                if cdi_rate and annual_rate >= cdi_rate + (TESOURO_PREFIXADO_CDI_SPREAD_MIN / 100):
                    triggered = True
                    spread_pp = (annual_rate - cdi_rate) * 100
                    reason = f"Prefixado {annual_rate * 100:.2f}% = CDI+{spread_pp:.1f}pp"

            if not triggered:
                continue

            if _is_deduped(r, bond_code, "renda_fixa"):
                logger.debug("Deduped %s (renda_fixa)", bond_code)
                continue

            logger.info("FIXED INCOME OPPORTUNITY: %s — %s", bond_code, reason)
            _mark_sent(r, bond_code, "renda_fixa")

            # Build a minimal quote_data for the analyzer
            quote_data = {
                "annual_rate": annual_rate,
                "maturity_days": maturity_days,
                "reason": reason,
                "cdi_rate": cdi_rate,
            }
            report = asyncio.run(run_analysis(
                ticker=bond_name,
                asset_type="renda_fixa",
                drop_pct=0.0,  # not applicable — use rate as signal
                period="renda_fixa",
                current_price=annual_rate * 100,  # display as % for alert
                currency="BRL",
                quote_data=quote_data,
            ))
            dispatch_opportunity(report)
            found.append({"bond": bond_code, "rate": annual_rate, "reason": reason})

        except Exception as exc:
            logger.error("scan_fixed_income error for key %s: %s", key, exc)

    logger.info("scan_fixed_income done: %d bonds scanned, %d opportunities", len(tesouro_keys), len(found))
    return {"scanned": len(tesouro_keys), "opportunities": found}


@shared_task(name="opportunity_detector.generate_radar")
def generate_radar_task() -> dict:
    """Celery task to generate/refresh the radar report cache."""
    from app.modules.opportunity_detector.radar import generate_radar_report
    report = generate_radar_report(force_refresh=True)
    return {
        "generated_at": report.get("generated_at"),
        "acoes": len(report.get("acoes", [])),
        "fiis": len(report.get("fiis", [])),
        "crypto": len(report.get("crypto", [])),
        "renda_fixa": len(report.get("renda_fixa", [])),
    }
