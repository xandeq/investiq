"""Risks section: identify and assess top risks of the day via LLM."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_RISKS = """Você é um gestor de risco de uma asset management brasileira.
Dado o snapshot macro do dia (índices, moedas, juros), identifique os 5 principais riscos para investimentos.
Para cada risco retorne JSON: nome, probabilidade (alta/média/baixa), impacto (alto/médio/baixo),
setores_afetados (lista), como_se_proteger (1 linha).
Retorne APENAS JSON array com 5 itens."""


async def generate_risks(macro_data: dict[str, Any], news: list[dict]) -> list[dict[str, Any]]:
    """Generate risk assessment from macro data + news via LLM."""
    vix = macro_data.get("vix")
    ptax = macro_data.get("ptax")
    sp500 = macro_data.get("sp500")
    selic = macro_data.get("selic")
    oil = macro_data.get("oil_wti")

    # Build context for LLM
    macro_summary = (
        f"VIX={vix or 'N/D'}, S&P500={sp500 or 'N/D'}, "
        f"Dólar/BRL={ptax or 'N/D'}, SELIC={selic or 'N/D'}%, "
        f"Petróleo WTI={oil or 'N/D'}"
    )

    news_summary = ""
    if news:
        headlines = [n.get("manchete", n.get("headline", "")) for n in news[:5]]
        news_summary = "\nPrincipais notícias: " + " | ".join(headlines)

    prompt = f"Macro hoje: {macro_summary}{news_summary}\n\nIdentifique os 5 principais riscos para investimentos BR hoje."

    try:
        import json
        from app.modules.ai.provider import call_llm
        raw = await call_llm(prompt, system=_SYSTEM_RISKS, tier="paid", max_tokens=800)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])[:5]
    except Exception as exc:
        logger.warning("risks: LLM failed: %s", exc)

    # Fallback: generic risks
    risks = []
    if vix and vix > 20:
        risks.append({
            "nome": f"Volatilidade elevada (VIX={vix:.0f})",
            "probabilidade": "alta",
            "impacto": "alto",
            "setores_afetados": ["todos"],
            "como_se_proteger": "Reduzir posições especulativas, aumentar hedge",
        })
    risks += [
        {
            "nome": "Deterioração fiscal brasileira",
            "probabilidade": "média",
            "impacto": "alto",
            "setores_afetados": ["juros", "câmbio", "bolsa geral"],
            "como_se_proteger": "Maior alocação em exportadoras e dólar",
        },
        {
            "nome": "Mercado americano em correção",
            "probabilidade": "média",
            "impacto": "médio",
            "setores_afetados": ["tecnologia", "growth", "cripto"],
            "como_se_proteger": "Priorizar dividendos e value BR",
        },
    ]
    return risks[:5]


def format_risks_section(risks: list[dict[str, Any]]) -> str:
    """Format risks section as Telegram HTML."""
    if not risks:
        return "<b>⚠️ Principais Riscos</b>\n\nAnálise de riscos indisponível no momento."

    lines = ["<b>⚠️ Principais Riscos do Dia</b>", ""]
    prob_emoji = {"alta": "🔴", "média": "🟡", "baixa": "🟢"}
    impact_emoji = {"alto": "⬆️", "médio": "➡️", "baixo": "⬇️"}

    for i, r in enumerate(risks, 1):
        prob = r.get("probabilidade", "?")
        impact = r.get("impacto", "?")
        setores = r.get("setores_afetados", [])
        protecao = r.get("como_se_proteger", "")

        pe = prob_emoji.get(prob, "⚪")
        ie = impact_emoji.get(impact, "➡️")
        setores_str = ", ".join(setores) if isinstance(setores, list) else str(setores)

        lines.append(f"{pe} <b>{i}. {r.get('nome', '?')}</b>")
        lines.append(f"  Prob: {prob} | Impacto: {ie} {impact}")
        lines.append(f"  Setores: {setores_str}")
        lines.append(f"  🛡️ {protecao}")
        lines.append("")

    return "\n".join(lines)
