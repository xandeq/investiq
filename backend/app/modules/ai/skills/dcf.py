"""DCF (Discounted Cash Flow) skill adapter.

Provides AI-powered DCF interpretation for a given B3 asset, using
fundamentals from Redis cache and macro context (SELIC/CDI/IPCA as
discount rate proxies).
"""
from __future__ import annotations

import logging

from app.modules.ai.provider import call_llm
from app.modules.ai.skills import DISCLAIMER_TEXT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Você é um analista financeiro sênior especializado em ações brasileiras (B3). "
    "Forneça análises objetivas e técnicas em português. "
    "Seja direto — máximo 4 parágrafos. "
    "NUNCA faça recomendação explícita de compra ou venda."
)


async def run_dcf(ticker: str, fundamentals: dict, macro: dict, investor_profile: dict | None = None, tier: str = "free") -> dict:
    """Run DCF interpretation for a B3 asset.

    Args:
        ticker: B3 ticker symbol (e.g. "VALE3").
        fundamentals: Dict from FundamentalsCache — may include pe_ratio, pb_ratio,
            dividend_yield, ev_ebitda, roe, revenue_growth.
        macro: Dict with keys selic, cdi, ipca, ptax_usd (Decimal or float strings).
        investor_profile: Optional dict with investor context (objetivo, horizonte_anos,
            tolerancia_risco, percentual_renda_fixa_alvo) for personalized analysis.

    Returns:
        Dict with keys: ticker, analysis, methodology, disclaimer.
    """
    pe = fundamentals.get("pe_ratio", "N/D")
    pb = fundamentals.get("pb_ratio", "N/D")
    dy = fundamentals.get("dividend_yield", "N/D")
    ev_ebitda = fundamentals.get("ev_ebitda", "N/D")
    roe = fundamentals.get("roe", "N/D")

    selic = macro.get("selic", "N/D")
    cdi = macro.get("cdi", "N/D")
    ipca = macro.get("ipca", "N/D")

    profile_context = ""
    if investor_profile:
        objetivo = investor_profile.get("objetivo") or "N/D"
        horizonte = investor_profile.get("horizonte_anos") or "N/D"
        risco = investor_profile.get("tolerancia_risco") or "N/D"
        rf_alvo = investor_profile.get("percentual_renda_fixa_alvo") or "N/D"
        profile_context = (
            f"\nPerfil do investidor:\n"
            f"- Objetivo: {objetivo}\n"
            f"- Horizonte: {horizonte} anos\n"
            f"- Tolerância ao risco: {risco}\n"
            f"- Alocação alvo em renda fixa: {rf_alvo}%\n"
        )

    prompt = (
        f"Analise {ticker} sob perspectiva de DCF (Fluxo de Caixa Descontado).\n\n"
        f"Indicadores fundamentalistas:\n"
        f"- P/L (Price-to-Earnings): {pe}\n"
        f"- P/VP (Price-to-Book): {pb}\n"
        f"- Dividend Yield: {dy}%\n"
        f"- EV/EBITDA: {ev_ebitda}\n"
        f"- ROE: {roe}%\n\n"
        f"Contexto macroeconômico (taxas de desconto de referência):\n"
        f"- SELIC: {selic}% a.a.\n"
        f"- CDI: {cdi}% a.a.\n"
        f"- IPCA: {ipca}% a.a.\n"
        f"{profile_context}\n"
        f"Com base nesses dados, interprete:\n"
        f"1. O múltiplo P/L implica um retorno futuro compatível com o custo de oportunidade (SELIC/CDI)?\n"
        f"2. O EV/EBITDA sugere sobre ou subvalorização relativa ao setor?\n"
        f"3. O ROE compensa o risco frente à renda fixa?\n"
        f"4. Qual é o principal risco e catalisador para {ticker} no cenário macro atual?"
        + (f"\n5. Este ativo faz sentido para o perfil '{risco}' com horizonte de {horizonte} anos?" if investor_profile else "")
    )

    analysis = await call_llm(prompt, system=_SYSTEM, tier=tier)
    logger.info("DCF analysis completed for %s", ticker)

    return {
        "ticker": ticker,
        "analysis": analysis,
        "methodology": "DCF — Fluxo de Caixa Descontado",
        "disclaimer": DISCLAIMER_TEXT,
    }
