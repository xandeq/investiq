"""brapi.dev HTTP client for B3 market data.

brapi.dev API documentation:
  Base URL: https://brapi.dev/api
  Endpoints used:
    - GET /quote/list?search={tickers_csv}&token={token}   — batch quotes
    - GET /quote/{ticker}?modules=...&token={token}         — fundamentals
    - GET /quote/{ticker}?range=1y&interval=1d&token={token} — historical
    - GET /quote/%5EBVSP?token={token}                      — IBOVESPA (^BVSP)

PRODUCTION NOTE:
  brapi.dev Startup plan (R$59.99/mo) required for production use.
  Free tier: 15,000 req/month, 30-min delay.
  Startup plan: no published rate limit, 15-min delay.
  Implementation adds 200ms sleep between batch calls to avoid throttling.

AWS Secrets Manager:
  Token is fetched from secret_id="tools/brapi", key="BRAPI_TOKEN".
  Fetched once at BrapiClient construction and cached in process memory.
  Never hardcoded, never written to logs.
"""
from __future__ import annotations

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

BRAPI_BASE_URL = "https://brapi.dev/api"
_RETRY_AFTER_SECONDS = 5
_BATCH_SLEEP_SECONDS = 0.2


class BrapiRateLimitError(Exception):
    """Raised when brapi.dev returns 429 or 5xx and retry also fails."""


def _fetch_token_from_aws() -> str:
    """Fetch BRAPI_TOKEN from AWS Secrets Manager.

    Returns empty string if boto3 is unavailable or secret is missing.
    An empty token allows unauthenticated access on the free tier (4 tickers).
    """
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
    except Exception as exc:  # noqa: BLE001
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
                    "(limited to 4 tickers, 30-min delay). Set BRAPI_TOKEN env var or "
                    "store in AWS SM at tools/brapi for production use."
                )

    def _get(self, path: str, params: dict | None = None) -> dict:
        """Perform a GET request with retry on 429/5xx."""
        url = f"{BRAPI_BASE_URL}{path}"
        all_params = {"token": self._token} if self._token else {}
        if params:
            all_params.update(params)

        resp = requests.get(url, params=all_params, timeout=15)

        if resp.status_code in (429, 500, 502, 503, 504):
            logger.warning(
                "brapi.dev returned %s for %s — retrying after %ss",
                resp.status_code,
                path,
                _RETRY_AFTER_SECONDS,
            )
            time.sleep(_RETRY_AFTER_SECONDS)
            resp = requests.get(url, params=all_params, timeout=15)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise BrapiRateLimitError(
                    f"brapi.dev returned {resp.status_code} on retry for {path}"
                )

        resp.raise_for_status()
        return resp.json()

    def fetch_quotes(self, tickers: list[str]) -> list[dict]:
        """Fetch B3 stock quotes for a list of tickers.

        Calls /quote/{ticker} individually for each ticker — BRAPI free plan
        does not support comma-separated batch in the path.
        Returns list of dicts with keys:
          symbol, regularMarketPrice, regularMarketChange, regularMarketChangePercent
        """
        results = []
        for ticker in tickers:
            try:
                time.sleep(_BATCH_SLEEP_SECONDS)
                data = self._get(f"/quote/{ticker.upper()}")
                ticker_results = data.get("results", [])
                if ticker_results:
                    r = ticker_results[0]
                    results.append({
                        "symbol": r.get("symbol", ticker.upper()),
                        "regularMarketPrice": r.get("regularMarketPrice", 0.0),
                        "regularMarketChange": r.get("regularMarketChange", 0.0),
                        "regularMarketChangePercent": r.get("regularMarketChangePercent", 0.0),
                    })
            except Exception as exc:
                logger.warning("fetch_quotes: skipping %s — %s", ticker, exc)
        return results

    def fetch_fundamentals(self, ticker: str) -> dict:
        """Fetch fundamental analysis data for a single ticker.

        Returns dict with keys: pl, pvp, dy, ev_ebitda
        Values may be None if brapi.dev does not return them.
        """
        time.sleep(_BATCH_SLEEP_SECONDS)
        data = self._get(
            f"/quote/{ticker.upper()}",
            params={"modules": "defaultKeyStatistics,financialData"},
        )
        results = data.get("results", [{}])
        r = results[0] if results else {}

        key_stats = r.get("defaultKeyStatistics", {})
        financial = r.get("financialData", {})

        def _extract(d: dict, key: str) -> float | None:
            val = d.get(key)
            if val is None:
                return None
            if isinstance(val, dict):
                return val.get("raw")
            return val

        pvp = _extract(key_stats, "priceToBook")
        dy_raw = _extract(financial, "dividendYield")
        ev_ebitda = _extract(key_stats, "enterpriseToEbitda")
        # P/L from forwardPE or trailingPE
        pl = _extract(key_stats, "forwardPE") or _extract(key_stats, "trailingPE")

        return {
            "pl": pl,
            "pvp": pvp,
            "dy": dy_raw,
            "ev_ebitda": ev_ebitda,
        }

    def fetch_historical(self, ticker: str, range: str = "1y") -> list[dict]:
        """Fetch historical OHLCV data for a ticker.

        Returns list of dicts with keys:
          date (unix epoch int), open, high, low, close, volume
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
                "open": p.get("open", 0.0),
                "high": p.get("high", 0.0),
                "low": p.get("low", 0.0),
                "close": p.get("close", 0.0),
                "volume": p.get("volume", 0),
            }
            for p in points
        ]

    def fetch_ibovespa(self) -> dict:
        """Fetch IBOVESPA index quote (^BVSP).

        Returns dict with regularMarketPrice, regularMarketChange,
        regularMarketChangePercent and symbol keys.
        """
        # ^BVSP URL-encoded is %5EBVSP
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
