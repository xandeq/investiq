"""Portfolio Advisor skill — full AI analysis of the user's portfolio.

Analyzes positions + P&L + macro + investor profile and returns structured
actionable insights: diagnosis, positives, concerns, suggestions, next steps.
"""
from __future__ import annotations

import json
import logging

from app.modules.ai.provider import call_llm
from app.modules.ai.skills import DISCLAIMER_TEXT

logger = logging.getLogger(__name__)

_SYSTEM = (
    "Você é um consultor financeiro independente especializado em carteiras de investimento brasileiras (B3). "
    "Analise a carteira com profundidade e objetividade. "
    "Responda EXCLUSIVAMENTE em JSON válido, sem texto antes ou depois do JSON. "
    "NUNCA faça recomendação explícita de compra ou venda de ativos específicos. "
    "Foque em diagnóstico, diversificação, alinhamento com perfil e gestão de risco."
)

_OUTPUT_SCHEMA = """{
  "diagnostico": "parágrafo resumindo o estado geral da carteira",
  "pontos_positivos": ["item 1", "item 2", "item 3"],
  "pontos_de_atencao": ["item 1", "item 2", "item 3"],
  "sugestoes": ["sugestão 1", "sugestão 2", "sugestão 3"],
  "proximos_passos": ["passo 1", "passo 2", "passo 3"]
}"""


async def run_portfolio_advisor(
    positions: list[dict],
    pnl: dict,
    allocation: list[dict],
    macro: dict,
    investor_profile: dict | None = None,
    tier: str = "free",
) -> dict:
    """Run a full AI portfolio analysis.

    Args:
        positions: List of position dicts (ticker, asset_class, quantity, cmp, total_cost,
            current_price, unrealized_pnl, unrealized_pnl_pct).
        pnl: Portfolio P&L summary (realized_pnl_total, unrealized_pnl_total, total_portfolio_value).
        allocation: List of allocation dicts (asset_class, total_value, percentage).
        macro: Dict with selic, cdi, ipca, ptax_usd.
        investor_profile: Optional dict with investor context.

    Returns:
        Dict with keys: diagnostico, pontos_positivos, pontos_de_atencao, sugestoes,
            proximos_passos, disclaimer.
    """
    selic = macro.get("selic", "N/D")
    cdi = macro.get("cdi", "N/D")
    ipca = macro.get("ipca", "N/D")
    ptax = macro.get("ptax_usd", "N/D")

    # Format positions
    pos_lines = []
    for p in positions[:15]:  # limit to top 15 to keep prompt manageable
        ticker = p.get("ticker", "?")
        ac = p.get("asset_class", "?")
        qty = p.get("quantity", "?")
        cmp = p.get("cmp", "?")
        cost = p.get("total_cost", "?")
        upnl = p.get("unrealized_pnl")
        upnl_pct = p.get("unrealized_pnl_pct")
        pnl_str = f"P&L: R$ {upnl} ({upnl_pct}%)" if upnl is not None else "P&L: N/D"
        pos_lines.append(f"  - {ticker} ({ac}): {qty} cotas @ CMP R$ {cmp} | Custo R$ {cost} | {pnl_str}")
    positions_text = "\n".join(pos_lines) if pos_lines else "  - Carteira vazia"

    # Format allocation
    alloc_lines = [
        f"  - {a.get('asset_class')}: {a.get('percentage')}% (R$ {a.get('total_value')})"
        for a in allocation
    ]
    alloc_text = "\n".join(alloc_lines) if alloc_lines else "  - Sem alocação"

    total_value = pnl.get("total_portfolio_value", "N/D")
    realized = pnl.get("realized_pnl_total", "N/D")
    unrealized = pnl.get("unrealized_pnl_total", "N/D")

    profile_context = ""
    if investor_profile:
        objetivo = investor_profile.get("objetivo") or "N/D"
        horizonte = investor_profile.get("horizonte_anos") or "N/D"
        risco = investor_profile.get("tolerancia_risco") or "N/D"
        rf_alvo = investor_profile.get("percentual_renda_fixa_alvo") or "N/D"
        profile_context = (
            f"\nPerfil do investidor:\n"
            f"  - Objetivo: {objetivo}\n"
            f"  - Horizonte: {horizonte} anos\n"
            f"  - Tolerância ao risco: {risco}\n"
            f"  - Alocação alvo em renda fixa: {rf_alvo}%\n"
        )

    prompt = (
        f"Analise esta carteira de investimentos brasileira e retorne um diagnóstico estruturado.\n\n"
        f"Resumo da carteira:\n"
        f"  - Valor total: R$ {total_value}\n"
        f"  - P&L realizado: R$ {realized}\n"
        f"  - P&L não realizado: R$ {unrealized}\n\n"
        f"Posições atuais:\n{positions_text}\n\n"
        f"Alocação por classe:\n{alloc_text}\n"
        f"{profile_context}\n"
        f"Contexto macroeconômico:\n"
        f"  - SELIC: {selic}% a.a.\n"
        f"  - CDI: {cdi}% a.a.\n"
        f"  - IPCA: {ipca}% a.a.\n"
        f"  - PTAX: R$ {ptax}\n\n"
        f"Retorne APENAS o JSON abaixo, sem nenhum texto adicional:\n{_OUTPUT_SCHEMA}"
    )

    raw = await call_llm(prompt, system=_SYSTEM, tier=tier)
    logger.info("Portfolio advisor analysis completed (%d positions)", len(positions))

    # Parse structured output
    try:
        # Extract JSON if wrapped in markdown code fences
        text = raw.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        result = json.loads(text.strip())
    except (json.JSONDecodeError, IndexError):
        # Fallback: wrap raw text in structured format
        result = {
            "diagnostico": raw,
            "pontos_positivos": [],
            "pontos_de_atencao": [],
            "sugestoes": [],
            "proximos_passos": [],
        }

    result["disclaimer"] = DISCLAIMER_TEXT
    return result
