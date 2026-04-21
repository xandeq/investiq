"""Telegram bot — bidirectional using python-telegram-bot v21+."""
from __future__ import annotations

import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from app.modules.chart_analyzer.analyzer import analyze
from app.modules.telegram_bot.service import format_analysis_message

logger = logging.getLogger(__name__)

_SYSTEM_TESE = (
    "Voce e um analista tecnico experiente de acoes brasileiras (B3). "
    "Escreva uma tese de trade concisa (3-5 linhas) baseada nos dados fornecidos. "
    "Seja direto, objetivo e use linguagem profissional. "
    "Nao faca recomendacao explicita de compra ou venda."
)


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /start."""
    await update.message.reply_text(
        "InvestIQ Bot ativo.\n\n"
        "Comandos:\n"
        "/analisa <TICKER> — analise tecnica de uma acao\n"
        "/regime — diagnostico do mercado atual (BOVA11)\n"
        "/sinais — setups A+ ativos agora\n"
        "/carteira — posicoes abertas + P&L + outcomes (30d)\n"
        "/briefing — briefing imediato do mercado\n"
        "/ping — verifica se o bot esta online"
    )


async def cmd_analisa(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /analisa <TICKER>."""
    if not context.args:
        await update.message.reply_text("Uso: /analisa <TICKER>\nEx: /analisa BBSE3")
        return

    ticker = context.args[0].upper()
    await update.message.reply_text(f"Analisando {ticker}...")

    brapi_token = os.environ.get("BRAPI_TOKEN", "")
    analysis = await analyze(ticker, brapi_token=brapi_token)

    msg = await format_analysis_message(analysis)

    # Add AI thesis if no error
    if not analysis.get("error"):
        try:
            from app.modules.ai.provider import call_llm

            indicators = analysis.get("indicators", {})
            setup = analysis.get("setup")
            prompt = (
                f"Acao: {ticker}\n"
                f"Regime: {indicators.get('regime', 'N/D')}\n"
                f"RSI: {indicators.get('rsi_14', 'N/D')}\n"
                f"EMA20: {indicators.get('ema20', 'N/D')} | EMA50: {indicators.get('ema50', 'N/D')}\n"
                f"Volume ratio: {indicators.get('volume_ratio', 'N/D')}x\n"
            )
            if setup:
                prompt += (
                    f"Setup: {setup['pattern']} ({setup['direction']})\n"
                    f"Entrada: {setup['entry']} | Stop: {setup['stop']} | "
                    f"Alvo1: {setup['target_1']} | R/R: {setup['rr']}\n"
                )
            tese = await call_llm(prompt, system=_SYSTEM_TESE, tier="free", max_tokens=200)
            msg += f"\n\n<b>Tese:</b>\n{tese}"
        except Exception as exc:
            logger.warning("LLM tese failed for %s: %s", ticker, exc)

    # Send PNG chart if a setup was detected
    if analysis.get("has_setup") and not analysis.get("error"):
        try:
            import asyncio
            from app.modules.chart_analyzer.analyzer import fetch_ohlcv
            from app.modules.chart_analyzer.chart_image import generate_chart_png

            df = await asyncio.get_event_loop().run_in_executor(
                None, fetch_ohlcv, ticker, brapi_token
            )
            png_bytes = generate_chart_png(df, ticker, analysis.get("setup"))
            if png_bytes:
                await update.message.reply_photo(photo=png_bytes, caption=msg[:1024])
                return
        except Exception as exc:
            logger.warning("cmd_analisa: chart PNG failed for %s (%s) — falling back to text", ticker, exc)

    await update.message.reply_html(msg)


