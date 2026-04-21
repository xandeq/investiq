"""brapi.dev HTTP client for B3 market data.

brapi.dev API documentation:
  Base URL: https://brapi.dev/api
  Endpoints used:
    - GET /quote/list?search={tickers_csv}&token={token}   — batch quotes
    - GET /quote/{ticker}?modules=...&token={token}         — fundamentals
    - GET /quote/{ticker}?range=1y&interval=1d&token={token} — historical
    - GET /quote/%5EBVSP?token={token}                      — IBOVESPA (^BVSP)

PLAN NOTES:
  brapi.dev Pro plan required for production use.
  Free tier: 15,000 req/month, 30-min delay, modules often return 400.
  Pro plan: no rate limit, 15-min delay, all modules available.
  With Pro: _BATCH_SLEEP_SECONDS can be reduced or removed.

Token resolution:
  1. BRAPI_TOKEN env var (container env / .env file)
  2. AWS Secrets Manager (tools/brapi → BRAPI_TOKEN)
  3. Empty string — unauthenticated (dev only)
"""
from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

BRAPI_BASE_URL = "https://brapi.dev/api"
_RETRY_AFTER_SECONDS = 5
# Pro plan: no need for aggressive throttling — 0.05s is enough to be polite
_BATCH_SLEEP_SECONDS = float(os.environ.get("BRAPI_SLEEP", "0.05"))


class BrapiRateLimitError(Exception):
    """Raised when brapi.dev returns 429 or 5xx and retry also fails."""


def _fetch_token_from_aws() -> str:
    """Fetch BRAPI_TOKEN from AWS Secrets Manager."""
    try:
        import json
        import boto3
        from botocore.exceptions import ClientError

        client = boto3.client("secretsmanager", region_name="us-east-1")
        resp = client.get_secret_value(SecretId="tools/brapi")
        secret = json.loads(resp["SecretString"])
        token = secret.get("BRAPI_TOKEN", "")
        if token:
            logger.info("brapi.dev token loaded from AWS Secrets Manager")
        return token
    except ImportError:
        logger.warning("boto3 not available — brapi.dev token not fetched from AWS SM")
        return ""
    except Exception as exc:
        logger.warning("Failed to fetch brapi.dev token from AWS SM: %s", exc)
        return ""


