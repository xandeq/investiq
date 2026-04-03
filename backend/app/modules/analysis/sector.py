"""Sector peer comparison analysis for B3 stocks (Phase 14 Plan 01).

Compares a target ticker against 5-10 sector peers on key valuation metrics:
P/E ratio, P/B ratio, Dividend Yield, and ROE.

Usage:
    from app.modules.analysis.sector import calculate_sector_comparison, _SECTOR_TICKERS
"""
from __future__ import annotations

import logging
import statistics
from typing import Any

from app.modules.analysis.data import DataFetchError, fetch_fundamentals

logger = logging.getLogger(__name__)

# Hardcoded sector-to-ticker mapping for B3 stocks.
# Keys match the `sector_key` field returned by fetch_fundamentals() (from BRAPI/yFinance).
_SECTOR_TICKERS: dict[str, list[str]] = {
    "energy": ["PETR4", "PETR3", "CSAN3", "PRIO3", "RECV3", "RRRP3", "UGPA3", "VBBR3"],
    "financial-services": ["ITUB4", "BBDC4", "BBAS3", "SANB11", "BPAC11", "BRSR6", "ABCB4", "BMGB4"],
    "basic-materials": ["VALE3", "SUZB3", "KLBN11", "GGBR4", "CSNA3", "USIM5", "GOAU4", "BRAP4"],
    "utilities": ["ELET3", "SBSP3", "CPFE3", "ENGI11", "CMIG4", "TAEE11", "EGIE3", "EQTL3"],
    "consumer-defensive": ["ABEV3", "NTCO3", "PCAR3", "CRFB3", "ASAI3", "MDIA3", "SLCE3"],
    "consumer-cyclical": ["MGLU3", "LREN3", "ARZZ3", "VIVT3", "RENT3", "LCAM3", "ALPA4"],
    "healthcare": ["RDOR3", "HAPV3", "FLRY3", "QUAL3", "HYPE3", "RADL3"],
    "technology": ["TOTS3", "LWSA3", "CASH3", "POSI3", "INTB3"],
    "industrials": ["WEGE3", "EMBR3", "RAIL3", "CCRO3", "ECOR3", "AZUL4"],
    "real-estate": ["CYRE3", "MRVE3", "EZTC3", "EVEN3", "MULT3", "IGTI11"],
    "communication-services": ["VIVT3", "TIMS3", "OIBR3"],
}

_METRICS = ["pe_ratio", "price_to_book", "dividend_yield", "roe"]


def _safe_float(value: Any) -> float | None:
    """Convert value to float, returning None on failure."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _calc_average(values: list[float]) -> float | None:
    """Calculate average of a list of non-None floats."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return round(sum(filtered) / len(filtered), 4)


def _calc_median(values: list[float]) -> float | None:
    """Calculate median of a list of non-None floats."""
    filtered = [v for v in values if v is not None]
    if not filtered:
        return None
    return round(statistics.median(filtered), 4)


def _calc_percentile_rank(target_value: float | None, peer_values: list[float | None]) -> float | None:
    """Calculate percentile rank of target value among peers.

    Counts how many peers have a value <= target, divides by total peers with data.
    Returns 0-100 scale.
    """
    if target_value is None:
        return None
    valid_peers = [v for v in peer_values if v is not None]
    if not valid_peers:
        return None
    count_lte = sum(1 for v in valid_peers if v <= target_value)
    return round((count_lte / len(valid_peers)) * 100, 1)


def calculate_sector_comparison(
    target_fundamentals: dict,
    peer_fundamentals: list[dict],
    ticker: str,
) -> dict:
    """Calculate sector peer comparison for a target ticker.

    Args:
        target_fundamentals: Flat dict from fetch_fundamentals() for the target ticker.
        peer_fundamentals: List of flat dicts from fetch_fundamentals() for each peer.
        ticker: The target ticker symbol (uppercase).

    Returns:
        Dict with sector averages, medians, percentile ranks, and peer data.
    """
    sector = target_fundamentals.get("sector", "Unknown")
    sector_key = target_fundamentals.get("sector_key", "")

    # Extract target metrics
    target_metrics = {
        metric: _safe_float(target_fundamentals.get(metric))
        for metric in _METRICS
    }

    # Build peers list with their metrics
    peers: list[dict] = []
    for peer_fund in peer_fundamentals:
        # peer ticker is injected by fetch_peer_fundamentals() under "_ticker" key
        peer_ticker = peer_fund.get("_ticker") or peer_fund.get("ticker", "")
        if not peer_ticker:
            continue
        peer_data: dict = {
            "ticker": peer_ticker,
            "current_price": _safe_float(peer_fund.get("current_price")),
            "market_cap": _safe_float(peer_fund.get("market_cap")),
        }
        for metric in _METRICS:
            peer_data[metric] = _safe_float(peer_fund.get(metric))
        peers.append(peer_data)

    # Gather metric values across all peers for stats
    peers_with_data = len(peers)
    peers_attempted = target_fundamentals.get("_peers_attempted", peers_with_data)

    # Calculate sector averages and medians per metric
    sector_averages: dict = {}
    sector_medians: dict = {}
    target_percentiles: dict = {}

    for metric in _METRICS:
        peer_values = [p[metric] for p in peers]
        sector_averages[metric] = _calc_average(peer_values)
        sector_medians[metric] = _calc_median(peer_values)
        target_percentiles[metric] = _calc_percentile_rank(target_metrics[metric], peer_values)

    return {
        "ticker": ticker,
        "sector": sector,
        "sector_key": sector_key,
        "peers_found": peers_with_data,
        "peers_attempted": peers_attempted,
        "max_peers": target_fundamentals.get("_max_peers", len(peers)),
        "target_metrics": target_metrics,
        "sector_averages": sector_averages,
        "sector_medians": sector_medians,
        "target_percentiles": target_percentiles,
        "peers": peers,
        "data_completeness": {
            "peers_with_data": peers_with_data,
            "peers_without_data": peers_attempted - peers_with_data,
            "missing_tickers": target_fundamentals.get("_missing_tickers", []),
            "note": (
                f"{peers_with_data} of {peers_attempted} peers included; "
                f"{peers_attempted - peers_with_data} missing data"
            ),
        },
    }


def fetch_peer_fundamentals(
    peer_tickers: list[str],
    target_ticker: str,
) -> tuple[list[dict], list[str]]:
    """Fetch fundamentals for each peer ticker, skipping failures.

    Args:
        peer_tickers: List of peer ticker symbols to fetch.
        target_ticker: The target ticker to exclude from peers.

    Returns:
        Tuple of (successful_peer_fundamentals, missing_tickers).
    """
    peer_fundamentals: list[dict] = []
    missing_tickers: list[str] = []

    for peer_ticker in peer_tickers:
        if peer_ticker.upper() == target_ticker.upper():
            continue
        try:
            fund = fetch_fundamentals(peer_ticker)
            # Inject ticker symbol so calculate_sector_comparison can identify peers
            fund = dict(fund)
            fund["_ticker"] = peer_ticker.upper()
            peer_fundamentals.append(fund)
        except DataFetchError as exc:
            logger.warning("Failed to fetch fundamentals for peer %s: %s", peer_ticker, exc)
            missing_tickers.append(peer_ticker)
        except Exception as exc:
            logger.warning("Unexpected error fetching peer %s: %s", peer_ticker, exc)
            missing_tickers.append(peer_ticker)

    return peer_fundamentals, missing_tickers
