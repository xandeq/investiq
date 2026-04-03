"""Dividend sustainability analysis calculations (Phase 13 Plan 02 — AI-03).

Computes:
- Annual dividend aggregation (group by year, sum rate)
- Current yield, payout ratio, coverage ratio
- Consistency score (years paid / total years, last 5)
- Sustainability flag: safe / warning / risk
- Dividend history per year

Data source: fundamentals dict from data.py (BRAPI).
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _extract_year(date_str: str | None) -> int | None:
    """Extract year from a date string."""
    if not date_str:
        return None
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.year
    except (ValueError, AttributeError):
        try:
            return int(str(date_str)[:4])
        except (ValueError, TypeError):
            return None


def aggregate_annual_dividends(cash_dividends: list[dict]) -> dict[int, float]:
    """Aggregate dividend payments by year.

    Groups all dividend payments (DIVIDENDO, JCP, RENDIMENTO) by
    payment_date year and sums the rate.

    Args:
        cash_dividends: List of dicts with 'rate' and 'payment_date' keys.

    Returns:
        Sorted dict {year: total_dps} e.g. {2025: 2.50, 2024: 2.30}
    """
    annual: dict[int, float] = {}

    for div in cash_dividends:
        rate = div.get("rate")
        if rate is None or not isinstance(rate, (int, float)):
            continue

        year = _extract_year(div.get("payment_date"))
        if year is None:
            continue

        annual[year] = annual.get(year, 0.0) + rate

    # Round values and sort descending
    return {
        k: round(v, 4)
        for k, v in sorted(annual.items(), reverse=True)
    }


def assess_dividend_sustainability(
    payout_ratio: float | None,
    coverage_ratio: float | None,
    annual_dividends: dict[int, float],
) -> str:
    """Assess dividend sustainability.

    Risk triggers (any one triggers "risk"):
    - payout_ratio > 0.80
    - coverage_ratio < 1.2
    - Dividend cut > 20% in last 3 years

    Warning triggers (any one triggers "warning"):
    - payout_ratio > 0.60
    - coverage_ratio < 1.5

    Otherwise: "safe"

    Args:
        payout_ratio: DPS / EPS (None if EPS <= 0)
        coverage_ratio: EPS / DPS (None if DPS <= 0)
        annual_dividends: {year: total_dps} sorted descending

    Returns:
        "safe", "warning", or "risk"
    """
    # Check for dividend cut > 20% in last 3 years
    years_sorted = sorted(annual_dividends.keys(), reverse=True)
    has_major_cut = False
    if len(years_sorted) >= 2:
        for i in range(min(len(years_sorted) - 1, 3)):
            current_year_dps = annual_dividends[years_sorted[i]]
            prev_year_dps = annual_dividends[years_sorted[i + 1]]
            if prev_year_dps > 0:
                change = (current_year_dps - prev_year_dps) / prev_year_dps
                if change < -0.20:
                    has_major_cut = True
                    break

    # Risk checks
    if payout_ratio is not None and payout_ratio > 0.80:
        return "risk"
    if coverage_ratio is not None and coverage_ratio < 1.2:
        return "risk"
    if has_major_cut:
        return "risk"

    # Warning checks
    if payout_ratio is not None and payout_ratio > 0.60:
        return "warning"
    if coverage_ratio is not None and coverage_ratio < 1.5:
        return "warning"

    return "safe"


def calculate_dividend_analysis(fundamentals: dict) -> dict:
    """Calculate dividend analysis from BRAPI fundamentals.

    Args:
        fundamentals: Dict from fetch_fundamentals() with dividends_data,
                      eps, current_price, dividend_yield, etc.

    Returns:
        Dict with current_yield, payout_ratio, coverage_ratio,
        consistency, sustainability, dividend_history, data_completeness.
    """
    dividends_data = fundamentals.get("dividends_data", [])
    eps = fundamentals.get("eps")
    current_price = fundamentals.get("current_price")
    brapi_yield = fundamentals.get("dividend_yield")

    available_fields = []
    missing_fields = []

    # ---- a) Annual dividends ----
    annual_dividends = aggregate_annual_dividends(dividends_data)

    if annual_dividends:
        available_fields.append("dividend_history")
    else:
        missing_fields.append("dividend_history")

    # ---- b) Current DPS (most recent full year) ----
    current_dps = None
    if annual_dividends:
        most_recent_year = max(annual_dividends.keys())
        current_dps = annual_dividends[most_recent_year]

    # ---- c) Yield ----
    current_yield = None
    if current_dps is not None and current_price and current_price > 0:
        current_yield = round(current_dps / current_price, 4)
        available_fields.append("current_yield")
    elif brapi_yield is not None:
        current_yield = round(brapi_yield, 4)
        available_fields.append("current_yield")
    else:
        missing_fields.append("current_yield")

    # ---- d) Payout ratio ----
    payout_ratio = None
    if current_dps is not None and eps is not None and eps > 0:
        payout_ratio = round(current_dps / eps, 4)
        available_fields.append("payout_ratio")
    else:
        missing_fields.append("payout_ratio")

    # ---- e) Coverage ratio ----
    coverage_ratio = None
    if eps is not None and current_dps is not None and current_dps > 0:
        coverage_ratio = round(eps / current_dps, 4)
        available_fields.append("coverage_ratio")
    else:
        missing_fields.append("coverage_ratio")

    # ---- f) Consistency score (last 5 years) ----
    current_year = datetime.now().year
    last_5_years = list(range(current_year, current_year - 5, -1))
    paid_years = sum(1 for y in last_5_years if y in annual_dividends)
    total_years = len(last_5_years)
    consistency = {
        "paid_years": paid_years,
        "total_years": total_years,
        "score": round(paid_years / total_years, 2),
    }
    available_fields.append("consistency")

    # ---- g) Sustainability ----
    sustainability = assess_dividend_sustainability(
        payout_ratio, coverage_ratio, annual_dividends
    )
    available_fields.append("sustainability")

    # ---- h) Dividend history per year ----
    dividend_history = []
    for year, dps in sorted(annual_dividends.items(), reverse=True):
        entry: dict = {"year": year, "dps": dps}
        # Approximate yield using current price (rough proxy)
        if current_price and current_price > 0:
            entry["yield"] = round(dps / current_price, 4)
        else:
            entry["yield"] = None
        dividend_history.append(entry)

    # ---- Data completeness ----
    total_fields = len(available_fields) + len(missing_fields)
    completeness = f"{len(available_fields) * 100 // max(total_fields, 1)}%"

    return {
        "current_yield": current_yield,
        "payout_ratio": payout_ratio,
        "coverage_ratio": coverage_ratio,
        "consistency": consistency,
        "sustainability": sustainability,
        "dividend_history": dividend_history,
        "data_completeness": {
            "available": available_fields,
            "missing": missing_fields,
            "completeness": completeness,
        },
    }
