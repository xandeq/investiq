"""Signals section: A+ equity setups + crypto signals from Binance."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

_CRYPTO_UNIVERSE = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT"]


async def fetch_signals_data(redis_client=None) -> dict[str, Any]:
    """Fetch active equity A+ signals + crypto momentum signals."""
    # Equity signals from Redis cache
    equity_signals: list[dict] = []
    try:
        from app.modules.signal_engine.scanner import get_active_signals
        equity_signals = await get_active_signals(redis_client)
    except Exception as exc:
        logger.warning("signals: equity fetch failed: %s", exc)

    # Crypto signals: check Binance for momentum
    crypto_signals: list[dict] = []
    try:
        loop = asyncio.get_event_loop()
        from app.modules.market_data.adapters.binance_adapter import get_crypto_quotes
        quotes = await loop.run_in_executor(None, get_crypto_quotes)

        for symbol, data in quotes.items():
            if data is None:
                continue
            change = data.get("change_pct", 0)
            # Simple signal: momentum > 2% or < -2%
            if abs(change) >= 2.0:
                direction = "long" if change > 0 else "short"
                crypto_signals.append({
                    "ticker": symbol.replace("USDT", "/USDT"),
                    "direction": direction,
                    "change_pct": change,
                    "price": data["price"],
                    "volume_usd": data["volume_usd"],
                    "pattern": "momentum_24h",
                    "confidence": min(abs(change) / 10, 0.9),  # simple heuristic
                })
        crypto_signals.sort(key=lambda x: abs(x["change_pct"]), reverse=True)
    except Exception as exc:
        logger.warning("signals: crypto fetch failed: %s", exc)

    return {
        "equity": equity_signals,
        "crypto": crypto_signals,
    }


def format_signals_section(data: dict[str, Any]) -> str:
    """Format signals as Telegram HTML."""
    equity = data.get("equity", [])
    crypto = data.get("crypto", [])

    lines = []

    # Equity signals
    lines.append("<b>📊 Sinais Operacionais — Ações</b>")
    lines.append("")
    if equity:
        for s in equity:
            setup = s.get("setup") or {}
            ticker = s.get("ticker", "?")
            pattern = setup.get("pattern", "N/D")
            direction = setup.get("direction", "N/D")
            entry = setup.get("entry", "?")
            stop = setup.get("stop", "?")
            t1 = setup.get("target_1", "?")
            rr = setup.get("rr", "?")
            grade = setup.get("grade", s.get("grade", "?"))
            confidence = s.get("score", 0)

            dir_emoji = "🟢" if direction == "long" else "🔴"
            lines.append(f"{dir_emoji} <b>{ticker}</b> — {pattern} | Nota: {grade}")
            lines.append(f"  Entrada: R${entry} | Stop: R${stop} | Alvo 1: R${t1}")
            lines.append(f"  R/R: {rr} | Score: {confidence}")
            lines.append("")
    else:
        lines.append("  Sem setups A+ ativos no momento.")
        lines.append("  <i>Hoje sem A+ — foco em posições abertas.</i>")
        lines.append("")

    # Crypto signals
    lines.append("<b>₿ Sinais Operacionais — Cripto</b>")
    lines.append("")
    if crypto:
        for s in crypto[:4]:
            dir_emoji = "🟢" if s["direction"] == "long" else "🔴"
            change = s["change_pct"]
            sign = "+" if change >= 0 else ""
            lines.append(
                f"{dir_emoji} <b>{s['ticker']}</b> — {s['pattern']}\n"
                f"  Preço: US${s['price']:,.2f} | Var 24h: {sign}{change:.1f}%\n"
                f"  ⚠️ Entrar só com confirmação técnica + stop definido"
            )
            lines.append("")
    else:
        lines.append("  Sem momentum significativo em cripto agora.")
        lines.append("")

    return "\n".join(lines)