async def cmd_regime(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /regime — uses BOVA11 as Ibov proxy."""
    await update.message.reply_text("Verificando regime de mercado (BOVA11)...")

    brapi_token = os.environ.get("BRAPI_TOKEN", "")
    analysis = await analyze("BOVA11", brapi_token=brapi_token)

    if analysis.get("error"):
        await update.message.reply_text(f"Erro ao consultar BOVA11: {analysis['error']}")
        return

    indicators = analysis.get("indicators", {})
    regime = indicators.get("regime", "N/D")
    ema50 = indicators.get("ema50", "N/D")
    rsi = indicators.get("rsi_14", "N/D")
    confluences = analysis.get("confluences", [])

    lines = [
        "<b>Regime de Mercado — BOVA11</b>",
        "",
        f"Regime: <b>{regime}</b>",
        f"RSI: {rsi} | EMA50: R$ {ema50}",
    ]
    if confluences:
        lines += ["", "<b>Sinais:</b>"] + [f"  - {c}" for c in confluences[:4]]

    lines += ["", "<i>Baseado em BOVA11 como proxy do Ibovespa.</i>"]
    await update.message.reply_html("\n".join(lines))


async def cmd_ping(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /ping."""
    await update.message.reply_text("pong — InvestIQ Bot online")


async def cmd_carteira(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /carteira — open positions + P&L + outcome summary."""
    await update.message.reply_text("Buscando carteira...")

    from datetime import date
    import redis.asyncio as aioredis

    redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    today = date.today().strftime("%d/%m/%Y")

    lines = [f"<b>Carteira — {today}</b>", ""]

    # Fetch open swing trade operations
    try:
        from sqlalchemy import text
        from app.core.db import async_session_factory

        async with async_session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT ticker, entry_price, target_price, quantity "
                    "FROM swing_trade_operations "
                    "WHERE status = 'open' AND deleted_at IS NULL "
                    "ORDER BY ticker"
                )
            )
            ops = result.fetchall()

        if ops:
            lines.append(f"<b>Posições abertas:</b> {len(ops)}")

            # Try to enrich with current prices
            try:
                redis_client = aioredis.from_url(redis_url, decode_responses=True)
                try:
                    from app.modules.market_data.service import MarketDataService

                    svc = MarketDataService(redis_client)
                    for row in ops[:5]:
                        ticker, entry_price, target_price, qty = (
                            row[0], float(row[1]), row[2], float(row[3])
                        )
                        try:
                            quote = await svc.get_quote(ticker)
                            if not quote.data_stale and quote.regularMarketPrice:
                                current = float(quote.regularMarketPrice)
                                pnl_pct = (current - entry_price) / entry_price * 100
                                pnl_sign = "+" if pnl_pct >= 0 else ""
                                lines.append(
                                    f"  • <b>{ticker}</b> entrada R${entry_price:.2f} | "
                                    f"atual R${current:.2f} | P&L: {pnl_sign}{pnl_pct:.1f}%"
                                )
                                continue
                        except Exception:
                            pass
                        lines.append(
                            f"  • <b>{ticker}</b> entrada R${entry_price:.2f}"
                            + (f" alvo R${float(target_price):.2f}" if target_price else "")
                        )
                finally:
                    try:
                        await redis_client.aclose()
                    except Exception:
                        pass
            except Exception as exc:
                logger.warning("cmd_carteira: failed to enrich with prices: %s", exc)
                for row in ops[:5]:
                    ticker, entry_price, target_price = row[0], float(row[1]), row[2]
                    lines.append(
                        f"  • <b>{ticker}</b> entrada R${entry_price:.2f}"
                        + (f" alvo R${float(target_price):.2f}" if target_price else "")
                    )
        else:
            lines.append("<b>Posições abertas:</b> nenhuma")
    except Exception as exc:
        logger.warning("cmd_carteira: swing trade fetch failed: %s", exc)
        lines.append("<b>Posições abertas:</b> dados indisponíveis")

    lines.append("")

    # Fetch outcomes summary (last 30 days)
    try:
        from sqlalchemy import text
        from app.core.db import async_session_factory
        from datetime import timedelta, date as dt_date

        cutoff = (dt_date.today() - timedelta(days=30)).isoformat()
        async with async_session_factory() as db:
            result = await db.execute(
                text(
                    "SELECT COUNT(*), AVG(r_multiple) "
                    "FROM signal_outcomes "
                    "WHERE status = 'closed' AND exit_date >= :cutoff"
                ),
                {"cutoff": cutoff},
            )
            row = result.fetchone()

        count = int(row[0] or 0)
        expectancy = float(row[1]) if row[1] is not None else None
        if count > 0 and expectancy is not None:
            lines.append(
                f"<b>Outcomes fechados (30d):</b> {count} trades | "
                f"Expectancy: {expectancy:+.2f}R"
            )
        elif count == 0:
            lines.append("<b>Outcomes (30d):</b> sem trades fechados")
    except Exception as exc:
        logger.warning("cmd_carteira: outcomes fetch failed: %s", exc)
        lines.append("<b>Outcomes (30d):</b> dados indisponíveis")

    await update.message.reply_html("\n".join(lines))


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /briefing — force an immediate morning briefing."""
    await update.message.reply_text("Compilando briefing...")

    try:
        import redis.asyncio as aioredis
        from app.modules.telegram_bot.briefings import build_morning_briefing

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            message = await build_morning_briefing(redis_client)
        finally:
            try:
                await redis_client.aclose()
            except Exception:
                pass

        await update.message.reply_html(message)
    except Exception as exc:
        logger.error("cmd_briefing: failed: %s", exc)
        await update.message.reply_text(f"Erro ao compilar briefing: {exc}")


async def cmd_sinais(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handler for /sinais — lista setups A+ ativos agora."""
    await update.message.reply_text("Buscando setups A+...")

    try:
        import redis.asyncio as aioredis
        from app.modules.signal_engine.scanner import get_active_signals

        redis_url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
        redis_client = aioredis.from_url(redis_url, decode_responses=True)
        try:
            signals = await get_active_signals(redis_client)
        finally:
            try:
                await redis_client.aclose()
            except Exception:
                pass
    except Exception as exc:
        logger.warning("cmd_sinais: failed to fetch signals: %s", exc)
        signals = []

    if not signals:
        await update.message.reply_text(
            "Hoje sem setups A+ — mercado nao oferece oportunidade agora."
        )
        return

    lines = ["<b>Setups A+ Ativos</b>", ""]
    for s in signals:
        setup = s.get("setup") or {}
        ticker = s.get("ticker", "?")
        pattern = setup.get("pattern", "N/D")
        direction = setup.get("direction", "N/D")
        entry = setup.get("entry", "?")
        stop = setup.get("stop", "?")
        rr = setup.get("rr", "?")
        lines.append(
            f"<b>{ticker}</b> — {pattern} ({direction})\n"
            f"  Entrada: R${entry} | Stop: R${stop} | R/R: {rr}"
        )

    await update.message.reply_html("\n".join(lines))


def create_application(token: str) -> Application:
    """Build and configure the Telegram Application."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analisa", cmd_analisa))
    app.add_handler(CommandHandler("regime", cmd_regime))
    app.add_handler(CommandHandler("ping", cmd_ping))
    app.add_handler(CommandHandler("sinais", cmd_sinais))
    app.add_handler(CommandHandler("carteira", cmd_carteira))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    return app
