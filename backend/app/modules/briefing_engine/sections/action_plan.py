"""Action plan section: daily action plan + watchlist with triggers."""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_SYSTEM_ACTION = """Você é um consultor de investimentos objetivo.
Dado o cenário do dia (macro, sinais, riscos), gere:
1. Resumo executivo (3-4 linhas): cenário, viés, tema dominante, ação geral
2. Plano de ação por perfil (conservador, moderado, agressivo, cripto)
3. Watchlist objetiva: 5-8 itens com gatilho específico
Retorne JSON com: resumo_executivo (str), vies (bullish/neutro/bearish),
risco_dia (alto/moderado/baixo), tema_dominante (str), plano_conservador (str),
plano_moderado (str), plano_agressivo (str), plano_cripto (str), watchlist (list of {ativo, gatilho}).
APENAS JSON."""


async def generate_action_plan(
    macro_data: dict[str, Any],
    signals: dict[str, Any],
    risks: list[dict[str, Any]],
    recommendations_equity: list[dict],
    recommendations_fiis: list[dict],
) -> dict[str, Any]:
    """Generate the daily action plan via LLM."""
    # Build context
    equity_tickers = [r.get("ticker", "") for r in recommendations_equity[:3]]
    fii_tickers = [r.get("ticker", "") for r in recommendations_fiis[:3]]
    signal_tickers = [s.get("ticker", "") for s in signals.get("equity", [])]
    top_risks = [r.get("nome", "") for r in risks[:3]]

    vix = macro_data.get("vix")
    ptax = macro_data.get("ptax")
    selic = macro_data.get("selic")
    fg = macro_data.get("fear_greed") or {}

    prompt = (
        f"Macro: VIX={vix}, PTAX={ptax}, SELIC={selic}%, "
        f"Fear&Greed={fg.get('value','?')} ({fg.get('classification','?')})\n"
        f"Ações recomendadas: {', '.join(equity_tickers) or 'nenhuma'}\n"
        f"FIIs recomendados: {', '.join(fii_tickers) or 'nenhum'}\n"
        f"Sinais A+: {', '.join(signal_tickers) or 'nenhum'}\n"
        f"Top riscos: {' | '.join(top_risks)}\n\n"
        f"Gere o plano de ação do dia."
    )

    try:
        import json
        from app.modules.ai.provider import call_llm
        raw = await call_llm(prompt, system=_SYSTEM_ACTION, tier="standard", max_tokens=1000)
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])
    except Exception as exc:
        logger.warning("action_plan: LLM failed: %s", exc)

    # Fallback
    vix_level = "alto" if (vix and vix > 20) else "moderado"
    watchlist = []
    for t in equity_tickers:
        watchlist.append({"ativo": t, "gatilho": "pullback com volume acima da média"})
    for t in fii_tickers:
        watchlist.append({"ativo": t, "gatilho": "abaixo do valor patrimonial"})
    if macro_data.get("btc"):
        watchlist.append({"ativo": "BTC", "gatilho": "rompimento de resistência com volume"})

    return {
        "resumo_executivo": f"Cenário de risco {vix_level}. Foco em qualidade e defensivos.",
        "vies": "neutro",
        "risco_dia": vix_level,
        "tema_dominante": "qualidade + dividendos",
        "plano_conservador": "Priorizar Tesouro Selic e CDB de liquidez diária.",
        "plano_moderado": f"Montar posição parcial em {', '.join(equity_tickers[:2]) or 'ações de dividendos'}.",
        "plano_agressivo": f"Swing trade só com gatilho técnico: {', '.join(signal_tickers[:2]) or 'aguardar A+'}.",
        "plano_cripto": "Entrar só com confirmação. Stop obrigatório.",
        "watchlist": watchlist[:8],
    }


def format_executive_summary(plan: dict[str, Any]) -> str:
    """Format the executive summary (top of report)."""
    vies = plan.get("vies", "neutro")
    risco = plan.get("risco_dia", "?")
    tema = plan.get("tema_dominante", "?")
    resumo = plan.get("resumo_executivo", "")

    vies_emoji = {"bullish": "🟢", "neutro": "🟡", "bearish": "🔴"}.get(vies, "⚪")
    risco_emoji = {"alto": "🔴", "moderado": "🟡", "baixo": "🟢"}.get(risco, "⚪")

    return (
        f"<b>📋 Resumo Executivo</b>\n\n"
        f"{vies_emoji} <b>Viés:</b> {vies.capitalize()}\n"
        f"{risco_emoji} <b>Risco do dia:</b> {risco.capitalize()}\n"
        f"🎯 <b>Tema dominante:</b> {tema}\n\n"
        f"{resumo}"
    )


def format_action_plan_section(plan: dict[str, Any]) -> str:
    """Format action plan + watchlist as Telegram HTML."""
    lines = ["<b>🎯 Plano de Ação do Dia</b>", ""]

    plans = [
        ("🛡️ Conservador", plan.get("plano_conservador", "")),
        ("⚖️ Moderado", plan.get("plano_moderado", "")),
        ("⚡ Agressivo", plan.get("plano_agressivo", "")),
        ("₿ Cripto", plan.get("plano_cripto", "")),
    ]
    for label, text in plans:
        if text:
            lines.append(f"<b>{label}:</b> {text}")

    lines.append("")
    lines.append("<b>👁️ Watchlist — Monitorar hoje</b>")
    lines.append("")

    watchlist = plan.get("watchlist", [])
    for w in watchlist:
        ativo = w.get("ativo", "?")
        gatilho = w.get("gatilho", "?")
        lines.append(f"  • <b>{ativo}</b> — {gatilho}")

    return "\n".join(lines)
