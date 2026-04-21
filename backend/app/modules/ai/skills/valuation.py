"""Relative Valuation skill adapter.

Compares an asset's P/L and P/VP against typical Brazilian market sector norms
to assess relative over/undervaluation.
"""
from __future__ import annotations

import logging

from app.modules.ai.provider import call_llm
from app.modules.ai.skills import DISCLAIMER_TEXT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Você é um analista de valuation especializado em ações e FIIs brasileiros. "
    "Use análise de múltiplos comparativos (peer comparison). "
    "Responda em português, máximo 3 parágrafos, foco técnico e objetivo. "
    "NUNCA faça recomendação explícita de compra ou venda."
)


def _fmt(val, suffix: str = "", pct: bool = False, decimals: int = 1) -> str:
    """Format a value for display; handles None, ratio-vs-percentage ambiguity."""
    if val is None:
        return "N/D"
    try:
        v = float(val)
        if pct and abs(v) < 1:   # stored as ratio (0.08 → 8.0%)
            v = v * 100
        return f"{v:.{decimals}f}{suffix}"
    except (TypeError, ValueError):
        return str(val)


async def run_valuation(ticker: str, fundamentals: dict, tier: str = "free") -> dict:
    """Run relative valuation analysis for a B3 asset.

    Args:
        ticker: B3 ticker symbol.
        fundamentals: Dict from Redis market:fundamentals:{ticker} (Celery-populated).
                      Accepted keys: pl, pvp, dy, ev_ebitda, market_cap, setor,
                      industria, roe, roa, margem_bruta, margem_operacional,
                      margem_liquida, divida_sobre_ebitda, beta, eps.
                      Legacy keys (pe_ratio, pb_ratio, dividend_yield, sector)
                      are also accepted for backwards compatibility.

    Returns:
        Dict with keys: ticker, analysis, methodology, disclaimer, multiples.
    """
    # Normalise keys — support both Redis schema and legacy schema
    pe        = fundamentals.get("pl")          or fundamentals.get("pe_ratio")
    pb        = fundamentals.get("pvp")         or fundamentals.get("pb_ratio")
    dy_raw    = fundamentals.get("dy")          or fundamentals.get("dividend_yield")
    ev_ebitda = fundamentals.get("ev_ebitda")
    market_cap= fundamentals.get("market_cap")
    sector    = fundamentals.get("setor")       or fundamentals.get("sector", "não especificado")
    industria = fundamentals.get("industria", "")
    roe       = fundamentals.get("roe")
    roa       = fundamentals.get("roa")
    margem_liq= fundamentals.get("margem_liquida")
    div_ebitda= fundamentals.get("divida_sobre_ebitda")
    beta      = fundamentals.get("beta")
    eps       = fundamentals.get("eps")

    sector_label = f"{sector}" + (f" / {industria}" if industria and industria != sector else "")

    prompt = (
        f"Realize valuation relativa de {ticker} (setor: {sector_label}).\n\n"
        f"Múltiplos do ativo:\n"
        f"- P/L: {_fmt(pe, 'x', decimals=1)} | Mediana B3: ~12-15x (valor) / ~20-30x (crescimento)\n"
        f"- P/VP: {_fmt(pb, 'x', decimals=2)} | Abaixo de 1x = possível desconto patrimonial\n"
        f"- EV/EBITDA: {_fmt(ev_ebitda, 'x', decimals=1)} | Referência: 6-10x empresas maduras B3\n"
        f"- Dividend Yield 12m: {_fmt(dy_raw, '%', pct=True)} \n"
        f"- Market Cap: {_fmt(market_cap)}\n"
        f"- Beta: {_fmt(beta, decimals=2)}\n"
        f"- EPS (LPA): {_fmt(eps)}\n\n"
        f"Rentabilidade e endividamento:\n"
        f"- ROE: {_fmt(roe, '%', pct=True)} | ROA: {_fmt(roa, '%', pct=True)}\n"
        f"- Margem Líquida: {_fmt(margem_liq, '%', pct=True)}\n"
        f"- Dívida Líquida/EBITDA: {_fmt(div_ebitda, 'x', decimals=1)}\n\n"
        f"Interprete:\n"
        f"1. Os múltiplos indicam sobre ou subvalorização relativa ao setor {sector}?\n"
        f"2. O ROE {_fmt(roe,'%',pct=True)} justifica o P/VP atual? "
        f"P/VP < 1 com ROE positivo = oportunidade ou armadilha?\n"
        f"3. O endividamento (D/EBITDA {_fmt(div_ebitda,'x',decimals=1)}) "
        f"é sustentável para o perfil do negócio?\n"
        f"4. Qual o principal risco de valuation para {ticker} nos próximos 12 meses?"
    )

    # Expose normalised multiples so callers can display them in the UI
    multiples = {
        "pl": _fmt(pe, "x"),
        "pvp": _fmt(pb, "x", decimals=2),
        "dy": _fmt(dy_raw, "%", pct=True),
        "ev_ebitda": _fmt(ev_ebitda, "x"),
        "roe": _fmt(roe, "%", pct=True),
        "margem_liquida": _fmt(margem_liq, "%", pct=True),
        "divida_ebitda": _fmt(div_ebitda, "x"),
        "beta": _fmt(beta, decimals=2),
        "setor": sector_label,
    }

    analysis = await call_llm(prompt, system=_SYSTEM, tier=tier)
    logger.info("Valuation analysis completed for %s", ticker)

    return {
        "ticker": ticker,
        "analysis": analysis,
        "multiples": multiples,
        "methodology": "Valuation Relativa — Múltiplos Comparativos",
        "disclaimer": DISCLAIMER_TEXT,
    }
