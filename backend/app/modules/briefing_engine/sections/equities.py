"""Equities section: recommended stocks and bargains.

Uses chart_analyzer + signal_engine data. With BRAPI Pro, adds
fundamentals (P/L, ROE, DY). Without Pro, uses technical data only.
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Base curated dividend + quality stocks universe (full expanded list)
_DIVIDEND_UNIVERSE_DEFAULT = [
    "BBSE3", "ITUB4", "BBDC4", "ABEV3", "EGIE3",
    "TAEE11", "CMIG4", "VIVT3", "KLBN11", "WEGE3",
    "BBAS3", "SANB11", "JBSS3", "BEEF3", "PETR4",
    "VALE3", "PRIO3", "ENEV3", "SUZB3", "RDOR3",
]


async def _get_dynamic_equity_universe(redis_client, fallback: list[str]) -> list[str]:
    """Return equities ranked by DY (highest first) using Redis fundamentals cache.

    Filters out stocks with ROE < 0 (quality filter). Falls back to curated list.
    """
    if redis_client is None:
        return fallback

    dy_scores: list[tuple[str, float]] = []
    for ticker in fallback:
        try:
            raw = await redis_client.get(f"market:fundamentals:{ticker}")
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode()
                fund = json.loads(raw)
                roe = fund.get("roe")
                # Skip negative ROE (quality filter)
                if roe is not None and roe < 0:
                    continue
                dy = fund.get("dy")
                dy_pct = (dy * 100 if dy and abs(dy) < 1 else (dy or 0.0))
                dy_scores.append((ticker, dy_pct))
            else:
                dy_scores.append((ticker, 0.0))
        except Exception:
            dy_scores.append((ticker, 0.0))

    if not dy_scores:
        return fallback

    dy_scores.sort(key=lambda x: x[1], reverse=True)
    return [t for t, _ in dy_scores]

_SYSTEM_EQUITIES = """Você é um analista de ações brasileiro sênior.
Dado dados técnicos de ações (regime, RSI, confluências, setup), gere uma tabela de recomendações.
Para cada ação, retorne JSON com: ticker, tese (1 linha), faixa_entrada, risco (baixo/médio/alto), horizonte, nota (0-10), motivo_destaque.
Seja direto. Sem disclaimer. Máximo 5 ações. Retorne APENAS JSON array."""


async def fetch_equities_data(redis_client=None) -> dict[str, Any]:
    """Fetch technical analysis for dividend universe.

    Universe is dynamically ranked by real DY from Redis cache (BRAPI Startup),
    filtered for positive ROE. Falls back to curated list.
    """
    brapi_token = os.environ.get("BRAPI_TOKEN", "")

    # Dynamic universe ranked by DY
    universe = await _get_dynamic_equity_universe(redis_client, _DIVIDEND_UNIVERSE_DEFAULT)

    sem = asyncio.Semaphore(3)  # limit concurrent BRAPI calls to avoid 429

    async def _analyze(ticker: str):
        async with sem:
            try:
                await asyncio.sleep(0.3)  # small stagger
                from app.modules.chart_analyzer.analyzer import analyze
                return await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
            except Exception:
                return None

    tasks = [_analyze(t) for t in universe]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    analyzed = []
    for ticker, result in zip(universe, results):
        if isinstance(result, dict) and not result.get("error"):
            analyzed.append({"ticker": ticker, "analysis": result})

    # Enrich with fundamentals from Redis (populated by refresh_quotes task)
    if redis_client is not None:
        import json as _json
        for item in analyzed:
            try:
                raw = await redis_client.get(f"market:fundamentals:{item['ticker']}")
                if raw:
                    if isinstance(raw, bytes):
                        raw = raw.decode()
                    item["fund"] = _json.loads(raw)
            except Exception:
                item["fund"] = {}
    else:
        for item in analyzed:
            item["fund"] = {}

    return {"analyzed": analyzed}


async def generate_equity_recommendations(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Use LLM to generate buy recommendations from analyzed data."""
    analyzed = data.get("analyzed", [])
    if not analyzed:
        return []

    # Build summary for LLM — include fundamentals from Redis cache
    import json as _json
    import os as _os
    summaries = []
    for item in analyzed:
        t = item["ticker"]
        a = item["analysis"]
        ind = a.get("indicators", {})
        setup = a.get("setup")
        confluences = a.get("confluences", [])

        line = (
            f"- {t}: regime={ind.get('regime','?')}, RSI={ind.get('rsi_14','?')}, "
            f"confluências={len(confluences)}, setup={'sim' if setup else 'não'}"
        )

        # Add fundamentals from Redis if available
        fund = item.get("fund", {})
        fund_parts = []
        if fund.get("pl"):
            fund_parts.append(f"P/L={fund['pl']:.1f}")
        if fund.get("pvp"):
            fund_parts.append(f"P/VP={fund['pvp']:.2f}")
        if fund.get("dy"):
            fund_parts.append(f"DY={fund['dy']*100:.1f}%" if fund['dy'] < 1 else f"DY={fund['dy']:.1f}%")
        if fund.get("roe"):
            fund_parts.append(f"ROE={fund['roe']*100:.1f}%" if fund['roe'] < 1 else f"ROE={fund['roe']:.1f}%")
        if fund_parts:
            line += " | " + " ".join(fund_parts)

        summaries.append(line)

    prompt = "Analise as seguintes ações e recomende as 3-5 melhores para carteira agora:\n\n" + "\n".join(summaries)

    try:
        import json
        from app.modules.ai.provider import call_llm
        raw = await call_llm(prompt, system=_SYSTEM_EQUITIES, tier="paid", max_tokens=800)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])[:5]
    except Exception as exc:
        logger.warning("equities: LLM recommendation failed: %s", exc)

    # Fallback: top by confluences
    fallback = sorted(analyzed, key=lambda x: len(x["analysis"].get("confluences", [])), reverse=True)[:3]
    return [
        {
            "ticker": item["ticker"],
            "tese": f"Setup técnico: {len(item['analysis'].get('confluences', []))} confluências",
            "faixa_entrada": f"R${item['analysis']['indicators'].get('ema20', '?')}",
            "risco": "médio",
            "horizonte": "médio prazo",
            "nota": 7.0,
            "motivo_destaque": "confluências técnicas",
        }
        for item in fallback
    ]


