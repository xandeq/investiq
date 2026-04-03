"""Earnings analysis calculations (Phase 13 Plan 02 — AI-02).

Computes:
- EPS history (up to 5 years) with YoY growth
- EPS CAGR over available history
- Accrual ratio: (net_income - operating_cash_flow) / (total_debt + total_cash)
- FCF conversion: free_cash_flow / net_income
- Earnings quality flag: high / medium / low

Data source: fundamentals dict from data.py (BRAPI).
"""
from __future__ import annotations

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def _parse_year(end_date: str | None) -> str | None:
    """Extract year from an end_date string (e.g. '2025-12-31' or ISO)."""
    if not end_date:
        return None
    try:
        # Handle ISO format or date string
        dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
        return str(dt.year)
    except (ValueError, AttributeError):
        # Try just first 4 chars
        if len(str(end_date)) >= 4:
            return str(end_date)[:4]
        return None


def _rate(label: str, value: float | None, thresholds: dict) -> str:
    """Rate a metric as good/moderate/poor based on thresholds."""
    if value is None:
        return "insufficient_data"
    if label == "accrual":
        if value < thresholds["good"]:
            return "good"
        elif value <= thresholds["moderate"]:
            return "moderate"
        return "poor"
    else:  # fcf
        if value > thresholds["good"]:
            return "good"
        elif value >= thresholds["moderate"]:
            return "moderate"
        return "poor"


def assess_earnings_quality(
    accrual_ratio: float | None, fcf_conversion: float | None
) -> str:
    """Assess overall earnings quality.

    - high: accrual < 0.20 AND fcf_conversion > 0.80
    - low: accrual > 0.40 OR fcf_conversion < 0.50
    - medium: everything else (including insufficient data)
    """
    if accrual_ratio is not None and fcf_conversion is not None:
        if accrual_ratio < 0.20 and fcf_conversion > 0.80:
            return "high"
        if accrual_ratio > 0.40 or fcf_conversion < 0.50:
            return "low"
    elif accrual_ratio is not None:
        if accrual_ratio > 0.40:
            return "low"
    elif fcf_conversion is not None:
        if fcf_conversion < 0.50:
            return "low"

    return "medium"


def calculate_earnings_analysis(fundamentals: dict) -> dict:
    """Calculate earnings analysis from BRAPI fundamentals.

    Args:
        fundamentals: Dict from fetch_fundamentals() with income_history,
                      cashflow_history, shares_outstanding, etc.

    Returns:
        Dict with eps_history, eps_cagr_5y, quality_metrics, data_completeness.
    """
    income_history = fundamentals.get("income_history", [])
    cashflow_history = fundamentals.get("cashflow_history", [])
    shares_outstanding = fundamentals.get("shares_outstanding")

    available_fields = []
    missing_fields = []

    # ---- a) EPS history (up to 5 years) with YoY growth ----
    eps_history = []
    if income_history and shares_outstanding and shares_outstanding > 0:
        available_fields.append("eps_history")
        for stmt in income_history[:5]:
            net_income = stmt.get("net_income")
            revenue = stmt.get("total_revenue")
            year = _parse_year(stmt.get("end_date"))

            if net_income is not None:
                eps = net_income / shares_outstanding
                eps_history.append({
                    "year": year,
                    "eps": round(eps, 4),
                    "revenue": revenue,
                    "yoy_growth": None,  # filled below
                })
            else:
                eps_history.append({
                    "year": year,
                    "eps": None,
                    "revenue": revenue,
                    "yoy_growth": None,
                })
    else:
        if not income_history:
            missing_fields.append("income_history")
        if not shares_outstanding:
            missing_fields.append("shares_outstanding")

    # Calculate YoY growth (income_history is most recent first)
    for i in range(len(eps_history) - 1):
        current_eps = eps_history[i].get("eps")
        previous_eps = eps_history[i + 1].get("eps")
        if current_eps is not None and previous_eps is not None and abs(previous_eps) > 0:
            eps_history[i]["yoy_growth"] = round(
                (current_eps - previous_eps) / abs(previous_eps), 4
            )

    # ---- EPS CAGR ----
    eps_cagr_5y = None
    eps_values = [e["eps"] for e in eps_history if e.get("eps") is not None]
    if len(eps_values) >= 2:
        # Most recent first in history; newest = index 0, oldest = last
        newest = eps_values[0]
        oldest = eps_values[-1]
        n_years = len(eps_values) - 1
        if oldest > 0 and newest > 0 and n_years > 0:
            try:
                eps_cagr_5y = round((newest / oldest) ** (1 / n_years) - 1, 4)
                available_fields.append("eps_cagr_5y")
            except (ZeroDivisionError, OverflowError):
                missing_fields.append("eps_cagr_5y")
        else:
            missing_fields.append("eps_cagr_5y")
    else:
        missing_fields.append("eps_cagr_5y")

    # ---- b) Accrual ratio ----
    accrual_ratio = None
    accrual_rating = "insufficient_data"
    total_debt = fundamentals.get("total_debt", 0) or 0
    total_cash = fundamentals.get("total_cash", 0) or 0
    denominator = total_debt + total_cash

    if income_history and cashflow_history and denominator > 0:
        net_income_recent = income_history[0].get("net_income")
        ocf_recent = cashflow_history[0].get("operating_cash_flow")

        if net_income_recent is not None and ocf_recent is not None:
            accrual_ratio = round(
                (net_income_recent - ocf_recent) / denominator, 4
            )
            accrual_rating = _rate(
                "accrual", accrual_ratio,
                {"good": 0.20, "moderate": 0.40},
            )
            available_fields.append("accrual_ratio")
        else:
            missing_fields.append("accrual_ratio")
    else:
        missing_fields.append("accrual_ratio")
        if denominator == 0:
            missing_fields.append("total_assets_proxy")

    # ---- c) FCF conversion ----
    fcf_conversion = None
    fcf_rating = "insufficient_data"

    if income_history and cashflow_history:
        net_income_recent = income_history[0].get("net_income")
        fcf_recent = cashflow_history[0].get("free_cash_flow")

        if (
            net_income_recent is not None
            and fcf_recent is not None
            and net_income_recent > 0
        ):
            fcf_conversion = round(fcf_recent / net_income_recent, 4)
            fcf_rating = _rate(
                "fcf", fcf_conversion,
                {"good": 0.80, "moderate": 0.50},
            )
            available_fields.append("fcf_conversion")
        else:
            missing_fields.append("fcf_conversion")
    else:
        missing_fields.append("fcf_conversion")

    # ---- d) Earnings quality flag ----
    earnings_quality = assess_earnings_quality(accrual_ratio, fcf_conversion)

    # ---- Data completeness ----
    total_fields = len(available_fields) + len(missing_fields)
    completeness = f"{len(available_fields) * 100 // max(total_fields, 1)}%"

    return {
        "eps_history": eps_history,
        "eps_cagr_5y": eps_cagr_5y,
        "quality_metrics": {
            "accrual_ratio": accrual_ratio,
            "accrual_rating": accrual_rating,
            "fcf_conversion": fcf_conversion,
            "fcf_rating": fcf_rating,
            "earnings_quality": earnings_quality,
        },
        "data_completeness": {
            "available": available_fields,
            "missing": missing_fields,
            "completeness": completeness,
            "note": "accrual_ratio uses (total_debt + total_cash) as proxy for total assets"
            if accrual_ratio is not None
            else None,
        },
    }
