"""FIIs section: recommended FIIs and bargains using BRAPI data."""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Curated FII universe — all major liquid FIIs across segments
_FII_UNIVERSE_DEFAULT = [
    "KNCR11", "HGLG11", "XPML11", "MXRF11", "KNRI11",
    "IRDM11", "BCFF11", "XPCA11", "BTLG11", "VISC11",
    "HCTR11", "BRCO11", "XPLG11", "LVBI11", "RZTR11",
    "HGRE11", "RBRP11", "BRCR11", "HFOF11", "RBRF11",
    "HSML11", "MALL11", "VISC11", "GGRC11",
]


async def _get_dynamic_fii_universe(redis_client, fallback: list[str]) -> list[str]:
    """Return FIIs ranked by DY (highest first) using Redis fundamentals cache.

    Falls back to the default curated list if Redis is unavailable or empty.
    This ensures the briefing recommends FIIs that are actually paying well today.
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
                dy = fund.get("dy")
                if dy is not None:
                    # Normalise: BRAPI may return 0.08 (ratio) or 8.0 (percentage)
                    dy_pct = dy * 100 if abs(dy) < 1 else dy
                    dy_scores.append((ticker, dy_pct))
                else:
                    dy_scores.append((ticker, 0.0))
        except Exception:
            dy_scores.append((ticker, 0.0))

    if not dy_scores:
        return fallback

    # Sort descending by DY; tickers without data go last
    dy_scores.sort(key=lambda x: x[1], reverse=True)
    ranked = [t for t, _ in dy_scores]
    logger.debug("FII briefing universe ranked by DY: %s", ranked[:5])
    return ranked

_SYSTEM_FIIS = """Você é um especialista em FIIs (Fundos de Investimento Imobiliário) brasileiro.
Dado dados técnicos de FIIs, gere recomendações.
Para cada FII retorne JSON: ticker, segmento, tese (1 linha), faixa_entrada, risco, nota (0-10), destaque.
Seja direto. Máximo 5 FIIs. Retorne APENAS JSON array."""


async def fetch_fiis_data(redis_client=None) -> dict[str, Any]:
    """Fetch technical + fundamental data for FII universe.

    Universe is ranked by real DY from Redis fundamentals cache (Startup plan),
    so the briefing always covers the highest-yielding FIIs first.
    """
    brapi_token = os.environ.get("BRAPI_TOKEN", "")

    # Dynamic universe: top FIIs by DY from Redis, fallback to curated list
    universe = await _get_dynamic_fii_universe(redis_client, _FII_UNIVERSE_DEFAULT)

    sem = asyncio.Semaphore(3)  # limit concurrent BRAPI calls

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
            item = {"ticker": ticker, "analysis": result}
            # Enrich with DY/P/VP from Redis
            if redis_client is not None:
                try:
                    raw = await redis_client.get(f"market:fundamentals:{ticker}")
                    if raw:
                        if isinstance(raw, bytes):
                            raw = raw.decode()
                        fund = json.loads(raw)
                        dy = fund.get("dy")
                        item["dy_pct"] = (dy * 100 if dy and abs(dy) < 1 else dy) if dy else None
                        item["pvp"] = fund.get("pvp")
                except Exception:
                    item["dy_pct"] = None
                    item["pvp"] = None
            analyzed.append(item)

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
        line = (
            f"- {t}: regime={ind.get('regime','?')}, RSI={ind.get('rsi_14','?')}, "
            f"EMA20={ind.get('ema20','?')}, confluências={len(a.get('confluences',[]))}"
        )
        # Add real DY and P/VP if available
        fund_parts = []
        if item.get("dy_pct"):
            fund_parts.append(f"DY={item['dy_pct']:.1f}%")
        if item.get("pvp"):
            fund_parts.append(f"P/VP={item['pvp']:.2f}")
        if fund_parts:
            line += " | " + " ".join(fund_parts)
        summaries.append(line)

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
