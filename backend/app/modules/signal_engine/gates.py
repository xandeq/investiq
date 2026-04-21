"""Signal Engine — Gate evaluator for A+ swing trade setups.

Gates are evaluated sequentially (fast-fail). The first gate that fails
stops evaluation and sets grade = FAIL (or partial grade for partial passes).

Gate list (10 gates):
1.  has_setup           — chart_analyzer returned has_setup=True
2.  score_tecnico       — setup grade in ('A+', 'A') → score >= 85
3.  confluencias        — len(confluences) >= 5
4.  rr                  — setup.rr >= 3.0
5.  multi_tf_alinhado   — 'multi_tf_aligned' in confluences
6.  volume_ratio        — indicators.volume_ratio >= 1.5
7.  regime_trending     — indicators.regime in ('trending_up', 'trending_down')
8.  sem_earnings        — earnings_days is None OR earnings_days > 5
9.  sem_ex_div          — ex_div_days is None OR ex_div_days > 3
10. liquidez_ok         — ticker is in RADAR_ACOES (proxy for ADV > R$50M)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Liquid B3 large + mid caps (ADV > R$20M) — full IBOV + selected small caps.
# Expanded for BRAPI Pro which allows scanning the full universe without 429s.
RADAR_ACOES: frozenset[str] = frozenset({
    # IBOV core (top 76 by liquidity)
    "PETR4", "VALE3", "ITUB4", "BBDC4", "ABEV3", "WEGE3", "BBSE3", "BBAS3",
    "EGIE3", "TOTS3", "HAPV3", "BEEF3", "RDOR3", "SBSP3", "PRIO3", "RENT3",
    "EMBR3", "SUZB3", "LREN3", "B3SA3", "BOVA11", "RADL3", "ELET3", "ENEV3",
    "SANB11", "CSAN3", "UGPA3", "JBSS3", "MRVE3", "CYRE3", "EZTC3", "DIRR3",
    "TAEE11", "CMIG4", "CPFE3", "ENBR3", "TIMS3", "VIVT3", "TASA4", "ALPA4",
    "MULT3", "IGTA3", "BEEF3", "SMTO3", "SLCE3", "AGRO3", "TTEN3", "SOJA3",
    "KLBN11", "DXCO3", "IRBR3", "CIEL3", "GETL3", "PETZ3", "RECV3", "BPAN4",
    "AURE3", "VBBR3", "RAIZ4", "CBAV3", "INTB3", "LOGG3", "GMAT3", "LWSA3",
    "TOTS3",  "MOVI3", "FLRY3", "ODPV3", "QUAL3", "ONCO3", "HAPV3", "AMER3",
    "MGLU3", "VIVA3", "ANIM3", "COGN3", "YDUQ3",
    # ETFs reference
    "BOVA11", "SMAL11", "IVVB11",
})

_GRADE_SCORE_MAP: dict[str, float] = {
    "A+": 100.0,
    "A": 90.0,
    "B": 70.0,
    "C": 50.0,
}

_TRENDING_REGIMES: frozenset[str] = frozenset({"trending_up", "trending_down"})


@dataclass
class GateResult:
    gate_name: str
    passed: bool
    value: float | str | None
    threshold: float | str | None
    reason: str


@dataclass
class SignalEvaluation:
    ticker: str
    grade: str          # "A+" | "A" | "B" | "C" | "FAIL"
    score: float        # 0–100
    passed_gates: int
    total_gates: int
    gates: list[GateResult] = field(default_factory=list)
    is_a_plus: bool = False
    setup: dict | None = None


def _grade_from_passed(passed: int, total: int) -> str:
    if passed == total:
        return "A+"
    if passed >= total - 2:   # 8-9 of 10
        return "A"
    if passed >= total - 4:   # 6-7 of 10
        return "B"
    return "C"


def evaluate_signal(
    ticker: str,
    analysis: dict,
    macro: dict | None = None,
    earnings_days: int | None = None,
    ex_div_days: int | None = None,
) -> SignalEvaluation:
    """Evaluate 10 sequential A+ gates for a given ticker analysis.

    Args:
        ticker:        B3 ticker (e.g. "BBSE3").
        analysis:      Output dict from chart_analyzer.analyze().
        macro:         Optional macro context dict (CDI/SELIC/IPCA from Redis).
                       Not used by current gates but reserved for future gates.
        earnings_days: Days until next earnings release. None = unknown (treated as safe).
        ex_div_days:   Days until ex-dividend date. None = unknown (treated as safe).

    Returns:
        SignalEvaluation with full gate trace, grade, and score.
    """
    total_gates = 10
    gates: list[GateResult] = []
    setup = analysis.get("setup")
    indicators = analysis.get("indicators", {})
    confluences = analysis.get("confluences", [])

    def _fail(name: str, value, threshold, reason: str) -> SignalEvaluation:
        gates.append(GateResult(name, False, value, threshold, reason))
        passed = len([g for g in gates if g.passed])
        grade = _grade_from_passed(passed, total_gates) if passed > 0 else "FAIL"
        score = (passed / total_gates) * 100
        return SignalEvaluation(
            ticker=ticker,
            grade=grade,
            score=round(score, 1),
            passed_gates=passed,
            total_gates=total_gates,
            gates=gates,
            is_a_plus=False,
            setup=setup,
        )

    def _pass(name: str, value, threshold, reason: str) -> None:
        gates.append(GateResult(name, True, value, threshold, reason))

    # Gate 1 — has_setup
    has_setup = analysis.get("has_setup", False)
    if not has_setup:
        return _fail("has_setup", has_setup, True, "chart_analyzer retornou has_setup=False")
    _pass("has_setup", has_setup, True, "Setup detectado pelo chart_analyzer")

    # Gate 2 — score_tecnico >= 85 (grade A+ ou A)
    setup_grade = (setup or {}).get("grade", "C")
    setup_score = _GRADE_SCORE_MAP.get(setup_grade, 0.0)
    if setup_score < 85.0:
        return _fail(
            "score_tecnico", setup_grade, "A ou A+",
            f"Grade do setup é '{setup_grade}' (score={setup_score}) — requer A ou A+"
        )
    _pass("score_tecnico", setup_grade, "A ou A+", f"Grade {setup_grade} aprovado (score={setup_score})")

    # Gate 3 — confluencias >= 5
    n_conf = len(confluences)
    if n_conf < 5:
        return _fail(
            "confluencias", n_conf, 5,
            f"Apenas {n_conf} confluência(s) — mínimo de 5 exigido"
        )
    _pass("confluencias", n_conf, 5, f"{n_conf} confluências detectadas")

    # Gate 4 — rr >= 3.0
    rr = float((setup or {}).get("rr", 0.0))
    if rr < 3.0:
        return _fail("rr", rr, 3.0, f"R/R de {rr:.2f} abaixo do mínimo de 3.0")
    _pass("rr", rr, 3.0, f"R/R de {rr:.2f} aprovado")

    # Gate 5 — multi_tf_alinhado: 'multi_tf_aligned' in confluences
    multi_tf = "multi_tf_aligned" in confluences
    if not multi_tf:
        return _fail(
            "multi_tf_alinhado", False, True,
            "'multi_tf_aligned' ausente nas confluências"
        )
    _pass("multi_tf_alinhado", True, True, "multi_tf_aligned presente nas confluências")

    # Gate 6 — volume_ratio >= 1.5
    vol_ratio = float(indicators.get("volume_ratio", 0.0))
    if vol_ratio < 1.5:
        return _fail(
            "volume_ratio", vol_ratio, 1.5,
            f"Volume ratio {vol_ratio:.2f}x abaixo do mínimo de 1.5x"
        )
    _pass("volume_ratio", vol_ratio, 1.5, f"Volume ratio {vol_ratio:.2f}x aprovado")

    # Gate 7 — regime trending
    regime = indicators.get("regime", "")
    if regime not in _TRENDING_REGIMES:
        return _fail(
            "regime_trending", regime, "trending_up | trending_down",
            f"Regime '{regime}' não é tendência clara"
        )
    _pass("regime_trending", regime, "trending_up | trending_down", f"Regime '{regime}' aprovado")

    # Gate 8 — sem_earnings: None (desconhecido = seguro) OR > 5 dias
    if earnings_days is not None and earnings_days <= 5:
        return _fail(
            "sem_earnings", earnings_days, ">5 dias",
            f"Earnings em {earnings_days} dia(s) — risco de gap"
        )
    _pass(
        "sem_earnings",
        earnings_days if earnings_days is not None else "desconhecido",
        ">5 dias",
        "Sem earnings próximos (seguro)"
    )

    # Gate 9 — sem_ex_div: None (desconhecido = seguro) OR > 3 dias
    if ex_div_days is not None and ex_div_days <= 3:
        return _fail(
            "sem_ex_div", ex_div_days, ">3 dias",
            f"Ex-dividendo em {ex_div_days} dia(s) — risco de ajuste de preço"
        )
    _pass(
        "sem_ex_div",
        ex_div_days if ex_div_days is not None else "desconhecido",
        ">3 dias",
        "Sem ex-dividendo próximo (seguro)"
    )

    # Gate 10 — liquidez_ok: ticker in RADAR_ACOES
    ticker_upper = ticker.upper()
    if ticker_upper not in RADAR_ACOES:
        return _fail(
            "liquidez_ok", ticker_upper, "RADAR_ACOES",
            f"Ticker {ticker_upper} fora do radar de liquidez (ADV > R$50M)"
        )
    _pass("liquidez_ok", ticker_upper, "RADAR_ACOES", f"{ticker_upper} aprovado no critério de liquidez")

    # All 10 gates passed → A+
    passed = len([g for g in gates if g.passed])
    return SignalEvaluation(
        ticker=ticker,
        grade="A+",
        score=100.0,
        passed_gates=passed,
        total_gates=total_gates,
        gates=gates,
        is_a_plus=True,
        setup=setup,
    )
