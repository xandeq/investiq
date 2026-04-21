"""Macro section: Selic, IPCA, dólar, petróleo, BTC, S&P, Nasdaq, Ibovespa, VIX, Fear&Greed."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


async def fetch_macro_data() -> dict[str, Any]:
    """Fetch all macro data in parallel. Never raises — degrades gracefully."""
    loop = asyncio.get_event_loop()

    async def _safe(fn, *args):
        try:
            return await loop.run_in_executor(None, fn, *args)
        except Exception as exc:
            logger.warning("macro fetch %s failed: %s", fn.__name__, exc)
            return None

    from app.modules.market_data.adapters.stooq import get_global_indices
    from app.modules.market_data.adapters.binance_adapter import get_btc_price
    from app.modules.market_data.adapters.alternativeme import get_fear_greed

    indices_task = asyncio.create_task(_safe(get_global_indices))
    btc_task = asyncio.create_task(_safe(get_btc_price))
    fg_task = asyncio.create_task(_safe(get_fear_greed))

    indices, btc_price, fear_greed = await asyncio.gather(indices_task, btc_task, fg_task)

    # BCB macro is already in Redis via MarketDataService — fetch from there
    bcb_data: dict = {}
    try:
        from app.modules.market_data.service import MarketDataService
        import redis.asyncio as aioredis
        import os

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        r = aioredis.from_url(redis_url, decode_responses=True)
        try:
            svc = MarketDataService(r)
            macro = await svc.get_macro()
            bcb_data = {
                "selic": float(macro.selic) if macro.selic else None,
                "cdi": float(macro.cdi) if macro.cdi else None,
                "ipca": float(macro.ipca) if macro.ipca else None,
                "ptax": float(macro.ptax) if macro.ptax else None,
            }
        finally:
            await r.aclose()
    except Exception as exc:
        logger.warning("macro: BCB fetch failed: %s", exc)

    # Petróleo: WTI via Stooq
    try:
        from app.modules.market_data.adapters.stooq import _fetch
        oil_price = await loop.run_in_executor(None, _fetch, "cl.f")  # WTI crude futures
    except Exception:
        oil_price = None

    return {
        "selic": bcb_data.get("selic"),
        "cdi": bcb_data.get("cdi"),
        "ipca_12m": bcb_data.get("ipca"),
        "ptax": bcb_data.get("ptax"),
        "vix": indices.get("vix") if indices else None,
        "sp500": indices.get("sp500") if indices else None,
        "nasdaq": indices.get("nasdaq") if indices else None,
        "ibovespa": indices.get("ibovespa") if indices else None,
        "btc": btc_price,
        "oil_wti": oil_price,
        "fear_greed": fear_greed,
    }


def format_macro_section(data: dict[str, Any]) -> str:
    """Format macro data as Telegram HTML string."""
    def _fmt(val, prefix="", suffix="", decimals=2):
        if val is None:
            return "N/D"
        return f"{prefix}{val:,.{decimals}f}{suffix}"

    fg = data.get("fear_greed") or {}
    fg_str = f"{fg.get('value', '?')} — {fg.get('classification', '?')}" if fg else "N/D"

    lines = [
        "<b>📊 Painel Macro</b>",
        "",
        f"  • SELIC: {_fmt(data.get('selic'), suffix='% a.a.')}",
        f"  • IPCA 12m: {_fmt(data.get('ipca_12m'), suffix='%')}",
        f"  • Dólar (PTAX): {_fmt(data.get('ptax'), prefix='R$')}",
        f"  • Petróleo WTI: {_fmt(data.get('oil_wti'), prefix='US$')}",
        f"  • Bitcoin: {_fmt(data.get('btc'), prefix='US$', decimals=0)}",
        f"  • S&P 500: {_fmt(data.get('sp500'), decimals=0)}",
        f"  • Nasdaq 100: {_fmt(data.get('nasdaq'), decimals=0)}",
        f"  • Ibovespa: {_fmt(data.get('ibovespa'), decimals=0)}",
        f"  • VIX: {_fmt(data.get('vix'), decimals=1)}",
        f"  • Fear & Greed: {fg_str}",
    ]
    return "\n".join(lines)
