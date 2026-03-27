"""Goldman Sachs Stock Screener skill — AI-powered B3 stock screening."""
from __future__ import annotations

import json
import logging

from app.modules.ai.provider import call_llm

logger = logging.getLogger(__name__)

DISCLAIMER = (
    "Este relatório é gerado por inteligência artificial e tem caráter exclusivamente "
    "educacional e informativo. Não constitui recomendação de investimento. "
    "Consulte um assessor financeiro certificado antes de tomar decisões."
)

_SYSTEM = (
    "Você é um analista sênior de equity com 20 anos de experiência triando ações "
    "para clientes de alta renda em uma grande gestora brasileira. "
    "Foco exclusivo em ativos da B3 (bolsa brasileira). "
    "Responda EXCLUSIVAMENTE em JSON válido, sem texto antes ou depois. "
    "Use dados reais conhecidos sobre empresas brasileiras. "
    "Seja preciso, objetivo e profissional — estilo relatório Goldman Sachs."
)

_OUTPUT_SCHEMA = """{
  "summary": "parágrafo executivo de 3 linhas sobre o cenário atual e a seleção",
  "stocks": [
    {
      "ticker": "VALE3",
      "company_name": "Vale S.A.",
      "sector": "Mineração",
      "pe_ratio": 6.5,
      "pe_vs_sector": "30% abaixo da média do setor de mineração",
      "revenue_growth_5y": "+8% CAGR nos últimos 5 anos",
      "debt_to_equity": 0.42,
      "debt_health": "saudável",
      "dividend_yield": 8.2,
      "payout_score": "sustentável",
      "moat_rating": "forte",
      "moat_description": "Maior produtora mundial de minério de ferro de alta qualidade com ativos únicos",
      "bull_target": 75.0,
      "bear_target": 48.0,
      "current_price_ref": 62.0,
      "risk_score": 6,
      "risk_reasoning": "Exposição a commodities e câmbio, mas balanço sólido e dividendos consistentes",
      "entry_zone": "R$ 58–64",
      "stop_loss": "abaixo de R$ 52",
      "thesis": "Líder global com vantagens de custo estruturais e dividend yield atrativo acima do CDI."
    }
  ]
}"""


async def run_goldman_screener(
    investor_profile: dict | None,
    portfolio_tickers: list[str],
    macro: dict,
    sector_filter: str | None,
    custom_notes: str | None,
    tier: str = "paid",
) -> dict:
    """Run Goldman Sachs-style B3 stock screening.

    Args:
        investor_profile: User profile dict (tolerancia_risco, horizonte_anos, etc.)
        portfolio_tickers: Tickers the user already holds (to avoid duplication)
        macro: Dict with selic, cdi, ipca, ptax_usd
        sector_filter: Optional sector preference (ex: "Financeiro")
        custom_notes: Optional freeform user notes

    Returns:
        Dict with summary and list of 10 StockAnalysis dicts + disclaimer.
    """
    selic = macro.get("selic", "N/D")
    cdi = macro.get("cdi", "N/D")
    ipca = macro.get("ipca", "N/D")
    ptax = macro.get("ptax_usd", "N/D")

    # Profile context
    profile_text = "Não informado"
    if investor_profile:
        risco = investor_profile.get("tolerancia_risco") or "N/D"
        horizonte = investor_profile.get("horizonte_anos") or "N/D"
        objetivo = investor_profile.get("objetivo") or "N/D"
        rf_alvo = investor_profile.get("percentual_renda_fixa_alvo") or "N/D"
        profile_text = (
            f"Tolerância ao risco: {risco} | "
            f"Horizonte: {horizonte} anos | "
            f"Objetivo: {objetivo} | "
            f"Alvo renda fixa: {rf_alvo}%"
        )

    already_holds = ", ".join(portfolio_tickers[:20]) if portfolio_tickers else "nenhum"
    sector_line = f"Setor preferido: {sector_filter}" if sector_filter else "Sem restrição de setor"
    notes_line = f"Observações adicionais: {custom_notes}" if custom_notes else ""

    prompt = f"""Faça uma triagem completa de ações da B3 no estilo Goldman Sachs.

PERFIL DO INVESTIDOR:
{profile_text}

CONTEXTO MACROECONÔMICO:
- SELIC: {selic}% a.a. (taxa livre de risco)
- CDI: {cdi}% a.a.
- IPCA: {ipca}% (inflação mensal recente)
- PTAX: R$ {ptax}

PREFERÊNCIAS:
- {sector_line}
- {notes_line}
- Ativos que o investidor JÁ POSSUI (não recomendar duplicatas): {already_holds}

INSTRUÇÃO:
Selecione os 10 melhores ativos da B3 que melhor se encaixam neste perfil.
Para cada ativo, forneça análise completa conforme o schema abaixo.
Considere diversificação entre setores.
Use o SELIC ({selic}%) como benchmark — só recomende ativos com retorno esperado superior.

Retorne APENAS o JSON abaixo, sem nenhum texto adicional:
{_OUTPUT_SCHEMA}
"""

    raw = await call_llm(prompt, system=_SYSTEM, model="gpt-4o", tier=tier, max_tokens=4000)
    logger.info("Goldman screener AI call completed")

    # Parse JSON
    text = raw.strip()
    if text.startswith("```"):
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    try:
        result = json.loads(text.strip())
    except (json.JSONDecodeError, IndexError) as exc:
        logger.error("Failed to parse screener JSON: %s | raw: %s", exc, raw[:200])
        raise ValueError(f"AI returned invalid JSON: {exc}") from exc

    stocks = result.get("stocks", [])
    if not stocks:
        logger.error("Screener returned empty stocks list. summary=%s", result.get("summary", "")[:100])
        raise ValueError("AI returned no stocks. Possibly model did not follow the schema.")

    result["disclaimer"] = DISCLAIMER
    result["generated_at"] = __import__("datetime").datetime.utcnow().isoformat()
    return result
