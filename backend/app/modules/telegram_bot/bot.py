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


def create_application(token: str) -> Application:
    """Build and configure the Telegram Application."""
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("analisa", cmd_analisa))
    app.add_handler(CommandHandler("regime", cmd_regime))
    app.add_handler(CommandHandler("ping", cmd_ping))
    return app
