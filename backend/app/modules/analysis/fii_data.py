"""BRAPI FII data fetcher with Redis caching (Phase 18).

Fetches FII-specific data: current price, DY history (monthly), P/VP,
portfolio fields from summaryProfile. Same caching pattern as data.py.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import requests

from app.modules.analysis.data import (
    _BRAPI_BASE_URL,
    _CACHE_TTL_SECONDS,
    DataFetchError,
    _extract,
    _get_sync_redis,
    _resolve_brapi_token,
)

logger = logging.getLogger(__name__)


def fetch_fii_data(ticker: str) -> dict:
    """Fetch FII detail data from BRAPI with 24h Redis cache.

    Returns dict with keys:
      current_price, pvp, dy_12m, dividends_monthly, portfolio,
      last_dividend, daily_liquidity, book_value
    """
    ticker_upper = ticker.upper()
    cache_key = f"brapi:fii_detail:{ticker_upper}"

    # Redis cache check
    try:
        r = _get_sync_redis()
        cached = r.get(cache_key)
        if cached:
            return json.loads(cached)
    except Exception as exc:
        logger.warning("Redis cache miss for FII %s: %s", ticker_upper, exc)

    # Fetch from BRAPI
    token = _resolve_brapi_token()
    params: dict = {"modules": "dividendsData,summaryProfile"}
    if token:
        params["token"] = token

    try:
        url = f"{_BRAPI_BASE_URL}/quote/{ticker_upper}"
        resp = requests.get(url, params=params, timeout=15)

        # Handle MODULES_NOT_AVAILABLE (400 from BRAPI for some tickers)
        if resp.status_code == 400:
            try:
                err_body = resp.json()
                if "MODULES_NOT_AVAILABLE" in str(err_body):
                    # Fallback: fetch base quote only (no modules)
                    base_params: dict = {}
                    if token:
                        base_params["token"] = token
                    resp2 = requests.get(
                        f"{_BRAPI_BASE_URL}/quote/{ticker_upper}",
                        params=base_params,
                        timeout=15,
                    )
                    resp2.raise_for_status()
                    data = resp2.json()
                else:
                    raise DataFetchError(ticker_upper, "BRAPI", f"HTTP 400: {err_body}")
            except DataFetchError:
                raise
            except Exception as exc:
                raise DataFetchError(ticker_upper, "BRAPI", f"HTTP 400 parse error: {exc}")
        else:
            resp.raise_for_status()
            data = resp.json()

    except DataFetchError:
        raise
    except Exception as exc:
        raise DataFetchError(ticker_upper, "BRAPI", str(exc))

    results = data.get("results", [])
    if not results:
        raise DataFetchError(ticker_upper, "BRAPI", "No results returned")

    r_data = results[0]
    current_price = r_data.get("regularMarketPrice")
    daily_volume = r_data.get("regularMarketVolume")
    key_stats = r_data.get("defaultKeyStatistics", {}) or {}
    summary_profile = r_data.get("summaryProfile", {}) or {}
    dividends_data = r_data.get("dividendsData", {}) or {}

    book_value = _extract(key_stats, "bookValue")
    price_to_book = _extract(key_stats, "priceToBook")

    # Parse cashDividends into monthly aggregation (last 12 months)
    cash_dividends = dividends_data.get("cashDividends", []) or []
    dividends_monthly, dy_12m, last_dividend = _parse_dividends_monthly(
        cash_dividends, current_price
    )

    # Portfolio fields from summaryProfile (defensive — BRAPI may not return these)
    portfolio = {
        "num_imoveis": summary_profile.get("numberOfProperties")
        or summary_profile.get("numImoveis"),
        "tipo_contrato": summary_profile.get("contractType")
        or summary_profile.get("tipoContrato"),
        "vacancia": summary_profile.get("vacancy") or summary_profile.get("vacancia"),
    }

    # P/VP: use priceToBook from BRAPI key_stats, or compute if both values available
    pvp = price_to_book
    if pvp is None and current_price and book_value and book_value > 0:
        pvp = round(current_price / book_value, 2)

    result = {
        "current_price": current_price,
        "pvp": pvp,
        "dy_12m": dy_12m,
        "dividends_monthly": dividends_monthly,
        "portfolio": portfolio,
        "last_dividend": last_dividend,
        "daily_liquidity": daily_volume,
        "book_value": book_value,
    }

    # Cache in Redis (24h TTL)
    try:
        r = _get_sync_redis()
        r.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(result))
    except Exception as exc:
        logger.warning("Redis cache write failed for FII %s: %s", ticker_upper, exc)

    return result


def _parse_dividends_monthly(
    cash_dividends: list, current_price: float | None
) -> tuple[list, float | None, float | None]:
    """Parse BRAPI cashDividends into monthly aggregation for last 12 months."""
    if not cash_dividends:
        return [], None, None

    now = datetime.now()
    twelve_months_ago = now - timedelta(days=365)

    # Aggregate by YYYY-MM, limit to last 12 months
    monthly: dict[str, float] = defaultdict(float)
    last_dividend = None

    for div in cash_dividends:
        rate = div.get("rate")
        if rate is None:
            continue

        date_str = div.get("paymentDate", "")
        parsed_date = _parse_date(date_str)
        if parsed_date is None:
            continue

        if parsed_date >= twelve_months_ago:
            month_key = parsed_date.strftime("%Y-%m")
            monthly[month_key] += float(rate)

    # Sort ascending by month, take last 12
    sorted_months = sorted(monthly.items())[-12:]
    dividends_monthly = [{"month": m, "rate": round(r, 4)} for m, r in sorted_months]

    # DY 12m = sum of last 12 months dividends / current price
    total_12m = sum(r for _, r in sorted_months)
    dy_12m = round(total_12m / current_price, 4) if current_price and current_price > 0 else None

    # Last dividend = most recent entry (first in BRAPI list = most recent)
    last_dividend = cash_dividends[0].get("rate") if cash_dividends else None
    if last_dividend is not None:
        last_dividend = float(last_dividend)

    return dividends_monthly, dy_12m, last_dividend


def _parse_date(date_str: str) -> datetime | None:
    """Parse date from BRAPI (handles YYYY-MM-DD, ISO, and DD/MM/YYYY)."""
    if not date_str:
        return None
    # Strip time component for ISO strings
    clean = date_str.split("T")[0] if "T" in date_str else date_str
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(clean, fmt)
        except ValueError:
            continue
    return None
