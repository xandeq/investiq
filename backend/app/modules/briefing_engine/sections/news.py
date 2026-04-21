"""News section: fetch from CVM RSS + Finnhub, rank by LLM relevance."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)

_RANK_SYSTEM = """Você é um analista de investimentos sênior. Recebeu uma lista de notícias de mercado.
Tarefa: ranquear as notícias da MAIS para a MENOS relevante para decisões de investimento em ações BR, FIIs e renda fixa.
Para cada notícia, retorne exatamente 5 campos em formato JSON array:
- manchete (string)
- por_que_importa (1 linha)
- impacto_provavel (1 linha: positivo/negativo/neutro + contexto)
- ativos_afetados (lista de tickers ou setores)
- acao_sugerida (1 linha objetiva)

Retorne APENAS o JSON array, sem texto fora dele. Máximo 9 itens."""


async def fetch_and_rank_news(hours_back: int = 48) -> list[dict[str, Any]]:
    """Fetch news from all sources and rank by investment relevance via LLM."""
    loop = asyncio.get_event_loop()

    async def _safe(fn, *args):
        try:
            return await loop.run_in_executor(None, fn, *args) or []
        except Exception as exc:
            logger.warning("news fetch %s failed: %s", fn.__name__, exc)
            return []

    from app.modules.news.adapters.cvm_rss import get_cvm_news
    from app.modules.news.adapters.gnews_adapter import get_financial_news
    from app.modules.news.adapters.finnhub_adapter import get_market_news

    cvm_task = asyncio.create_task(_safe(get_cvm_news, hours_back))
    gnews_task = asyncio.create_task(_safe(get_financial_news, hours_back))
    finnhub_task = asyncio.create_task(_safe(get_market_news, "general", hours_back))

    cvm_news, gnews_news, finnhub_news = await asyncio.gather(cvm_task, gnews_task, finnhub_task)

    all_news = cvm_news + gnews_news + finnhub_news

    if not all_news:
        return []

    # Deduplicate by headline similarity (simple)
    seen_headlines: set[str] = set()
    deduped = []
    for n in all_news:
        h = n.get("headline", "")[:60].lower()
        if h not in seen_headlines:
            seen_headlines.add(h)
            deduped.append(n)

    # Take top 15 for LLM ranking
    candidates = deduped[:15]

    # Build prompt
    headlines_txt = "\n".join(
        f"{i+1}. [{n.get('source','?')}] {n.get('headline', '')}"
        for i, n in enumerate(candidates)
    )

    try:
        import json
        from app.modules.ai.provider import call_llm

        prompt = f"Notícias recentes de mercado:\n\n{headlines_txt}\n\nRanqueie e analise as 9 mais relevantes."
        raw = await call_llm(prompt, system=_RANK_SYSTEM, tier="free", max_tokens=1500)

        # Extract JSON
        start = raw.find("[")
        end = raw.rfind("]") + 1
        if start >= 0 and end > start:
            ranked = json.loads(raw[start:end])
            return ranked[:9]
    except Exception as exc:
        logger.warning("news: LLM ranking failed: %s", exc)

    # Fallback: return raw headlines without ranking
    return [
        {
            "manchete": n.get("headline", ""),
            "por_que_importa": "Sem análise disponível",
            "impacto_provavel": "Indefinido",
            "ativos_afetados": n.get("tickers", []),
            "acao_sugerida": "Monitorar",
        }
        for n in candidates[:9]
    ]


def format_news_section(news: list[dict[str, Any]]) -> str:
    """Format ranked news as Telegram HTML string."""
    if not news:
        return "<b>📰 Notícias do dia</b>\n\nSem notícias relevantes no momento."

    lines = ["<b>📰 Notícias mais relevantes</b>", ""]
    for i, n in enumerate(news, 1):
        headline = n.get("manchete", n.get("headline", ""))
        por_que = n.get("por_que_importa", "")
        impacto = n.get("impacto_provavel", "")
        ativos = n.get("ativos_afetados", [])
        acao = n.get("acao_sugerida", "")

        ativos_str = ", ".join(ativos) if isinstance(ativos, list) else str(ativos)

        lines.append(f"<b>{i}. {headline}</b>")
        if por_que:
            lines.append(f"  📌 {por_que}")
        if impacto:
            lines.append(f"  📈 Impacto: {impacto}")
        if ativos_str:
            lines.append(f"  🎯 Ativos: {ativos_str}")
        if acao:
            lines.append(f"  ✅ Ação: {acao}")
        lines.append("")

    return "\n".join(lines)
