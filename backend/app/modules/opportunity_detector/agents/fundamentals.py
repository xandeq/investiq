"""Fundamentals Agent — evaluates asset fundamentals to support the opportunity verdict.

Reuses BRAPI data already fetched by the scanner. For Phase 1 uses a
simplified fundamentals check (P/E, dividend yield, market cap) since full
DCF requires paid BRAPI plan modules. Phase 2 can wire into the existing
analysis module's DCF/earnings pipeline.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class FundamentalsResult:
    quality: str  # "solidos" | "medianos" | "fracos" | "indisponivel"
    summary: str  # 1-sentence PT-BR
    metrics: dict = field(default_factory=dict)  # raw metrics for Phase 2 UI


async def analyze_fundamentals(
    ticker: str,
    asset_type: str,
    quote_data: dict,
    call_llm,
) -> FundamentalsResult:
    """Assess fundamentals using available quote data."""
    if asset_type != "acao":
        # Crypto/RF: no fundamental analysis
        return FundamentalsResult(
            quality="indisponivel",
            summary="Análise fundamentalista não aplicável para este tipo de ativo.",
        )

    # Extract available metrics from BRAPI quote
    metrics = {
        "pe_ratio": quote_data.get("priceEarnings"),
        "eps": quote_data.get("earningsPerShare"),
        "market_cap": quote_data.get("marketCap"),
        "dividend_yield": quote_data.get("dividendYield"),
        "price": quote_data.get("regularMarketPrice"),
        "52w_low": quote_data.get("fiftyTwoWeekLow"),
        "52w_high": quote_data.get("fiftyTwoWeekHigh"),
    }

    # Build metrics summary for LLM
    metrics_str = "\n".join(
        f"- {k}: {v}" for k, v in metrics.items() if v is not None
    ) or "Sem métricas disponíveis"

    prompt = f"""Você é um analista fundamentalista do mercado brasileiro.

Ativo: {ticker}
Métricas disponíveis:
{metrics_str}

Tarefa: Avalie rapidamente a qualidade fundamentalista deste ativo.

Responda EXCLUSIVAMENTE neste formato JSON (sem markdown):
{{
  "quality": "<solidos|medianos|fracos|indisponivel>",
  "summary": "<1 frase em PT-BR sobre a saúde fundamentalista>"
}}

Critérios:
- solidos: P/L razoável para o setor, EPS positivo, boa capitalização
- medianos: métricas mistas, alguns pontos de atenção
- fracos: P/L negativo, EPS negativo, capitalização baixa, alto endividamento
- indisponivel: sem dados suficientes

Responda apenas o JSON."""

    try:
        text, _ = await call_llm(prompt, max_tokens=150)
        import json
        clean = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return FundamentalsResult(
            quality=data.get("quality", "indisponivel"),
            summary=data.get("summary", "Análise indisponível."),
            metrics=metrics,
        )
    except Exception as exc:
        logger.warning("FundamentalsAgent failed for %s: %s", ticker, exc)
        return FundamentalsResult(
            quality="indisponivel",
            summary="Análise fundamentalista indisponível no momento.",
            metrics=metrics,
        )
