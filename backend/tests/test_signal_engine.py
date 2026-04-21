"""Tests for signal_engine.gates — gate evaluation logic.

All tests use mocked analysis dicts — no HTTP calls are made.
"""
from __future__ import annotations

import pytest

from app.modules.signal_engine.gates import evaluate_signal, RADAR_ACOES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_analysis(
    has_setup: bool = True,
    grade: str = "A+",
    rr: float = 3.5,
    confluences: list[str] | None = None,
    volume_ratio: float = 2.0,
    regime: str = "trending_up",
) -> dict:
    """Build a minimal analysis dict that mirrors chart_analyzer.analyze() output."""
    if confluences is None:
        # 5 confluences including multi_tf_aligned
        confluences = [
            "multi_tf_aligned",
            "RSI neutro (zona de valor)",
            "Acima da EMA200 (tendência de alta)",
            "EMA20 > EMA50 (momentum altista)",
            "MACD acima do sinal",
        ]
    setup = (
        {
            "pattern": "Bullish Engulfing",
            "direction": "long",
            "entry": 30.00,
            "stop": 27.00,
            "target_1": 39.00,
            "target_2": 42.00,
            "rr": rr,
            "grade": grade,
        }
        if has_setup
        else None
    )
    return {
        "ticker": "BBSE3",
        "has_setup": has_setup,
        "setup": setup,
        "indicators": {
            "rsi_14": 50.0,
            "volume_ratio": volume_ratio,
            "regime": regime,
            "ema20": 30.5,
            "ema50": 29.0,
            "ema200": 25.0,
            "atr": 0.8,
            "macd": 0.1,
            "macd_signal": 0.05,
        },
        "confluences": confluences,
        "levels": {"support": [], "resistance": []},
        "error": None,
    }


# ---------------------------------------------------------------------------
# Gate 1 — has_setup
# ---------------------------------------------------------------------------

def test_evaluate_signal_no_setup_fails_gate1():
    """If has_setup=False, gate 1 fails → grade FAIL, is_a_plus=False."""
    analysis = _make_analysis(has_setup=False)
    result = evaluate_signal("BBSE3", analysis)

    assert result.is_a_plus is False
    assert result.grade == "FAIL"
    assert result.passed_gates == 0
    assert len(result.gates) == 1
    assert result.gates[0].gate_name == "has_setup"
    assert result.gates[0].passed is False


# ---------------------------------------------------------------------------
# Gate 3 — confluencias
# ---------------------------------------------------------------------------

def test_evaluate_signal_missing_confluences_fails():
    """With < 5 confluências, signal must not be A+.

    Note: gate 5 (multi_tf_alinhado) fires before gate 3 can be tested in
    isolation when we remove multi_tf_aligned. To isolate gate 3 we provide
    exactly 4 confluences that include multi_tf_aligned — gate 3 fires first.
    """
    analysis = _make_analysis(
        confluences=[
            "multi_tf_aligned",
            "RSI neutro (zona de valor)",
            "MACD acima do sinal",
            "Acima da EMA200 (tendência de alta)",
        ]  # only 4 — gate 3 fires
    )
    result = evaluate_signal("BBSE3", analysis)

    assert result.is_a_plus is False
    # Gate 3 should be the failing gate
    failed = [g for g in result.gates if not g.passed]
    assert failed, "Expected at least one failed gate"
    assert failed[0].gate_name == "confluencias"


# ---------------------------------------------------------------------------
# Gate 4 — rr
# ---------------------------------------------------------------------------

def test_evaluate_signal_low_rr_fails():
    """With RR < 3.0, signal must not be A+."""
    analysis = _make_analysis(rr=2.5)
    result = evaluate_signal("BBSE3", analysis)

    assert result.is_a_plus is False
    failed = [g for g in result.gates if not g.passed]
    assert failed[0].gate_name == "rr"


# ---------------------------------------------------------------------------
# All 10 gates pass → A+
# ---------------------------------------------------------------------------

def test_evaluate_signal_a_plus_all_gates():
    """With a perfect mock analysis, all 10 gates should pass → grade A+."""
    analysis = _make_analysis()
    # BBSE3 is in RADAR_ACOES
    assert "BBSE3" in RADAR_ACOES

    result = evaluate_signal("BBSE3", analysis)

    assert result.is_a_plus is True
    assert result.grade == "A+"
    assert result.passed_gates == 10
    assert result.total_gates == 10
    assert result.score == 100.0
    assert all(g.passed for g in result.gates)


# ---------------------------------------------------------------------------
# Score proportionality
# ---------------------------------------------------------------------------

def test_signal_evaluation_score_proportional():
    """Score must be proportional to the number of gates passed."""
    # Gate 1 fails immediately → 0 passed out of 10 → score = 0.0
    analysis_no_setup = _make_analysis(has_setup=False)
    result_zero = evaluate_signal("BBSE3", analysis_no_setup)
    assert result_zero.score == 0.0
    assert result_zero.passed_gates == 0

    # All 10 gates pass → score = 100.0
    analysis_perfect = _make_analysis()
    result_perfect = evaluate_signal("BBSE3", analysis_perfect)
    assert result_perfect.score == 100.0

    # Verify formula: score = (passed_gates / total_gates) * 100
    for result in [result_zero, result_perfect]:
        expected_score = (result.passed_gates / result.total_gates) * 100
        assert abs(result.score - expected_score) < 0.01


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_evaluate_signal_unknown_ticker_fails_gate10():
    """A ticker not in RADAR_ACOES should fail gate 10 (liquidez_ok)."""
    analysis = _make_analysis()
    result = evaluate_signal("XYZW11", analysis)

    assert result.is_a_plus is False
    failed = [g for g in result.gates if not g.passed]
    assert failed[0].gate_name == "liquidez_ok"


def test_evaluate_signal_earnings_in_3_days_fails_gate8():
    """earnings_days <= 5 should fail gate 8 (sem_earnings)."""
    analysis = _make_analysis()
    result = evaluate_signal("BBSE3", analysis, earnings_days=3)

    assert result.is_a_plus is False
    failed = [g for g in result.gates if not g.passed]
    assert failed[0].gate_name == "sem_earnings"


def test_evaluate_signal_exdiv_tomorrow_fails_gate9():
    """ex_div_days <= 3 should fail gate 9 (sem_ex_div)."""
    analysis = _make_analysis()
    result = evaluate_signal("BBSE3", analysis, ex_div_days=1)

    assert result.is_a_plus is False
    failed = [g for g in result.gates if not g.passed]
    assert failed[0].gate_name == "sem_ex_div"


def test_evaluate_signal_sideways_regime_fails_gate7():
    """A 'sideways' regime should fail gate 7 (regime_trending)."""
    analysis = _make_analysis(regime="sideways")
    result = evaluate_signal("BBSE3", analysis)

    assert result.is_a_plus is False
    failed = [g for g in result.gates if not g.passed]
    assert failed[0].gate_name == "regime_trending"


def test_evaluate_signal_low_volume_fails_gate6():
    """volume_ratio < 1.5 should fail gate 6."""
    analysis = _make_analysis(volume_ratio=1.1)
    result = evaluate_signal("BBSE3", analysis)

    assert result.is_a_plus is False
    failed = [g for g in result.gates if not g.passed]
    assert failed[0].gate_name == "volume_ratio"
