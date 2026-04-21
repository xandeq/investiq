"""FIIs section: recommended FIIs and bargains using BRAPI data."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_FII_UNIVERSE = [
    "KNCR11", "HGLG11", "XPML11", "MXRF11", "KNRI11",
    "IRDM11", "BCFF11", "XPCA11", "BTLG11", "VISC11",
]

_SYSTEM_FIIS = """Você é um especialista em FIIs (Fundos de Investimento Imobiliário) brasileiro.
Dado dados técnicos de FIIs, gere recomendações.
Para cada FII retorne JSON: ticker, segmento, tese (1 linha), faixa_entrada, risco, nota (0-10), destaque.
Seja direto. Máximo 5 FIIs. Retorne APENAS JSON array."""


async def fetch_fiis_data(redis_client=None) -> dict[str, Any]:
    """Fetch technical + basic data for FII universe."""
    brapi_token = os.environ.get("BRAPI_TOKEN", "")

    sem = asyncio.Semaphore(3)  # limit concurrent BRAPI calls to avoid 429

    async def _analyze(ticker: str):
        async with sem:
            try:
                await asyncio.sleep(0.3)  # small stagger
                from app.modules.chart_analyzer.analyzer import analyze
                return await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
            except Exception:
                return None

    tasks = [_analyze(t) for t in _FII_UNIVERSE]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    analyzed = []
    for ticker, result in zip(_FII_UNIVERSE, results):
        if isinstance(result, dict) and not result.get("error"):
            analyzed.append({"ticker": ticker, "analysis": result})

    return {"analyzed": analyzed}


async def generate_fii_recommendations(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Generate FII recommendations via LLM."""
    analyzed = data.get("analyzed", [])
    if not analyzed:
        return []

    summaries = []
    for item in analyzed:
        t = item["ticker"]
        a = item["analysis"]
        ind = a.get("indicators", {})
        summaries.append(
            f"- {t}: regime={ind.get('regime','?')}, RSI={ind.get('rsi_14','?')}, "
            f"EMA20={ind.get('ema20','?')}, confluências={len(a.get('confluences',[]))}"
        )

    prompt = "Analise os seguintes FIIs e recomende os 3-5 melhores para carteira agora:\n\n" + "\n".join(summaries)

    try:
        import json
        from app.modules.ai.provider import call_llm
        raw = await call_llm(prompt, system=_SYSTEM_FIIS, tier="paid", max_tokens=700)
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            return json.loads(raw[start:end])[:5]
    except Exception as exc:
        logger.warning("fiis: LLM recommendation failed: %s", exc)

    # Fallback
    top = sorted(analyzed, key=lambda x: len(x["analysis"].get("confluences", [])), reverse=True)[:3]
    return [
        {
            "ticker": item["ticker"],
            "segmento": "FII",
            "tese": f"{len(item['analysis'].get('confluences',[]))} confluências técnicas",
            "faixa_entrada": f"R${item['analysis']['indicators'].get('ema20','?')}",
            "risco": "médio",
            "nota": 7.0,
            "destaque": "técnico",
        }
        for item in top
    ]


async def generate_fii_bargains(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Identify FIIs trading below fair value (RSI oversold)."""
    analyzed = data.get("analyzed", [])
    bargains = []
    for item in analyzed:
        a = item["analysis"]
        ind = a.get("indicators", {})
        rsi = ind.get("rsi_14", 50)
        if rsi < 38:
            bargains.append({
                "ticker": item["ticker"],
                "motivo_desconto": f"RSI={rsi:.0f} — sobrevendido",
                "valida_compra": "Recuperação acima de RSI 40 com volume",
                "invalida_tese": "Piora de vacância ou inadimplência reportada",
                "yield_sustentavel": "Verificar última distribuição",
            })
    return bargains[:3]


def format_fiis_section(recommendations: list[dict], bargains: list[dict]) -> str:
    """Format FIIs section as Telegram HTML."""
    lines = ["<b>🏢 FIIs Recomendados Agora</b>", ""]

    if recommendations:
        for r in recommendations:
            lines.append(f"<b>{r.get('ticker','?')}</b> ⭐{r.get('nota','?')} | {r.get('segmento','FII')}")
            lines.append(f"  📌 {r.get('tese','')}")
            lines.append(f"  💰 Entrada: {r.get('faixa_entrada','?')} | Risco: {r.get('risco','?')}")
            lines.append("")
    else:
        lines.append("  Sem recomendações de FIIs no momento.")
        lines.append("")

    if bargains:
        lines.append("<b>💎 FIIs Baratos e Bons</b>")
        lines.append("")
        for b in bargains:
            lines.append(f"<b>{b.get('ticker','?')}</b>")
            lines.append(f"  📉 {b.get('motivo_desconto','')}")
            lines.append(f"  ✅ Valida: {b.get('valida_compra','')}")
            lines.append(f"  ❌ Invalida: {b.get('invalida_tese','')}")
            lines.append(f"  💰 {b.get('yield_sustentavel','')}")
            lines.append("")

    return "\n".join(lines)
