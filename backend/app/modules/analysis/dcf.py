"""2-Stage FCFF DCF calculation with CAPM WACC and sensitivity (Phase 13).

Implements:
- CAPM-based WACC calculation using SELIC as risk-free rate
- 5-year explicit FCF projection + terminal value (Gordon Growth)
- 3-scenario sensitivity analysis (bear/base/bull)
- Growth rate estimation from historical FCF CAGR

Constants calibrated for Brazilian market (B3).
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Brazil Equity Risk Premium (Damodaran 2025 estimate for Brazil)
ERP_BRAZIL = 0.07

# Default debt cost spread over risk-free rate
_DEBT_SPREAD = 0.02

# Projection horizon (years)
_PROJECTION_YEARS = 5


def calculate_wacc(
    selic: float,
    beta: float | None,
    debt: float,
    equity: float,
    tax_rate: float = 0.34,
) -> float:
    """Calculate Weighted Average Cost of Capital using CAPM.

    Args:
        selic: Risk-free rate (SELIC, decimal, e.g. 0.1475)
        beta: Stock beta vs IBOVESPA. None defaults to 1.0 (market avg).
        debt: Total debt (BRL)
        equity: Market cap / equity value (BRL)
        tax_rate: Corporate tax rate (default 34% for Brazil: 15% IR + 10% adicional + 9% CSLL)

    Returns:
        WACC as decimal (e.g. 0.18 for 18%)
    """
    if beta is None:
        beta = 1.0

    # Cost of equity via CAPM: Ke = Rf + beta * ERP
    ke = selic + beta * ERP_BRAZIL

    # Simplified cost of debt: Kd = Rf + spread
    kd = selic + _DEBT_SPREAD

    total_capital = debt + equity
    if total_capital <= 0:
        return ke

    # WACC = Ke * (E/(D+E)) + Kd * (1-T) * (D/(D+E))
    wacc = ke * (equity / total_capital) + kd * (1 - tax_rate) * (debt / total_capital)
    return wacc


def calculate_dcf(
    fcf_current: float,
    shares_outstanding: float,
    growth_rate: float,
    wacc: float,
    terminal_growth: float,
) -> dict:
    """Calculate 2-Stage FCFF DCF valuation.

    Stage 1: 5-year explicit FCF projections at growth_rate
    Stage 2: Terminal value via Gordon Growth Model

    Args:
        fcf_current: Most recent annual Free Cash Flow (BRL)
        shares_outstanding: Total shares outstanding
        growth_rate: Expected FCF growth rate (decimal)
        wacc: Weighted Average Cost of Capital (decimal)
        terminal_growth: Long-term perpetuity growth rate (decimal)

    Returns:
        Dict with fair_value, enterprise_value, projections, etc.

    Raises:
        ValueError: If WACC <= terminal_growth (no convergence)
    """
    if wacc <= terminal_growth:
        raise ValueError(
            f"WACC ({wacc:.4f}) must be greater than terminal growth "
            f"({terminal_growth:.4f}) for DCF convergence"
        )

    if shares_outstanding <= 0:
        raise ValueError("shares_outstanding must be positive")

    # Stage 1: Project FCFs and discount
    projected_fcfs = []
    pv_stage1 = 0.0
    fcf_prev = fcf_current

    for year in range(1, _PROJECTION_YEARS + 1):
        fcf_year = fcf_prev * (1 + growth_rate)
        pv = fcf_year / ((1 + wacc) ** year)
        projected_fcfs.append({
            "year": year,
            "fcf": round(fcf_year, 2),
            "present_value": round(pv, 2),
        })
        pv_stage1 += pv
        fcf_prev = fcf_year

    # Stage 2: Terminal value (Gordon Growth)
    fcf_terminal = fcf_prev * (1 + terminal_growth)
    terminal_value = fcf_terminal / (wacc - terminal_growth)
    pv_terminal = terminal_value / ((1 + wacc) ** _PROJECTION_YEARS)

    # Enterprise value
    enterprise_value = pv_stage1 + pv_terminal

    # Fair value per share
    fair_value = enterprise_value / shares_outstanding

    return {
        "fair_value": round(fair_value, 2),
        "enterprise_value": round(enterprise_value, 2),
        "pv_stage1": round(pv_stage1, 2),
        "pv_terminal": round(pv_terminal, 2),
        "terminal_value": round(terminal_value, 2),
        "projected_fcfs": projected_fcfs,
        "assumptions": {
            "fcf_current": fcf_current,
            "growth_rate": growth_rate,
            "wacc": wacc,
            "terminal_growth": terminal_growth,
            "projection_years": _PROJECTION_YEARS,
        },
    }


def calculate_dcf_with_sensitivity(
    fcf_current: float,
    shares_outstanding: float,
    growth_rate: float,
    wacc: float,
    terminal_growth: float,
    net_debt: float,
) -> dict:
    """DCF with 3-scenario sensitivity analysis.

    Scenarios:
    - Bear (low): growth -2pp, WACC +2pp
    - Base: as provided
    - Bull (high): growth +2pp, WACC -2pp (floored at terminal_growth + 1pp)

    Net debt is subtracted from enterprise value to get equity value.

    Args:
        fcf_current: Most recent annual FCF (BRL)
        shares_outstanding: Total shares outstanding
        growth_rate: Base case FCF growth rate
        wacc: Base case WACC
        terminal_growth: Terminal growth rate
        net_debt: Total debt minus total cash (BRL)

    Returns:
        Dict with fair_value (base), fair_value_range, upside_pct,
        scenarios, key_drivers, projected_fcfs.
    """
    scenarios = {}

    # Define scenario parameters
    scenario_params = {
        "low": {
            "growth": max(growth_rate - 0.02, 0.0),
            "wacc": wacc + 0.02,
            "label": "Bear (pessimista)",
        },
        "base": {
            "growth": growth_rate,
            "wacc": wacc,
            "label": "Base",
        },
        "high": {
            "growth": growth_rate + 0.02,
            "wacc": max(wacc - 0.02, terminal_growth + 0.01),
            "label": "Bull (otimista)",
        },
    }

    for key, params in scenario_params.items():
        try:
            dcf_result = calculate_dcf(
                fcf_current=fcf_current,
                shares_outstanding=shares_outstanding,
                growth_rate=params["growth"],
                wacc=params["wacc"],
                terminal_growth=terminal_growth,
            )
            # Equity value = EV - net_debt
            equity_value = dcf_result["enterprise_value"] - net_debt
            scenario_fair_value = equity_value / shares_outstanding if shares_outstanding > 0 else 0

            scenarios[key] = {
                "label": params["label"],
                "fair_value": round(scenario_fair_value, 2),
                "enterprise_value": dcf_result["enterprise_value"],
                "equity_value": round(equity_value, 2),
                "growth_rate": params["growth"],
                "wacc": params["wacc"],
            }
        except ValueError as exc:
            logger.warning("Scenario %s failed: %s", key, exc)
            scenarios[key] = {
                "label": params["label"],
                "fair_value": None,
                "error": str(exc),
            }

    # Base case result
    base = scenarios.get("base", {})
    base_fair_value = base.get("fair_value", 0) or 0

    # Fair value range
    low_fv = scenarios.get("low", {}).get("fair_value")
    high_fv = scenarios.get("high", {}).get("fair_value")

    # Base projected FCFs
    try:
        base_dcf = calculate_dcf(
            fcf_current, shares_outstanding, growth_rate, wacc, terminal_growth
        )
        projected_fcfs = base_dcf["projected_fcfs"]
    except ValueError:
        projected_fcfs = []

    # Key drivers analysis
    key_drivers = _identify_key_drivers(scenarios, growth_rate, wacc)

    return {
        "fair_value": base_fair_value,
        "fair_value_range": {
            "low": low_fv,
            "high": high_fv,
        },
        "upside_pct": None,  # Caller sets this using current_price
        "scenarios": scenarios,
        "key_drivers": key_drivers,
        "projected_fcfs": projected_fcfs,
    }


def _identify_key_drivers(
    scenarios: dict,
    growth_rate: float,
    wacc: float,
) -> list[str]:
    """Identify which assumptions drive fair value most."""
    drivers = []

    low_fv = scenarios.get("low", {}).get("fair_value")
    base_fv = scenarios.get("base", {}).get("fair_value")
    high_fv = scenarios.get("high", {}).get("fair_value")

    if low_fv is not None and high_fv is not None and base_fv and base_fv > 0:
        spread = high_fv - low_fv
        spread_pct = (spread / base_fv) * 100
        drivers.append(
            f"Sensitivity spread: R${spread:.2f} ({spread_pct:.0f}% of base fair value)"
        )

    if base_fv and base_fv > 0:
        if high_fv is not None:
            upside_from_growth = ((high_fv - base_fv) / base_fv) * 100
            drivers.append(
                f"Growth +2pp / WACC -2pp moves fair value +{upside_from_growth:.0f}%"
            )
        if low_fv is not None:
            downside_from_risk = ((base_fv - low_fv) / base_fv) * 100
            drivers.append(
                f"Growth -2pp / WACC +2pp moves fair value -{downside_from_risk:.0f}%"
            )

    if not drivers:
        drivers.append("Insufficient data for sensitivity analysis")

    return drivers


def estimate_growth_rate(
    cashflow_history: list[dict],
    default: float = 0.05,
) -> float:
    """Estimate FCF growth rate from historical cashflow CAGR.

    Uses last 5 years of FCF data. Falls back to default if:
    - Less than 3 data points
    - Negative FCF values
    - CAGR outside 0-30% range

    Args:
        cashflow_history: List of dicts with "free_cash_flow" key
        default: Fallback growth rate

    Returns:
        Estimated growth rate as decimal (e.g. 0.08 for 8%)
    """
    if not cashflow_history or len(cashflow_history) < 3:
        logger.info("Insufficient cashflow history (%d points), using default growth %.2f",
                     len(cashflow_history) if cashflow_history else 0, default)
        return default

    # Extract FCF values (most recent first in BRAPI)
    fcf_values = []
    for cf in cashflow_history[:5]:
        fcf = cf.get("free_cash_flow")
        if fcf is not None and isinstance(fcf, (int, float)):
            fcf_values.append(fcf)

    if len(fcf_values) < 3:
        return default

    # Need oldest and newest for CAGR
    # BRAPI returns most recent first, so reverse for chronological order
    fcf_values = list(reversed(fcf_values))

    oldest = fcf_values[0]
    newest = fcf_values[-1]

    # Both must be positive for meaningful CAGR
    if oldest <= 0 or newest <= 0:
        logger.info("Negative FCF detected, using default growth %.2f", default)
        return default

    n_years = len(fcf_values) - 1
    if n_years <= 0:
        return default

    # CAGR = (newest / oldest)^(1/n) - 1
    try:
        cagr = (newest / oldest) ** (1 / n_years) - 1
    except (ZeroDivisionError, OverflowError):
        return default

    # Clamp to reasonable range
    if cagr < 0 or cagr > 0.30:
        logger.info("CAGR %.2f outside 0-30%% range, using default %.2f", cagr, default)
        return default

    logger.info("Estimated growth rate from %d years FCF CAGR: %.4f", n_years, cagr)
    return round(cagr, 4)
