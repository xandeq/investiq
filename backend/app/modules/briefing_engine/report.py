"""Briefing Engine — main orchestrator.

Builds the full 14-section daily investment report by fetching all data
sources in parallel and generating LLM narratives for each section.

Usage:
    report = await build_full_report(redis_client)
    # report["telegram_chunks"] -> list of str (each < 4096 chars)
    # report["html"] -> full HTML for email
    # report["summary"] -> short version (executive summary only)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

BRT = timezone(timedelta(hours=-3))


def _chunk_message(text: str, max_len: int = 4000) -> list[str]:
    """Split a long message into chunks <= max_len, splitting at newlines."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    current = ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > max_len:
            if current:
                chunks.append(current.rstrip())
            current = line
        else:
            current += line
    if current.strip():
        chunks.append(current.rstrip())
    return chunks


async def build_full_report(redis_client=None) -> dict[str, Any]:
    """Build the complete daily investment report.

    Returns dict with:
      - sections: dict of section_name -> formatted text
      - telegram_chunks: list of str ready for send_message
      - summary: short executive summary string
      - generated_at: ISO timestamp
      - raw_data: all fetched data (for storage/debugging)
    """
    now = datetime.now(BRT)
    date_str = now.strftime("%d/%m/%Y")
    time_str = now.strftime("%H:%M")

    logger.info("briefing_engine: starting full report generation")

    # ── Fetch all data in parallel ───────────────────────────────────────────
    from app.modules.briefing_engine.sections.macro import fetch_macro_data
    from app.modules.briefing_engine.sections.news import fetch_and_rank_news
    from app.modules.briefing_engine.sections.signals import fetch_signals_data
    from app.modules.briefing_engine.sections.equities import fetch_equities_data
    from app.modules.briefing_engine.sections.fiis import fetch_fiis_data
    from app.modules.briefing_engine.sections.fixed_income import fetch_fixed_income_data

    async def _safe(coro, fallback):
        try:
            return await coro
        except Exception as exc:
            logger.warning("briefing_engine: section fetch failed: %s", exc)
            return fallback

    macro_task = asyncio.create_task(_safe(fetch_macro_data(), {}))
    news_task = asyncio.create_task(_safe(fetch_and_rank_news(48), []))
    signals_task = asyncio.create_task(_safe(fetch_signals_data(redis_client), {"equity": [], "crypto": []}))
    equities_task = asyncio.create_task(_safe(fetch_equities_data(redis_client), {"analyzed": []}))
    fiis_task = asyncio.create_task(_safe(fetch_fiis_data(redis_client), {"analyzed": []}))
    fi_task = asyncio.create_task(_safe(fetch_fixed_income_data(), {}))

    macro_data, news, signals, equities_data, fiis_data, fi_data = await asyncio.gather(
        macro_task, news_task, signals_task, equities_task, fiis_task, fi_task
    )

    logger.info("briefing_engine: data fetched — generating sections")

    # ── Generate LLM-enhanced sections in parallel ───────────────────────────
    from app.modules.briefing_engine.sections.equities import generate_equity_recommendations, generate_bargains
    from app.modules.briefing_engine.sections.fiis import generate_fii_recommendations, generate_fii_bargains
    from app.modules.briefing_engine.sections.risks import generate_risks
    from app.modules.briefing_engine.sections.action_plan import generate_action_plan

    eq_recs_task = asyncio.create_task(_safe(generate_equity_recommendations(equities_data), []))
    eq_bargains_task = asyncio.create_task(_safe(generate_bargains(equities_data), []))
    fii_recs_task = asyncio.create_task(_safe(generate_fii_recommendations(fiis_data), []))
    fii_bargains_task = asyncio.create_task(_safe(generate_fii_bargains(fiis_data), []))
    risks_task = asyncio.create_task(_safe(generate_risks(macro_data, news), []))

    eq_recs, eq_bargains, fii_recs, fii_bargains, risks = await asyncio.gather(
        eq_recs_task, eq_bargains_task, fii_recs_task, fii_bargains_task, risks_task
    )

    # Action plan needs outputs from previous steps
    plan = await _safe(
        generate_action_plan(macro_data, signals, risks, eq_recs, fii_recs),
        {"resumo_executivo": "Análise indisponível", "vies": "neutro", "risco_dia": "moderado",
         "tema_dominante": "mercado", "plano_conservador": "Renda fixa",
         "plano_moderado": "Ações de dividendos", "plano_agressivo": "Swing com stop",
         "plano_cripto": "Aguardar confirmação", "watchlist": []}
    )

    logger.info("briefing_engine: all sections ready — formatting")

    # ── Format sections ───────────────────────────────────────────────────────
    from app.modules.briefing_engine.sections.macro import format_macro_section
    from app.modules.briefing_engine.sections.news import format_news_section
    from app.modules.briefing_engine.sections.signals import format_signals_section
    from app.modules.briefing_engine.sections.equities import format_equities_section
    from app.modules.briefing_engine.sections.fiis import format_fiis_section
    from app.modules.briefing_engine.sections.fixed_income import format_fixed_income_section
    from app.modules.briefing_engine.sections.risks import format_risks_section
    from app.modules.briefing_engine.sections.action_plan import format_executive_summary, format_action_plan_section

    header = (
        f"<b>🤖 InvestIQ — Relatório Completo</b>\n"
        f"📅 {date_str} às {time_str} BRT\n"
        f"━━━━━━━━━━━━━━━━━━━━━━"
    )

    sections = {
        "header": header,
        "executive_summary": format_executive_summary(plan),
        "macro": format_macro_section(macro_data),
        "news": format_news_section(news),
        "signals": format_signals_section(signals),
        "equities": format_equities_section(eq_recs, eq_bargains),
        "fiis": format_fiis_section(fii_recs, fii_bargains),
        "fixed_income": format_fixed_income_section(fi_data, macro_data.get("selic")),
        "risks": format_risks_section(risks),
        "action_plan": format_action_plan_section(plan),
        "footer": (
            "\n<i>⚠️ Ferramenta de decisão pessoal, não recomendação formal de investimento. "
            "Confira preços no book antes de executar. "
            "Nunca opere sem stop definido.</i>"
        ),
    }

    # ── Build Telegram chunks (ordered sections) ─────────────────────────────
    section_order = [
        "header", "executive_summary", "macro", "news",
        "equities", "fiis", "fixed_income",
        "signals", "risks", "action_plan", "footer",
    ]

    all_chunks: list[str] = []
    for key in section_order:
        text = sections.get(key, "")
        if text:
            all_chunks.extend(_chunk_message(text + "\n\n", max_len=4000))

    # Short summary (for quick /briefing on-demand)
    summary = (
        f"{header}\n\n"
        f"{sections['executive_summary']}\n\n"
        f"<i>Use /briefing para relatório completo.</i>"
    )

    return {
        "sections": sections,
        "telegram_chunks": all_chunks,
        "summary": summary,
        "generated_at": now.isoformat(),
        "raw_data": {
            "macro": macro_data,
            "signals_count": len(signals.get("equity", [])),
            "news_count": len(news),
            "eq_recommendations": len(eq_recs),
            "fii_recommendations": len(fii_recs),
            "risks_count": len(risks),
        },
    }