async def generate_bargains(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Identify undervalued stocks (technical oversold + good fundamentals)."""
    analyzed = data.get("analyzed", [])
    bargains = []
    for item in analyzed:
        a = item["analysis"]
        ind = a.get("indicators", {})
        rsi = ind.get("rsi_14", 50)
        regime = ind.get("regime", "")
        # Oversold in trending_up regime = bargain candidate
        if rsi < 40 and "up" in str(regime).lower():
            bargains.append({
                "ticker": item["ticker"],
                "motivo_desconto": f"RSI={rsi:.0f} — sobrevendido em tendência de alta",
                "valida_compra": "RSI retornar acima de 45 com volume",
                "invalida_tese": "Perda do suporte ou deterioração de fundamentos",
            })
    return bargains[:3]


def format_equities_section(recommendations: list[dict], bargains: list[dict]) -> str:
    """Format equities section as Telegram HTML."""
    lines = ["<b>📈 Ações Recomendadas Agora</b>", ""]

    if recommendations:
        for r in recommendations:
            nota = r.get("nota", "?")
            ticker = r.get("ticker", "?")
            tese = r.get("tese", "")
            entrada = r.get("faixa_entrada", "?")
            risco = r.get("risco", "?")
            horizonte = r.get("horizonte", "?")
            lines.append(f"<b>{ticker}</b> ⭐{nota}")
            lines.append(f"  📌 {tese}")
            lines.append(f"  💰 Entrada: {entrada} | Risco: {risco} | {horizonte}")
            lines.append("")
    else:
        lines.append("  Sem recomendações de ações no momento.")
        lines.append("")

    if bargains:
        lines.append("<b>💎 Ações Baratas e Boas</b>")
        lines.append("")
        for b in bargains:
            lines.append(f"<b>{b.get('ticker','?')}</b>")
            lines.append(f"  📉 {b.get('motivo_desconto','')}")
            lines.append(f"  ✅ Valida: {b.get('valida_compra','')}")
            lines.append(f"  ❌ Invalida: {b.get('invalida_tese','')}")
            lines.append("")

    return "\n".join(lines)
