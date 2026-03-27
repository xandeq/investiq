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


async def run_valuation(ticker: str, fundamentals: dict, tier: str = "free") -> dict:
    """Run relative valuation analysis for a B3 asset.

    Args:
        ticker: B3 ticker symbol.
        fundamentals: Dict from FundamentalsCache.

    Returns:
        Dict with keys: ticker, analysis, methodology, disclaimer.
    """
    pe = fundamentals.get("pe_ratio", "N/D")
    pb = fundamentals.get("pb_ratio", "N/D")
    dy = fundamentals.get("dividend_yield", "N/D")
    ev_ebitda = fundamentals.get("ev_ebitda", "N/D")
    market_cap = fundamentals.get("market_cap", "N/D")
    sector = fundamentals.get("sector", "não especificado")

    prompt = (
        f"Realize valuation relativa de {ticker} (setor: {sector}).\n\n"
        f"Múltiplos do ativo:\n"
        f"- P/L: {pe} | Mediana B3 historica: ~12-15x (acoes valor) / ~20-30x (crescimento)\n"
        f"- P/VP: {pb} | Abaixo de 1x = potencial desconto vs. patrimônio\n"
        f"- EV/EBITDA: {ev_ebitda} | Referência: 6-10x para empresas maduras B3\n"
        f"- Dividend Yield: {dy}%\n"
        f"- Market Cap: {market_cap}\n\n"
        f"Interprete:\n"
        f"1. Os múltiplos indicam sobre ou subvalorização relativa ao setor {sector}?\n"
        f"2. O P/VP < 1 tem alguma justificativa operacional (ROE baixo, deterioração) "
        f"ou é oportunidade?\n"
        f"3. Qual o principal risco de valuation para {ticker} nos próximos 12 meses?"
    )

    analysis = await call_llm(prompt, system=_SYSTEM, tier=tier)
    logger.info("Valuation analysis completed for %s", ticker)

    return {
        "ticker": ticker,
        "analysis": analysis,
        "methodology": "Valuation Relativa — Múltiplos Comparativos",
        "disclaimer": DISCLAIMER_TEXT,
    }