class BrapiClient:
    """HTTP client for brapi.dev B3 market data API.

    Token resolution order:
      1. Constructor argument (testing / explicit override)
      2. BRAPI_TOKEN environment variable
      3. AWS Secrets Manager (tools/brapi → BRAPI_TOKEN)
      4. Empty string — unauthenticated free tier (dev mode)
    """

    def __init__(self, token: str | None = None) -> None:
        if token is not None:
            self._token = token
        else:
            self._token = os.environ.get("BRAPI_TOKEN") or _fetch_token_from_aws()
            if not self._token:
                logger.warning(
                    "BRAPI_TOKEN not found — using unauthenticated free tier "
                    "(limited to 4 tickers, 30-min delay). Set BRAPI_TOKEN env var."
                )

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Perform a GET request with retry on 429/5xx."""
        url = f"{BRAPI_BASE_URL}{path}"
        all_params = {"token": self._token} if self._token else {}
        if params:
            all_params.update(params)

        resp = requests.get(url, params=all_params, timeout=20)

        if resp.status_code in (429, 500, 502, 503, 504):
            logger.warning(
                "brapi.dev returned %s for %s — retrying after %ss",
                resp.status_code, path, _RETRY_AFTER_SECONDS,
            )
            time.sleep(_RETRY_AFTER_SECONDS)
            resp = requests.get(url, params=all_params, timeout=20)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise BrapiRateLimitError(
                    f"brapi.dev returned {resp.status_code} on retry for {path}"
                )

        resp.raise_for_status()
        return resp.json()

    def fetch_quotes(self, tickers: list[str]) -> list[dict]:
        """Fetch B3 stock quotes for a list of tickers.

        With Pro: uses comma-separated batch endpoint (faster).
        Falls back to individual calls if batch fails.
        Returns list of dicts with price, change, change_pct + 52w high/low.
        """
        results = []
        # Try batch first (Pro supports comma-separated tickers in path)
        try:
            tickers_str = ",".join(t.upper() for t in tickers)
            time.sleep(_BATCH_SLEEP_SECONDS)
            data = self._get(f"/quote/{tickers_str}")
            for r in data.get("results", []):
                results.append(self._parse_quote(r))
            if results:
                return results
        except Exception:
            pass  # Fall back to individual calls

        # Individual fallback
        for ticker in tickers:
            try:
                time.sleep(_BATCH_SLEEP_SECONDS)
                data = self._get(f"/quote/{ticker.upper()}")
                ticker_results = data.get("results", [])
                if ticker_results:
                    results.append(self._parse_quote(ticker_results[0]))
            except Exception as exc:
                logger.warning("fetch_quotes: skipping %s — %s", ticker, exc)
        return results

    def _parse_quote(self, r: dict) -> dict:
        """Parse a single quote result into normalized dict."""
        return {
            "symbol": r.get("symbol", ""),
            "regularMarketPrice": r.get("regularMarketPrice", 0.0),
            "regularMarketChange": r.get("regularMarketChange", 0.0),
            "regularMarketChangePercent": r.get("regularMarketChangePercent", 0.0),
            "fiftyTwoWeekHigh": r.get("fiftyTwoWeekHigh"),
            "fiftyTwoWeekLow": r.get("fiftyTwoWeekLow"),
            "marketCap": r.get("marketCap"),
            "volume": r.get("regularMarketVolume"),
            "averageVolume": r.get("averageDailyVolume3Month") or r.get("averageVolume"),
        }

    def fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch comprehensive fundamental data for a single ticker.

        With Pro: all modules available — returns P/L, P/VP, DY, ROE, ROA,
        margens, receita, dívida, EBITDA, FCL, and more.
        Without Pro: modules return 400 → falls back to base quote fields.

        Returns dict with standardized keys (None for unavailable fields).
        """
        def _extract(d: dict, key: str) -> float | None:
            val = d.get(key)
            if val is None:
                return None
            if isinstance(val, dict):
                raw = val.get("raw")
                return float(raw) if raw is not None else None
            try:
                return float(val)
            except (TypeError, ValueError):
                return None

        def _parse_full_response(result: dict) -> dict:
            key_stats = result.get("defaultKeyStatistics", {}) or {}
            financial = result.get("financialData", {}) or {}
            summary = result.get("summaryProfile", {}) or {}

            return {
                # Valuation
                "pl": (
                    _extract(key_stats, "forwardPE")
                    or _extract(key_stats, "trailingPE")
                    or result.get("priceEarnings")
                ),
                "pvp": _extract(key_stats, "priceToBook"),
                "ev_ebitda": _extract(key_stats, "enterpriseToEbitda"),
                "variacao_12m": _extract(key_stats, "52WeekChange"),
                "beta": _extract(key_stats, "beta"),
                "market_cap": _extract(key_stats, "marketCap") or result.get("marketCap"),
                "enterprise_value": _extract(key_stats, "enterpriseValue"),
                "book_value_per_share": _extract(key_stats, "bookValue"),
                "eps": _extract(key_stats, "trailingEps") or _extract(key_stats, "earningsPerShare"),

                # Income / profitability
                "dy": _extract(financial, "dividendYield") or _extract(key_stats, "yield"),
                "roe": _extract(financial, "returnOnEquity"),
                "roa": _extract(financial, "returnOnAssets"),
                "margem_bruta": _extract(financial, "grossMargins"),
                "margem_operacional": _extract(financial, "operatingMargins"),
                "margem_liquida": _extract(financial, "profitMargins"),
                "receita_liquida": _extract(financial, "totalRevenue"),
                "ebitda": _extract(financial, "ebitda"),
                "lucro_liquido": _extract(financial, "netIncome") or _extract(financial, "totalCash"),  # approx
                "fluxo_caixa_livre": _extract(financial, "freeCashflow"),

                # Balance sheet / debt
                "divida_total": _extract(financial, "totalDebt"),
                "caixa": _extract(financial, "totalCash"),
                "divida_liquida": (
                    (_extract(financial, "totalDebt") or 0) - (_extract(financial, "totalCash") or 0)
                    if _extract(financial, "totalDebt") is not None else None
                ),
                "divida_sobre_ebitda": (
                    round((_extract(financial, "totalDebt") or 0) / _extract(financial, "ebitda"), 2)
                    if _extract(financial, "ebitda") and _extract(financial, "totalDebt") else None
                ),
                "current_ratio": _extract(financial, "currentRatio"),
                "debt_to_equity": _extract(financial, "debtToEquity"),

                # Sector info
                "setor": summary.get("sector") or summary.get("sectorKey"),
                "industria": summary.get("industry"),
            }

        time.sleep(_BATCH_SLEEP_SECONDS)
        try:
            data = self._get(
                f"/quote/{ticker.upper()}",
                params={"modules": "defaultKeyStatistics,financialData,summaryProfile"},
            )
        except requests.HTTPError as exc:
            response = exc.response
            error_code = None
            if response is not None:
                try:
                    error_code = response.json().get("code")
                except ValueError:
                    error_code = None
            if response is None or response.status_code != 400 or error_code != "MODULES_NOT_AVAILABLE":
                raise

            logger.info(
                "brapi.dev modules unavailable for %s (free plan) — using base quote",
                ticker.upper(),
            )
            data = self._get(f"/quote/{ticker.upper()}")

        results = data.get("results", [{}])
        result = results[0] if results else {}
        parsed = _parse_full_response(result)
        return parsed

    def fetch_historical(self, ticker: str, range: str = "6mo") -> list[dict]:
        """Fetch historical OHLCV data for a ticker.

        Default range changed to 6mo (Pro allows longer history for better
        multi-timeframe analysis). Use range='1y' for annual context.

        Returns list of dicts: date (epoch), open, high, low, close, volume.
        """
        time.sleep(_BATCH_SLEEP_SECONDS)
        data = self._get(
            f"/quote/{ticker.upper()}",
            params={"range": range, "interval": "1d"},
        )
        results = data.get("results", [{}])
        r = results[0] if results else {}
        points = r.get("historicalDataPrice", [])
        return [
            {
                "date": p.get("date", 0),
                "open": p.get("open") or 0.0,
                "high": p.get("high") or 0.0,
                "low": p.get("low") or 0.0,
                "close": p.get("close") or 0.0,
                "volume": p.get("volume") or 0,
            }
            for p in points
            if p.get("close")  # skip empty rows
        ]

    def fetch_quote_with_52w(self, ticker: str) -> dict | None:
        """Fetch quote including 52-week high/low, P/L, market cap.

        Used by the radar de oportunidades for discount calculation.
        Returns None on any error.
        """
        try:
            time.sleep(_BATCH_SLEEP_SECONDS)
            data = self._get(f"/quote/{ticker.upper()}")
            results = data.get("results", [])
            if not results:
                return None
            r = results[0]
            return {
                "symbol": r.get("symbol", ticker.upper()),
                "regularMarketPrice": r.get("regularMarketPrice"),
                "fiftyTwoWeekHigh": r.get("fiftyTwoWeekHigh"),
                "fiftyTwoWeekLow": r.get("fiftyTwoWeekLow"),
                "priceEarnings": r.get("priceEarnings"),
                "marketCap": r.get("marketCap"),
                "regularMarketChangePercent": r.get("regularMarketChangePercent"),
                "logourl": r.get("logourl"),
            }
        except Exception as exc:
            logger.warning("fetch_quote_with_52w: %s failed — %s", ticker, exc)
            return None

    def fetch_dividends(self, ticker: str) -> list[dict]:
        """Fetch dividend history for a ticker (requires Pro for dividendsData module).

        Returns list of {rate, paymentDate, label} sorted newest first.
        """
        try:
            time.sleep(_BATCH_SLEEP_SECONDS)
            data = self._get(
                f"/quote/{ticker.upper()}",
                params={"modules": "dividendsData"},
            )
            results = data.get("results", [{}])
            r = results[0] if results else {}
            dividends_data = r.get("dividendsData", {}) or {}
            cash_dividends = dividends_data.get("cashDividends", []) or []
            return sorted(cash_dividends, key=lambda d: d.get("paymentDate", ""), reverse=True)
        except Exception as exc:
            logger.debug("fetch_dividends: %s failed — %s", ticker, exc)
            return []

    def fetch_ibovespa(self) -> dict:
        """Fetch IBOVESPA index quote (^BVSP)."""
        time.sleep(_BATCH_SLEEP_SECONDS)
        data = self._get("/quote/%5EBVSP")
        results = data.get("results", [{}])
        r = results[0] if results else {}
        return {
            "symbol": r.get("symbol", "^BVSP"),
            "regularMarketPrice": r.get("regularMarketPrice", 0.0),
            "regularMarketChange": r.get("regularMarketChange", 0.0),
            "regularMarketChangePercent": r.get("regularMarketChangePercent", 0.0),
        }
