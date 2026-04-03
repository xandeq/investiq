"""Recommendation Agent — generates actionable buy suggestion when risk is acceptable.

Only called when RiskResult.is_opportunity is True.
Produces: suggested investment amount, target price, timeframe, stop-loss.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Default suggested investment amount (BRL) when no portfolio size is known
_DEFAULT_SUGGESTION_BRL = 2000.0


@dataclass
class RecommendationResult:
    suggested_amount_brl: float
    target_upside_pct: float  # expected upside % from current price
    timeframe_days: int
    stop_loss_pct: float  # suggested stop-loss % below current price
    action_summary: str  # 1 sentence PT-BR — shown in alert
    disclaimer: str = (
        "Análise educacional. Não constitui recomendação de investimento. "
        "Consulte um assessor financeiro habilitado."
    )


async def generate_recommendation(
    ticker: str,
    asset_type: str,
    current_price: float,
    drop_pct: float,
    risk_level: str,
    cause_explanation: str,
    fundamentals_summary: str,
    call_llm,
) -> RecommendationResult:
    """Generate buy recommendation for confirmed opportunities."""
    prompt = f"""Você é um analista de investimentos do mercado brasileiro.

Ativo: {ticker} ({asset_type})
Preço atual: R$ {current_price:.2f}
Queda recente: {abs(drop_pct):.1f}%
Causa: {cause_explanation}
Fundamentos: {fundamentals_summary}
Nível de risco: {risk_level}

Tarefa: Gere uma sugestão de aporte para um investidor de perfil moderado com R$ 50.000 de portfólio.

Responda EXCLUSIVAMENTE neste formato JSON (sem markdown):
{{
  "suggested_amount_brl": <número entre 1000 e 5000>,
  "target_upside_pct": <número entre 5 e 50>,
  "timeframe_days": <número entre 30 e 365>,
  "stop_loss_pct": <número entre 5 e 20>,
  "action_summary": "<1 frase em PT-BR com a sugestão de aporte, target e prazo>"
}}

Diretrizes:
- Aporte conservador: máx 10% do portfólio (R$ 5.000) para risco médio, R$ 2.000 para risco alto
- Target realista: baseado no histórico do ativo e na causa da queda
- Prazo: curto (30-90d) para recuperação técnica, longo (180-365d) para fundamentos
- Stop-loss: 8-15% abaixo do preço atual

Responda apenas o JSON."""

    try:
        text, _ = await call_llm(prompt, max_tokens=200)
        import json
        clean = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return RecommendationResult(
            suggested_amount_brl=float(data.get("suggested_amount_brl", _DEFAULT_SUGGESTION_BRL)),
            target_upside_pct=float(data.get("target_upside_pct", 15.0)),
            timeframe_days=int(data.get("timeframe_days", 90)),
            stop_loss_pct=float(data.get("stop_loss_pct", 10.0)),
            action_summary=data.get("action_summary", f"Considere um aporte gradual em {ticker}."),
        )
    except Exception as exc:
        logger.warning("RecommendationAgent failed for %s: %s", ticker, exc)
        return RecommendationResult(
            suggested_amount_brl=_DEFAULT_SUGGESTION_BRL,
            target_upside_pct=15.0,
            timeframe_days=90,
            stop_loss_pct=10.0,
            action_summary=f"Sugestão indisponível para {ticker}. Avalie manualmente.",
        )
