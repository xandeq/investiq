"""Morning briefing and evening summary builders for the Telegram bot (Sprint 3).

These async functions are called by Celery tasks (tasks.py) and by the
/briefing command in bot.py. All external failures degrade graciously —
we never raise, we always return a (possibly partial) string.
"""
from __future__ import annotations

import logging
import os
from datetime import date, datetime, timezone

logger = logging.getLogger(__name__)


async def build_morning_briefing(redis_client) -> str:
    """Compile morning briefing: regime + macro + active A+ signals.

    Returns a formatted string suitable for Telegram HTML mode.
    Never raises — degrades gracefully if individual data sources fail.
    """
    from app.modules.chart_analyzer.analyzer import analyze
    from app.modules.market_data.service import MarketDataService
    from app.modules.signal_engine.scanner import get_active_signals

    today = date.today().strftime("%d/%m/%Y")
    lines: list[str] = [
        f"<b>Bom dia! Briefing InvestIQ — {today}</b>",
        "",
    ]

    # ── 1. Regime de mercado (BOVA11) ─────────────────────────────────────────
    try:
        brapi_token = os.environ.get("BRAPI_TOKEN", "")
        analysis = await analyze("BOVA11", brapi_token=brapi_token, redis_client=redis_client)
        if not analysis.get("error"):
            indicators = analysis.get("indicators", {})
            regime = indicators.get("regime", "N/D")
            rsi = indicators.get("rsi_14", "N/D")
            lines.append(f"<b>Mercado (BOVA11):</b> {regime} | RSI {rsi}")
        else:
            lines.append("<b>Mercado:</b> dados indisponíveis")
    except Exception as exc:
        logger.warning("briefing: regime fetch failed: %s", exc)
        lines.append("<b>Mercado:</b> dados indisponíveis")

    lines.append("")

    # ── 2. Macro ───────────────────────────────────────────────────────────────
    try:
        svc = MarketDataService(redis_client)
        macro = await svc.get_macro()
        selic = macro.selic or "N/D"
        cdi = macro.cdi or "N/D"
        ipca = macro.ipca or "N/D"
        lines.append(f"<b>Macro:</b> SELIC {selic}% | CDI {cdi}% | IPCA {ipca}%")
    except Exception as exc:
        logger.warning("briefing: macro fetch failed: %s", exc)
        lines.append("<b>Macro:</b> dados indisponíveis")

    lines.append("")

    # ── 3. Sinais A+ ativos ────────────────────────────────────────────────────
    try:
        signals = await get_active_signals(redis_client)
        if signals:
            lines.append(f"<b>Setups A+ ativos ({len(signals)}):</b>")
            for s in signals[:5]:  # cap at 5 to keep message concise
                setup = s.get("setup") or {}
                ticker = s.get("ticker", "?")
                pattern = setup.get("pattern", "N/D")
                direction = setup.get("direction", "N/D")
                entry = setup.get("entry", "?")
                stop = setup.get("stop", "?")
                rr = setup.get("rr", "?")
                lines.append(
                    f"  • <b>{ticker}</b> — {pattern} ({direction}) "
                    f"Entrada R${entry} Stop R${stop} R/R {rr}"
                )
        else:
            lines.append("<b>Sinais A+:</b> nenhum setup ativo agora")
    except Exception as exc:
        logger.warning("briefing: signals fetch failed: %s", exc)
        lines.append("<b>Sinais A+:</b> dados indisponíveis")

    lines += ["", "<i>InvestIQ — análise automatizada. Não é recomendação de investimento.</i>"]
    return "\n".join(lines)


async def build_evening_summary(redis_client, db_session=None) -> str:
    """Compile evening summary: open positions + today's closed outcomes.

    Returns a formatted string suitable for Telegram HTML mode.
    Never raises — degrades gracefully if individual data sources fail.
    """
    today_str = date.today().strftime("%d/%m/%Y")
    lines: list[str] = [
        f"<b>Resumo do dia — {today_str}</b>",
        "",
    ]

    # ── 1. Posições abertas (swing trade) ──────────────────────────────────────
    if db_session is not None:
        try:
            from sqlalchemy import select
            from app.modules.swing_trade.models import SwingTradeOperation

            result = await db_session.execute(
                select(SwingTradeOperation).where(
                    SwingTradeOperation.status == "open",
                    SwingTradeOperation.deleted_at.is_(None),
                )
            )
            ops = list(result.scalars().all())
            if ops:
                lines.append(f"<b>Posições abertas:</b> {len(ops)}")
                for op in ops[:5]:
                    lines.append(
                        f"  • <b>{op.ticker}</b> entrada R${float(op.entry_price):.2f}"
                        + (f" alvo R${float(op.target_price):.2f}" if op.target_price else "")
                    )
            else:
                lines.append("<b>Posições abertas:</b> nenhuma")
        except Exception as exc:
            logger.warning("evening_summary: swing trade fetch failed: %s", exc)
            lines.append("<b>Posições abertas:</b> dados indisponíveis")
    else:
        lines.append("<b>Posições abertas:</b> dados não disponíveis (sem sessão DB)")

    lines.append("")

    # ── 2. Outcomes fechados hoje ──────────────────────────────────────────────
    if db_session is not None:
        try:
            from sqlalchemy import select
            from app.modules.outcome_tracker.models import SignalOutcome

            today = date.today()
            result = await db_session.execute(
                select(SignalOutcome).where(
                    SignalOutcome.exit_date == today,
                    SignalOutcome.status.in_(["closed", "stopped"]),
                )
            )
            closed = list(result.scalars().all())
            if closed:
                r_values = [float(o.r_multiple) for o in closed if o.r_multiple is not None]
                mean_r = sum(r_values) / len(r_values) if r_values else 0
                lines.append(
                    f"<b>Outcomes fechados hoje:</b> {len(closed)} trades | "
                    f"Expectancy: {mean_r:+.2f}R"
                )
            else:
                lines.append("<b>Outcomes fechados hoje:</b> nenhum")
        except Exception as exc:
            logger.warning("evening_summary: outcomes fetch failed: %s", exc)
            lines.append("<b>Outcomes do dia:</b> dados indisponíveis")
    else:
        lines.append("<b>Outcomes do dia:</b> dados não disponíveis (sem sessão DB)")

    lines += ["", "<i>InvestIQ — resumo automatizado. Não é recomendação de investimento.</i>"]
    return "\n".join(lines)
