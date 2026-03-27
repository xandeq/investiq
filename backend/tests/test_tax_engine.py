"""Unit tests for TaxEngine service class (TDD).

TaxEngine is initialized with a list of config rows — no DB connection needed.
Tests construct mock rows matching the TaxConfig column structure.

Coverage:
  - IR regressivo: 4 tiers with representative + boundary holding_days values
  - Exempt asset classes: LCI, LCA, FII (is_exempt=True, rate=0.00)
  - Non-exempt check: renda_fixa is NOT exempt
  - net_return: correct IR deduction for renda_fixa, passthrough for exempt
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import pytest

from app.modules.market_universe.tax_engine import TaxEngine


# ---------------------------------------------------------------------------
# Mock TaxConfig rows — matches TaxConfig model column structure
# ---------------------------------------------------------------------------

@dataclass
class MockTaxConfig:
    id: str
    asset_class: str
    holding_days_min: int
    holding_days_max: Optional[int]
    rate_percent: Decimal
    is_exempt: bool
    label: str


def _make_tax_configs() -> list[MockTaxConfig]:
    """Return 7 mock rows matching the seed data in migration 0015."""
    return [
        MockTaxConfig("tc-rf-1", "renda_fixa", 0,   180,  Decimal("22.50"), False, "IR Regressivo <=180 dias"),
        MockTaxConfig("tc-rf-2", "renda_fixa", 181, 360,  Decimal("20.00"), False, "IR Regressivo 181-360 dias"),
        MockTaxConfig("tc-rf-3", "renda_fixa", 361, 720,  Decimal("17.50"), False, "IR Regressivo 361-720 dias"),
        MockTaxConfig("tc-rf-4", "renda_fixa", 721, None, Decimal("15.00"), False, "IR Regressivo >720 dias"),
        MockTaxConfig("tc-lci-1", "LCI",       0,   None, Decimal("0.00"),  True,  "LCI PF - Isento de IR"),
        MockTaxConfig("tc-lca-1", "LCA",       0,   None, Decimal("0.00"),  True,  "LCA PF - Isento de IR"),
        MockTaxConfig("tc-fii-1", "FII",       0,   None, Decimal("0.00"),  True,  "FII Dividendo - Isento de IR"),
    ]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def engine() -> TaxEngine:
    return TaxEngine(_make_tax_configs())


# ---------------------------------------------------------------------------
# Tests — IR regressivo tiers
# ---------------------------------------------------------------------------

def test_ir_regressivo_tiers(engine):
    """All 4 IR tiers return correct rate for representative holding_days."""
    assert engine.get_rate("renda_fixa", 90)  == Decimal("22.50")   # tier 1: 0-180
    assert engine.get_rate("renda_fixa", 200) == Decimal("20.00")   # tier 2: 181-360
    assert engine.get_rate("renda_fixa", 400) == Decimal("17.50")   # tier 3: 361-720
    assert engine.get_rate("renda_fixa", 800) == Decimal("15.00")   # tier 4: >720


def test_ir_boundary_180_181(engine):
    """Boundary: day 180 stays in tier 1 (<=180), day 181 enters tier 2."""
    assert engine.get_rate("renda_fixa", 180) == Decimal("22.50")   # tier 1 inclusive upper
    assert engine.get_rate("renda_fixa", 181) == Decimal("20.00")   # tier 2 inclusive lower


def test_ir_boundary_360_361(engine):
    """Boundary: day 360 stays in tier 2 (181-360), day 361 enters tier 3."""
    assert engine.get_rate("renda_fixa", 360) == Decimal("20.00")
    assert engine.get_rate("renda_fixa", 361) == Decimal("17.50")


def test_ir_boundary_720_721(engine):
    """Boundary: day 720 stays in tier 3 (361-720), day 721 enters tier 4."""
    assert engine.get_rate("renda_fixa", 720) == Decimal("17.50")
    assert engine.get_rate("renda_fixa", 721) == Decimal("15.00")


def test_ir_very_long_holding(engine):
    """Very long holding period (10 years) still returns lowest tier."""
    assert engine.get_rate("renda_fixa", 3650) == Decimal("15.00")


# ---------------------------------------------------------------------------
# Tests — exempt asset classes
# ---------------------------------------------------------------------------

def test_exemptions(engine):
    """LCI, LCA, FII all return rate 0.00 (exempt)."""
    assert engine.get_rate("LCI", 365) == Decimal("0.00")
    assert engine.get_rate("LCA", 365) == Decimal("0.00")
    assert engine.get_rate("FII", 365) == Decimal("0.00")


def test_is_exempt_lci(engine):
    assert engine.is_exempt("LCI") is True


def test_is_exempt_lca(engine):
    assert engine.is_exempt("LCA") is True


def test_is_exempt_fii(engine):
    assert engine.is_exempt("FII") is True


def test_renda_fixa_not_exempt(engine):
    """renda_fixa is NOT exempt — IR regressivo applies."""
    assert engine.is_exempt("renda_fixa") is False


# ---------------------------------------------------------------------------
# Tests — net_return
# ---------------------------------------------------------------------------

def test_net_return_with_ir(engine):
    """net_return applies 17.5% IR for 365-day renda_fixa.

    gross=10.0%, rate=17.5% -> net = 10.0 * (1 - 0.175) = 8.25
    """
    result = engine.net_return(Decimal("10.0"), "renda_fixa", 365)
    assert result == Decimal("8.25")


def test_net_return_exempt_lci(engine):
    """LCI is exempt — net_return returns gross unchanged."""
    result = engine.net_return(Decimal("10.0"), "LCI", 365)
    assert result == Decimal("10.0")


def test_net_return_exempt_fii(engine):
    """FII is exempt — net_return returns gross unchanged."""
    result = engine.net_return(Decimal("8.0"), "FII", 180)
    assert result == Decimal("8.0")


def test_net_return_tier1(engine):
    """net_return applies 22.5% IR for 90-day renda_fixa.

    gross=10.0%, rate=22.5% -> net = 10.0 * (1 - 0.225) = 7.75
    """
    result = engine.net_return(Decimal("10.0"), "renda_fixa", 90)
    assert result == Decimal("7.75")


def test_net_return_tier4(engine):
    """net_return applies 15% IR for 800-day renda_fixa.

    gross=10.0%, rate=15% -> net = 10.0 * (1 - 0.15) = 8.5
    """
    result = engine.net_return(Decimal("10.0"), "renda_fixa", 800)
    assert result == Decimal("8.500")


# ---------------------------------------------------------------------------
# Tests — unknown asset class raises
# ---------------------------------------------------------------------------

def test_get_rate_unknown_asset_class_raises(engine):
    """get_rate raises ValueError for unknown asset class."""
    with pytest.raises(ValueError, match="No tax config"):
        engine.get_rate("unknown_class", 100)
