"""Macro impact analysis skill adapter.

Analyzes how current macroeconomic conditions (SELIC, IPCA, PTAX)
affect a specific portfolio allocation mix.
"""
from __future__ import annotations

import logging

from app.modules.ai.provider import call_llm
from app.modules.ai.skills import DISCLAIMER_TEXT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Você é um economista e estrategista de portfólio especializado no mercado brasileiro. "
    "Analise como o ambiente macroeconômico atual afeta cada classe de ativo do portfólio. "
    "Responda em português, máximo 4 parágrafos, linguagem clara e objetiva. "
    "NUNCA faça recomendação explícita de compra ou venda."
)


async def run_macro_impact(macro: dict, allocation: list[dict], investor_profile: dict | None = None, tier: str = "free") -> dict:
    """Run macro economic impact analysis for a portfolio allocation.

    Args:
        macro: Dict with keys: selic, cdi, ipca, ptax_usd (string or Decimal).
        allocation: List of dicts — each has asset_class, total_value, percentage.
            Example: [{"asset_class": "acao", "total_value": "120000", "percentage": "65.0"}]
        investor_profile: Optional dict with investor context for personalized analysis.

    Returns:
        Dict with keys: analysis, methodology, disclaimer.
    """
    selic = macro.get("selic", "N/D")
    cdi = macro.get("cdi", "N/D")
    ipca = macro.get("ipca", "N/D")
    ptax = macro.get("ptax_usd", "N/D")

    # Format allocation as readable text
    allocation_lines = []
    for item in allocation:
        asset_class = item.get("asset_class", "?")
        pct = item.get("percentage", "?")
        val = item.get("total_value", "?")
        allocation_lines.append(f"  - {asset_class}: {pct}% do portfólio (R$ {val})")
    allocation_text = "\n".join(allocation_lines) if allocation_lines else "  - Portfólio vazio"

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
        f"Analise o impacto do cenário macroeconômico atual neste portfólio brasileiro.\n\n"
        f"Indicadores macroeconômicos:\n"
        f"- SELIC: {selic}% a.a.\n"
        f"- CDI: {cdi}% a.a.\n"
        f"- IPCA (inflação): {ipca}% a.a.\n"
        f"- PTAX (dólar): R$ {ptax}\n\n"
        f"Composição do portfólio:\n{allocation_text}\n"
        f"{profile_context}\n"
        f"Avalie:\n"
        f"1. Com SELIC em {selic}% a.a., a alocação em renda variável está adequada vs. "
        f"custo de oportunidade da renda fixa?\n"
        f"2. Como o IPCA de {ipca}% afeta o poder de compra dos dividendos e a rentabilidade real?\n"
        f"3. A exposição cambial (PTAX {ptax}) é relevante para esta composição?\n"
        f"4. Quais classes de ativos desta carteira se beneficiam ou são prejudicadas "
        f"no cenário macro atual?"
        + (f"\n5. A composição atual está alinhada com o perfil '{risco}' e objetivo '{objetivo}'?" if investor_profile else "")
    )

    analysis = await call_llm(prompt, system=_SYSTEM, tier=tier)
    logger.info("Macro impact analysis completed")

    return {
        "analysis": analysis,
        "methodology": "Análise de Impacto Macroeconômico",
        "disclaimer": DISCLAIMER_TEXT,
    }
