"""Telegram bot service helpers — message formatting and sending."""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger(__name__)


async def send_message(
    chat_id: str,
    text: str,
    token: str | None = None,
    parse_mode: str = "HTML",
) -> None:
    """Send a message to a Telegram chat via Bot API."""
    bot_token = token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — skipping send_message")
        return

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                logger.warning("Telegram send failed: %s %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        logger.error("Telegram send error: %s", exc)


async def format_analysis_message(analysis: dict) -> str:
    """Format a chart analysis dict into a human-readable Telegram HTML message."""
    ticker = analysis.get("ticker", "???")
    has_setup = analysis.get("has_setup", False)
    indicators = analysis.get("indicators", {})
    levels = analysis.get("levels", {})
    confluences = analysis.get("confluences", [])
    error = analysis.get("error")

    if error and not indicators:
        return f"<b>{ticker}</b>\n\nErro ao analisar: {error}"

    rsi = indicators.get("rsi_14", "N/D")
    regime = indicators.get("regime", "N/D")
    ema20 = indicators.get("ema20", "N/D")
    ema50 = indicators.get("ema50", "N/D")
    ema200 = indicators.get("ema200", "N/D")
    atr = indicators.get("atr", "N/D")
    vol_ratio = indicators.get("volume_ratio", "N/D")
    macd = indicators.get("macd", "N/D")

    lines = [
        f"<b>Analise Tecnica: {ticker}</b>",
        "",
        f"Regime: <b>{regime}</b>",
        f"RSI(14): {rsi} | ATR: {atr}",
        f"EMA20: {ema20} | EMA50: {ema50} | EMA200: {ema200}",
        f"Volume ratio: {vol_ratio}x | MACD: {macd}",
        "",
    ]

    if has_setup:
        s = analysis["setup"]
        lines += [
            f"<b>Setup: {s['pattern'].upper()} ({s['direction'].upper()})</b>",
            f"Entrada: R$ {s['entry']} | Stop: R$ {s['stop']}",
            f"Alvo 1: R$ {s['target_1']} | Alvo 2: R$ {s['target_2']}",
            f"R/R: {s['rr']}:1 | Nota: {s['grade']}",
            "",
        ]
    else:
        lines += ["Sem setup identificado no momento.", ""]

    if confluences:
        lines.append("<b>Confluencias:</b>")
        for c in confluences[:4]:
            lines.append(f"  - {c}")
        lines.append("")

    supports = levels.get("support", [])
    resistances = levels.get("resistance", [])
    if supports:
        lines.append(f"Suporte: {', '.join(str(p) for p in supports[:3])}")
    if resistances:
        lines.append(f"Resistencia: {', '.join(str(p) for p in resistances[:3])}")

    lines.append("")
    lines.append("<i>Analise tecnica automatizada. Nao e recomendacao de investimento.</i>")

    return "\n".join(lines)


async def send_setup_message(
    chat_id: str,
    analysis: dict,
    token: str | None = None,
) -> None:
    """Format and send a full analysis message to a chat."""
    text = await format_analysis_message(analysis)
    await send_message(chat_id, text, token=token)
