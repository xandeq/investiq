"""Swing Trade Copilot — intelligent engine that delivers ready-to-trade decisions.

Produces two sets of picks:
  1. swing_picks   — top 5 momentum/technical setups with entry, stop, gain, thesis
  2. dividend_plays — cheap dividend stocks to enter now and hold weeks/months

Each pick includes everything needed to open the operation with one click.
Results are cached in Redis (TTL 4h) to avoid hammering BRAPI.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CACHE_KEY = "swing_trade:copilot:v2"
_CACHE_TTL = 4 * 3600  # 4 hours

# Extended universe: liquid large/mid caps covering sectors
COPILOT_UNIVERSE = [
    # Financials
    "ITUB4", "BBDC4", "BBAS3", "SANB11", "B3SA3", "BBSE3", "IRBR3",
    # Energy / Commodities
    "PETR4", "VALE3", "PRIO3", "UGPA3", "CSAN3", "SUZB3", "KLBN11",
    # Utilities / Dividend players
    "EGIE3", "TAEE11", "CMIG4", "ENEV3", "SBSP3", "SAPR11",
    # Consumer / Retail
    "ABEV3", "BRFS3", "RENT3", "LREN3", "PCAR3",
    # Tech / Services
    "WEGE3", "TOTS3", "TOTVS3", "LWSA3",
    # Healthcare / Others
    "HAPV3", "RDOR3", "EMBR3",
]

_SYSTEM_SWING = """Você é um trader de swing trade brasileiro experiente.
Analise os dados técnicos das ações e selecione os 5 melhores setups para swing trade agora.
Para cada ação retorne JSON com:
- ticker (str)
- tese (str: 2 linhas máximo — por que entrar agora e o que esperar)
- entrada (float: preço ideal de entrada — pode ser o atual ou próximo suporte)
- stop_loss (float: preço de stop obrigatório — abaixo do suporte)
- stop_gain (float: alvo de saída — suporte/resistência à frente)
- rr (float: relação risco/retorno)
- prazo (str: "dias", "semanas" ou "meses")
- confianca (str: "alta", "média" ou "baixa")
- motivo (str: 1 linha — gatilho principal que justifica a entrada hoje)

Critérios prioritários: RSI não sobrecomprado, tendência de alta ou recuperação, volume acima da média, suporte técnico próximo.
Retorne APENAS JSON array com exatamente 5 itens."""

_SYSTEM_DIVIDENDS = """Você é um especialista em ações de dividendos brasileiro.
Analise os dados técnicos e de dividendos das ações e selecione os 3-5 melhores para comprar agora e segurar semanas/meses.
Para cada ação retorne JSON com:
- ticker (str)
- tese (str: 2 linhas — por que está barata e qual o potencial de valorização + dividendos)
- entrada (float: preço atual ou até onde aceitar pagar)
- stop_loss (float: preço que invalida a tese)
- alvo_preco (float: preço alvo em 3-6 meses)
- dy_estimado (str: ex "8,5% a.a." — yield de dividendos estimado)
- prazo_sugerido (str: ex "2-4 meses")
- motivo_desconto (str: 1 linha — por que está mais barata que o normal)

