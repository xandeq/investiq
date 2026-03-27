"""Earnings quality and dividend analysis skill adapter.

Analyzes earnings quality, payout sustainability, and dividend history
for a given B3 asset.
"""
from __future__ import annotations

import logging

from app.modules.ai.provider import call_llm
from app.modules.ai.skills import DISCLAIMER_TEXT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Você é um analista especializado em qualidade de lucros e dividendos de empresas brasileiras. "
    "Analise a sustentabilidade dos dividendos e a qualidade dos lucros reportados. "
    "Responda em português, máximo 3 parágrafos, linguagem técnica e objetiva. "
    "NUNCA faça recomendação explícita de compra ou venda."
)


async def run_earnings(ticker: str, fundamentals: dict, tier: str = "free") -> dict:
    """Run earnings quality and dividend sustainability analysis.

    Args:
        ticker: B3 ticker symbol.
        fundamentals: Dict from FundamentalsCache.

    Returns:
        Dict with keys: ticker, analysis, methodology, disclaimer.
    """
    pe = fundamentals.get("pe_ratio", "N/D")
    dy = fundamentals.get("dividend_yield", "N/D")
    roe = fundamentals.get("roe", "N/D")
    revenue_growth = fundamentals.get("revenue_growth", "N/D")
    profit_margin = fundamentals.get("profit_margin", "N/D")
    payout_ratio = fundamentals.get("payout_ratio", "N/D")

    prompt = (
        f"Analise a qualidade dos lucros e sustentabilidade dos dividendos de {ticker}.\n\n"
        f"Indicadores:\n"
        f"- P/L: {pe} (quanto o mercado paga por R$1 de lucro)\n"
        f"- Dividend Yield: {dy}%\n"
        f"- ROE (Retorno sobre Patrimônio): {roe}%\n"
        f"- Crescimento de Receita: {revenue_growth}%\n"
        f"- Margem de Lucro: {profit_margin}%\n"
        f"- Payout Ratio: {payout_ratio}%\n\n"
        f"Avalie:\n"
        f"1. O ROE de {roe}% justifica o P/L de {pe}? Os lucros são recorrentes ou pontuais?\n"
        f"2. O payout ratio de {payout_ratio}% é sustentável com a margem e crescimento atuais?\n"
        f"3. Existe risco de corte de dividendos ou diluição nos próximos 2 anos?"
    )

    analysis = await call_llm(prompt, system=_SYSTEM, tier=tier)
    logger.info("Earnings analysis completed for %s", ticker)

    return {
        "ticker": ticker,
        "analysis": analysis,
        "methodology": "Análise de Lucros e Dividendos",
        "disclaimer": DISCLAIMER_TEXT,
    }
