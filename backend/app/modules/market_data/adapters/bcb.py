"""python-bcb macro data wrapper for SELIC, CDI, IPCA, and PTAX USD.

Uses the `bcb` package (python-bcb) to fetch Brazilian macro indicators
from BCB (Banco Central do Brasil) SGS (Sistema Gerenciador de Séries Temporais).

SGS series codes used:
  - CDI:   series 12  — daily interbank rate (annualized)
  - SELIC: series 11  — daily target rate (annualized)
  - IPCA:  series 433 — monthly CPI inflation

PTAX USD is fetched via bcb.PTAX CotacaoDolarDia endpoint (most accurate source).

All values are returned as Decimal using Decimal(str(float)) to avoid
IEEE 754 floating-point precision issues.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import Decimal

logger = logging.getLogger(__name__)

# SGS series codes
_CDI_CODE = 12
_SELIC_CODE = 11
_IPCA_CODE = 433


def _fetch_ptax_usd() -> Decimal:
    """Fetch the most recent BRL/USD PTAX rate from BCB.

    Tries up to 5 previous business days to handle weekends and holidays.
    Falls back to a default value if all attempts fail.
    """
    from bcb import PTAX

    ptax = PTAX()
    endpoint = ptax.get_endpoint("CotacaoDolarDia")

    # Try up to 5 previous days (handles weekends/holidays)
    for days_back in range(1, 6):
        target_date = date.today() - timedelta(days=days_back)
        try:
            df = (
                endpoint.query()
                .parameters(dataCotacao=target_date.strftime("%m-%d-%Y"))
                .collect()
            )
            if df is not None and not df.empty:
                # Use cotacaoVenda (selling rate) as standard reference
                rate = float(df["cotacaoVenda"].iloc[-1])
                return Decimal(str(rate))
        except Exception as exc:  # noqa: BLE001
            logger.debug("PTAX fetch failed for %s: %s", target_date, exc)

    logger.warning("PTAX USD fetch failed for all attempted dates — using fallback")
    # Return a reasonable fallback (will be data_stale=True in cache context)
    return Decimal("5.00")


def fetch_macro_indicators() -> dict:
    """Fetch current Brazilian macro indicators from BCB.

    Returns:
        dict with keys:
          - selic: Decimal — annual SELIC target rate (e.g., 0.1375 = 13.75%)
          - cdi: Decimal   — daily CDI rate annualized (e.g., 0.1365)
          - ipca: Decimal  — most recent monthly IPCA (e.g., 0.0052 = 0.52%)
          - ptax_usd: Decimal — BRL/USD selling rate (e.g., 5.25)
          - fetched_at: ISO 8601 timestamp string

    All Decimal values use Decimal(str(float)) for precision safety.
    """
    import bcb.sgs as sgs

    start_date = "2024-01-01"
    logger.info("Fetching macro indicators from BCB (series 11, 12, 433)")

    try:
        df = sgs.get(
            {
                _CDI_CODE: "CDI",
                _SELIC_CODE: "SELIC",
                _IPCA_CODE: "IPCA",
            },
            start=start_date,
        )
    except Exception as exc:
        logger.error("Failed to fetch BCB SGS data: %s", exc)
        raise

    # Take the most recent non-null value for each series
    def _last_value(series_name: str) -> Decimal:
        col = df[series_name].dropna()
        if col.empty:
            logger.warning("BCB series %s returned empty data", series_name)
            return Decimal("0")
        return Decimal(str(float(col.iloc[-1])))

    def _annualize(daily_pct: Decimal) -> Decimal:
        """Convert daily BCB rate (%) to annualized rate (%) using 252 business days."""
        return ((Decimal(1) + daily_pct / Decimal(100)) ** 252 - Decimal(1)) * Decimal(100)

    selic = _annualize(_last_value("SELIC"))
    cdi = _annualize(_last_value("CDI"))
    ipca = _last_value("IPCA")

    try:
        ptax_usd = _fetch_ptax_usd()
    except Exception as exc:  # noqa: BLE001
        logger.error("PTAX USD fetch failed: %s", exc)
        ptax_usd = Decimal("0")

    return {
        "selic": selic,
        "cdi": cdi,
        "ipca": ipca,
        "ptax_usd": ptax_usd,
        "fetched_at": datetime.utcnow().isoformat(),
    }
