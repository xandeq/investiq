"""BRAPI fundamentals data fetching + BCB SELIC integration (Phase 13).

Provides real financial data for DCF and other analysis types.
All data cached in Redis with 24h TTL per ticker.

Data sources:
- BRAPI: B3 stock fundamentals (financials, cashflow, income history)
- BCB: SELIC target rate (serie 432)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

_BRAPI_BASE_URL = "https://brapi.dev/api"
_BCB_SELIC_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados/ultimos/1?formato=json"

_CACHE_TTL_SECONDS = 86400  # 24h

# SELIC fallback when BCB API is unavailable
_SELIC_FALLBACK_RATE = 0.1475
_SELIC_FALLBACK_DATE = "2026-03-19"


class DataFetchError(Exception):
    """Raised when external data source fails to return usable data."""

    def __init__(self, ticker: str, source: str, detail: str) -> None:
        self.ticker = ticker
        self.source = source
        self.detail = detail
        super().__init__(f"{source} error for {ticker}: {detail}")


def _get_sync_redis():
    """Get synchronous Redis client (same pattern as wizard/tasks.py)."""
    import redis as sync_redis

    return sync_redis.from_url(
        os.environ.get("REDIS_URL", "redis://redis:6379/0"),
        decode_responses=True,
    )


def _extract(d: dict, key: str) -> float | None:
    """Extract value handling BRAPI's raw/fmt dict pattern.

    BRAPI sometimes returns values as raw numbers, sometimes as
    {"raw": 1.53, "fmt": "1.53"} dicts. This handles both.
    """
    val = d.get(key)
    if val is None:
        return None
    if isinstance(val, dict):
        return val.get("raw")
    return val


def _resolve_brapi_token() -> str:
    """Resolve BRAPI token using same priority as BrapiClient."""
    token = os.environ.get("BRAPI_TOKEN", "")
    if token:
        return token
    # Try AWS SM as last resort
    try:
        from app.modules.market_data.adapters.brapi import _fetch_token_from_aws

        return _fetch_token_from_aws()
    except Exception:
        return ""


def fetch_fundamentals(ticker: str) -> dict:
    """Fetch comprehensive fundamentals from BRAPI with Redis caching.

    Returns flat dict with financial metrics, history arrays, and
    data_completeness metadata.

    Raises:
        DataFetchError: If BRAPI returns error or critical data missing.
    """
    cache_key = f"brapi:fundamentals:{ticker.upper()}"

    # Check Redis cache
    try:
        r = _get_sync_redis()
        cached = r.get(cache_key)
        if cached:
            logger.info("Cache hit for %s fundamentals", ticker)
            return json.loads(cached)
    except Exception as exc:
        logger.warning("Redis cache read failed for %s: %s", ticker, exc)

    # Fetch from BRAPI
    token = _resolve_brapi_token()
    params = {
        "modules": "summaryProfile,defaultKeyStatistics,financialData,incomeStatementHistory,cashflowHistory",
        "fundamental": "true",
        "dividends": "true",
    }
    if token:
        params["token"] = token

    try:
        url = f"{_BRAPI_BASE_URL}/quote/{ticker.upper()}"
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        raise DataFetchError(ticker, "BRAPI", str(exc))

    results = data.get("results", [])
    if not results:
        raise DataFetchError(ticker, "BRAPI", "No results returned")

    r_data = results[0]

    # Extract from each module
    summary_profile = r_data.get("summaryProfile", {})
    key_stats = r_data.get("defaultKeyStatistics", {})
    financial = r_data.get("financialData", {})
    income_history = r_data.get("incomeStatementHistory", [])
    cashflow_history = r_data.get("cashflowHistory", [])
    dividends_data = r_data.get("dividendsData", {})

    # Current price from top-level result
    current_price = r_data.get("regularMarketPrice")

    # Parse fields with _extract for raw/fmt handling
    eps = _extract(key_stats, "earningsPerShare")
    pe_ratio = _extract(key_stats, "trailingPE") or _extract(key_stats, "forwardPE")
    price_to_book = _extract(key_stats, "priceToBook")
    beta = _extract(key_stats, "beta")
    enterprise_value = _extract(key_stats, "enterpriseValue")
    ev_ebitda = _extract(key_stats, "enterpriseToEbitda")
    book_value = _extract(key_stats, "bookValue")

    total_revenue = _extract(financial, "totalRevenue")
    ebitda = _extract(financial, "ebitda")
    free_cash_flow = _extract(financial, "freeCashflow")
    total_debt = _extract(financial, "totalDebt")
    total_cash = _extract(financial, "totalCash")
    debt_to_equity = _extract(financial, "debtToEquity")
    profit_margins = _extract(financial, "profitMargins")
    roe = _extract(financial, "returnOnEquity")
    current_ratio = _extract(financial, "currentRatio")
    dividend_yield = _extract(financial, "dividendYield") or _extract(key_stats, "yield")
    market_cap = _extract(key_stats, "marketCap") or r_data.get("marketCap")

    # Calculate shares outstanding from market cap / price
    shares_outstanding = None
    if market_cap and current_price and current_price > 0:
        shares_outstanding = market_cap / current_price

    # Parse income statement history
    parsed_income = []
    for stmt in income_history:
        parsed_income.append({
            "end_date": stmt.get("endDate"),
            "total_revenue": _extract(stmt, "totalRevenue"),
            "cost_of_revenue": _extract(stmt, "costOfRevenue"),
            "gross_profit": _extract(stmt, "grossProfit"),
            "ebit": _extract(stmt, "ebit"),
            "net_income": _extract(stmt, "netIncome"),
        })

    # Parse cashflow history
    parsed_cashflow = []
    for cf in cashflow_history:
        parsed_cashflow.append({
            "end_date": cf.get("endDate"),
            "operating_cash_flow": _extract(cf, "operatingCashFlow"),
            "free_cash_flow": _extract(cf, "freeCashFlow"),
            "investment_cash_flow": _extract(cf, "investmentCashFlow"),
            "financing_cash_flow": _extract(cf, "financingCashFlow"),
        })

    # Parse dividends
    cash_dividends = dividends_data.get("cashDividends", []) if isinstance(dividends_data, dict) else []
    parsed_dividends = []
    for div in cash_dividends[:20]:  # limit to recent 20
        parsed_dividends.append({
            "rate": div.get("rate"),
            "payment_date": div.get("paymentDate"),
            "ex_date": div.get("lastDatePrior"),
            "label": div.get("label"),
        })

    # Build data completeness
    all_fields = [
        "current_price", "eps", "pe_ratio", "price_to_book", "beta",
        "enterprise_value", "ev_ebitda", "book_value", "total_revenue",
        "ebitda", "free_cash_flow", "total_debt", "total_cash",
        "debt_to_equity", "profit_margins", "roe", "current_ratio",
        "dividend_yield", "market_cap", "shares_outstanding",
    ]
    field_values = {
        "current_price": current_price, "eps": eps, "pe_ratio": pe_ratio,
        "price_to_book": price_to_book, "beta": beta,
        "enterprise_value": enterprise_value, "ev_ebitda": ev_ebitda,
        "book_value": book_value, "total_revenue": total_revenue,
        "ebitda": ebitda, "free_cash_flow": free_cash_flow,
        "total_debt": total_debt, "total_cash": total_cash,
        "debt_to_equity": debt_to_equity, "profit_margins": profit_margins,
        "roe": roe, "current_ratio": current_ratio,
        "dividend_yield": dividend_yield, "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
    }
    available = [f for f in all_fields if field_values.get(f) is not None]
    missing = [f for f in all_fields if field_values.get(f) is None]
    completeness_pct = f"{len(available) * 100 // len(all_fields)}%"

    result = {
        "current_price": current_price,
        "eps": eps,
        "pe_ratio": pe_ratio,
        "price_to_book": price_to_book,
        "beta": beta,
        "enterprise_value": enterprise_value,
        "ev_ebitda": ev_ebitda,
        "book_value": book_value,
        "total_revenue": total_revenue,
        "ebitda": ebitda,
        "free_cash_flow": free_cash_flow,
        "total_debt": total_debt,
        "total_cash": total_cash,
        "debt_to_equity": debt_to_equity,
        "profit_margins": profit_margins,
        "roe": roe,
        "current_ratio": current_ratio,
        "dividend_yield": dividend_yield,
        "market_cap": market_cap,
        "shares_outstanding": shares_outstanding,
        "sector": summary_profile.get("sector"),
        "sector_key": summary_profile.get("sectorKey"),
        "industry": summary_profile.get("industry"),
        "income_history": parsed_income,
        "cashflow_history": parsed_cashflow,
        "dividends_data": parsed_dividends,
        "data_completeness": {
            "available": available,
            "missing": missing,
            "completeness": completeness_pct,
        },
    }

    # Cache in Redis
    try:
        r = _get_sync_redis()
        r.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(result, ensure_ascii=False, default=str))
        logger.info("Cached fundamentals for %s (TTL=%ds)", ticker, _CACHE_TTL_SECONDS)
    except Exception as exc:
        logger.warning("Redis cache write failed for %s: %s", ticker, exc)

    return result


def get_selic_rate() -> tuple[float, str, bool]:
    """Fetch current SELIC target rate from BCB API.

    Returns:
        (rate_decimal, date_str, is_fallback)
        e.g. (0.1475, "2026-03-19", False)

    On BCB API failure, returns hardcoded fallback with is_fallback=True.
    """
    cache_key = "bcb:selic:current"

    # Check Redis cache
    try:
        r = _get_sync_redis()
        cached = r.get(cache_key)
        if cached:
            data = json.loads(cached)
            return (data["rate"], data["date"], data["is_fallback"])
    except Exception as exc:
        logger.warning("Redis cache read failed for SELIC: %s", exc)

    # Fetch from BCB
    try:
        resp = requests.get(_BCB_SELIC_URL, timeout=10)
        resp.raise_for_status()
        bcb_data = resp.json()

        if not bcb_data:
            raise ValueError("Empty BCB response")

        entry = bcb_data[0]
        # "valor" is percentage string like "14.75"
        rate_pct = float(entry["valor"])
        rate_decimal = rate_pct / 100.0

        # Parse date from DD/MM/YYYY to YYYY-MM-DD
        raw_date = entry["data"]
        dt = datetime.strptime(raw_date, "%d/%m/%Y")
        date_str = dt.strftime("%Y-%m-%d")

        # Cache result
        cache_data = {"rate": rate_decimal, "date": date_str, "is_fallback": False}
        try:
            r = _get_sync_redis()
            r.setex(cache_key, _CACHE_TTL_SECONDS, json.dumps(cache_data))
        except Exception as exc:
            logger.warning("Redis cache write failed for SELIC: %s", exc)

        return (rate_decimal, date_str, False)

    except Exception as exc:
        logger.warning(
            "BCB SELIC API failed, using fallback rate %.4f: %s",
            _SELIC_FALLBACK_RATE,
            exc,
        )
        return (_SELIC_FALLBACK_RATE, _SELIC_FALLBACK_DATE, True)