Foco: ações com DY > 6%, RSI < 50 (não sobrecomprada), bons fundamentos.
Retorne APENAS JSON array com 3-5 itens."""


async def _analyze_with_semaphore(sem: asyncio.Semaphore, ticker: str, brapi_token: str, redis_client: Any) -> dict | None:
    async with sem:
        try:
            await asyncio.sleep(0.5)  # stagger to avoid BRAPI 429
            from app.modules.chart_analyzer.analyzer import analyze
            result = await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
            if result and not result.get("error"):
                return {"ticker": ticker, **result}
            # If 429/rate-limit error — wait and retry once
            if result and result.get("error") and "429" in str(result.get("error", "")):
                logger.info("copilot: 429 on %s — retrying after 6s", ticker)
                await asyncio.sleep(6)
                result = await analyze(ticker, brapi_token=brapi_token, redis_client=redis_client)
                if result and not result.get("error"):
                    return {"ticker": ticker, **result}
        except Exception as exc:
            logger.debug("copilot: analyze failed for %s: %s", ticker, exc)
    return None


async def _get_dy(ticker: str, redis_client: Any) -> float | None:
    """Fetch DY from Redis fundamentals cache."""
    if redis_client is None:
        return None
    try:
        raw = await redis_client.get(f"market:fundamentals:{ticker}")
        if raw:
            if isinstance(raw, bytes):
                raw = raw.decode()
            data = json.loads(raw)
            dy = data.get("dividend_yield")
            return float(dy) if dy is not None else None
    except Exception:
        pass
    return None


async def build_copilot_picks(redis_client=None, force: bool = False) -> dict[str, Any]:
    """Main entry point — returns copilot picks with cache."""
    # Try cache first
    if not force and redis_client is not None:
        try:
            raw = await redis_client.get(_CACHE_KEY)
            if raw:
                if isinstance(raw, bytes):
                    raw = raw.decode()
                cached = json.loads(raw)
                cached["from_cache"] = True
                return cached
        except Exception as exc:
            logger.warning("copilot: cache read failed: %s", exc)

    brapi_token = os.environ.get("BRAPI_TOKEN", "")
    sem = asyncio.Semaphore(2)  # conservative — BRAPI free plan allows ~2 concurrent

    logger.info("copilot: scanning %d tickers", len(COPILOT_UNIVERSE))
    tasks = [_analyze_with_semaphore(sem, t, brapi_token, redis_client) for t in COPILOT_UNIVERSE]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    analyzed = [r for r in results if isinstance(r, dict)]
    logger.info("copilot: %d tickers analyzed successfully", len(analyzed))

    if not analyzed:
        return _empty_response("Sem dados técnicos disponíveis no momento (BRAPI indisponível).")

    # Enrich with DY
    dy_tasks = [_get_dy(a["ticker"], redis_client) for a in analyzed]
    dy_values = await asyncio.gather(*dy_tasks, return_exceptions=True)
    for a, dy in zip(analyzed, dy_values):
        a["dy"] = dy if isinstance(dy, float) else None

    swing_picks = await _generate_swing_picks(analyzed)
    dividend_plays = await _generate_dividend_plays(analyzed)

    result = {
        "swing_picks": swing_picks,
        "dividend_plays": dividend_plays,
        "universe_scanned": len(analyzed),
        "from_cache": False,
    }

    # Cache result
    if redis_client is not None:
        try:
            await redis_client.setex(_CACHE_KEY, _CACHE_TTL, json.dumps(result, default=str))
        except Exception as exc:
            logger.warning("copilot: cache write failed: %s", exc)

    return result


async def _generate_swing_picks(analyzed: list[dict]) -> list[dict]:
    """Generate top 5 swing picks via LLM, with technical fallback."""
    # Sort candidates: prefer trending_up, high confluences, RSI 35-65
    candidates = sorted(
        analyzed,
        key=lambda a: (
            1 if "up" in str(a.get("indicators", {}).get("regime", "")).lower() else 0,
            len(a.get("confluences", [])),
            -abs(a.get("indicators", {}).get("rsi_14", 50) - 50),
        ),
        reverse=True,
    )[:15]

    summaries = _build_summaries(candidates)
    prompt = (
        "Dados técnicos das ações abaixo. Selecione os 5 melhores setups para swing trade agora:\n\n"
        + summaries
    )

    try:
        from app.modules.ai.provider import call_llm
        raw = await call_llm(prompt, system=_SYSTEM_SWING, tier="paid", max_tokens=1200)
        picks = _extract_json_array(raw)
        if picks and len(picks) >= 3:
            return picks[:5]
    except Exception as exc:
        logger.warning("copilot: swing LLM failed: %s", exc)

    return _fallback_swing_picks(candidates)


async def _generate_dividend_plays(analyzed: list[dict]) -> list[dict]:
    """Generate dividend play recommendations via LLM."""
    # Filter: DY > 4% OR known dividend payers
    KNOWN_DIVIDEND = {"BBSE3", "TAEE11", "EGIE3", "CMIG4", "ITUB4", "BBAS3", "ABEV3", "KLBN11", "SAPR11", "SANB11"}
    candidates = [
        a for a in analyzed
        if (a.get("dy") and a["dy"] > 4.0)
        or a["ticker"] in KNOWN_DIVIDEND
    ]

    if not candidates:
        candidates = analyzed[:10]

    # Prefer oversold (RSI < 50) and not in downtrend
    candidates = sorted(
        candidates,
        key=lambda a: (
            1 if a.get("dy") and a["dy"] > 6 else 0,
            -a.get("indicators", {}).get("rsi_14", 60),
        ),
        reverse=True,
    )[:10]

    summaries = _build_summaries(candidates, include_dy=True)
    prompt = (
        "Dados técnicos e de dividendos das ações abaixo. Selecione as 3-5 melhores para comprar agora e segurar semanas/meses:\n\n"
        + summaries
    )

    try:
        from app.modules.ai.provider import call_llm
        raw = await call_llm(prompt, system=_SYSTEM_DIVIDENDS, tier="paid", max_tokens=1000)
        picks = _extract_json_array(raw)
        if picks and len(picks) >= 2:
            return picks[:5]
    except Exception as exc:
        logger.warning("copilot: dividend LLM failed: %s", exc)

    return _fallback_dividend_plays(candidates)


def _build_summaries(items: list[dict], include_dy: bool = False) -> str:
    lines = []
    for a in items:
        ind = a.get("indicators", {})
        setup = a.get("setup") or {}
        confluences = a.get("confluences", [])
        rsi = ind.get("rsi_14", "?")
        regime = ind.get("regime", "?")
        vol = ind.get("volume_ratio", "?")
        ema20 = ind.get("ema20", "?")
        dy = a.get("dy")

        line = (
            f"- {a['ticker']}: regime={regime}, RSI={rsi}, "
            f"EMA20={ema20}, vol_ratio={vol}, "
            f"confluências={len(confluences)}, setup={'sim' if setup.get('pattern') else 'não'}"
        )
        if setup.get("entry"):
            line += f", entry={setup['entry']:.2f}, stop={setup['stop']:.2f}, alvo={setup.get('target_1', '?')}"
        if include_dy and dy:
            line += f", DY={dy:.1f}%"
        lines.append(line)
    return "\n".join(lines)


def _extract_json_array(raw: str) -> list | None:
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start:end])
        except json.JSONDecodeError:
            pass
    return None


def _fallback_swing_picks(candidates: list[dict]) -> list[dict]:
    picks = []
    for a in candidates[:5]:
        ind = a.get("indicators", {})
        setup = a.get("setup") or {}
        entry = setup.get("entry") or ind.get("ema20") or 0
        atr = ind.get("atr") or (entry * 0.02)
        stop = setup.get("stop") or round(entry - 1.8 * atr, 2)
        target = setup.get("target_1") or round(entry + 3.0 * atr, 2)
        rr = round((target - entry) / (entry - stop), 2) if entry > stop else 2.0
        picks.append({
            "ticker": a["ticker"],
            "tese": f"Setup técnico — {len(a.get('confluences', []))} confluências. Regime: {ind.get('regime', '?')}.",
            "entrada": round(entry, 2),
            "stop_loss": round(stop, 2),
            "stop_gain": round(target, 2),
            "rr": rr,
            "prazo": "semanas",
            "confianca": "média",
            "motivo": f"RSI={ind.get('rsi_14', '?')} — volume {ind.get('volume_ratio', '?')}x média",
        })
    return picks


def _fallback_dividend_plays(candidates: list[dict]) -> list[dict]:
    plays = []
    for a in candidates[:3]:
        ind = a.get("indicators", {})
        entry = ind.get("ema20") or 0
        atr = ind.get("atr") or (entry * 0.02)
        stop = round(entry - 2 * atr, 2)
        alvo = round(entry * 1.12, 2)
        dy = a.get("dy")
        plays.append({
            "ticker": a["ticker"],
            "tese": f"Pagadora de dividendos{f' (DY {dy:.1f}%)' if dy else ''} com preço atrativo. Segurar para receber rendimentos.",
            "entrada": round(entry, 2),
            "stop_loss": round(stop, 2),
            "alvo_preco": alvo,
            "dy_estimado": f"{dy:.1f}% a.a." if dy else "verificar",
            "prazo_sugerido": "2-4 meses",
            "motivo_desconto": f"RSI={ind.get('rsi_14', '?')} — abaixo da média histórica recente",
        })
    return plays


def _empty_response(reason: str) -> dict:
    return {
        "swing_picks": [],
        "dividend_plays": [],
        "universe_scanned": 0,
        "from_cache": False,
        "error": reason,
    }
