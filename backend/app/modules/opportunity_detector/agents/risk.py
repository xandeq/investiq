"""Risk Agent — classifies systemic vs isolated risk and rates overall risk level.

Synthesizes CauseResult + FundamentalsResult to produce a final risk verdict.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.modules.opportunity_detector.agents.cause import CauseResult
from app.modules.opportunity_detector.agents.fundamentals import FundamentalsResult

logger = logging.getLogger(__name__)


@dataclass
class RiskResult:
    level: str  # "baixo" | "medio" | "alto" | "evitar"
    is_opportunity: bool  # True = buy opportunity, False = stay away
    rationale: str  # 1 sentence PT-BR


async def analyze_risk(
    ticker: str,
    drop_pct: float,
    cause: CauseResult,
    fundamentals: FundamentalsResult,
    call_llm,
) -> RiskResult:
    """Synthesize cause + fundamentals into a risk verdict."""

    # Fast-path: systemic risk = always "evitar"
    if cause.is_systemic:
        return RiskResult(
            level="evitar",
            is_opportunity=False,
            rationale=f"Risco sistêmico detectado ({cause.category}). Aguardar estabilização do mercado.",
        )

    prompt = f"""Você é um gestor de risco especializado no mercado brasileiro.

Ativo: {ticker}
Queda: {abs(drop_pct):.1f}%
Causa identificada: {cause.category} — {cause.explanation}
Risco sistêmico: {"Sim" if cause.is_systemic else "Não"}
Fundamentos: {fundamentals.quality} — {fundamentals.summary}

Tarefa: Classifique o risco e determine se é uma oportunidade de compra.

Responda EXCLUSIVAMENTE neste formato JSON (sem markdown):
{{
  "level": "<baixo|medio|alto|evitar>",
  "is_opportunity": <true|false>,
  "rationale": "<1 frase em PT-BR justificando a classificação>"
}}

Critérios:
- baixo + is_opportunity=true: causa isolada, fundamentos sólidos, queda exagerada
- medio + is_opportunity=true: causa controlável, fundamentos medianos, queda parcialmente justificada
- alto + is_opportunity=false: fundamentos fracos, causa grave mas não sistêmica
- evitar + is_opportunity=false: risco sistêmico ou colapso fundamentalista

Responda apenas o JSON."""

    try:
        text, _ = await call_llm(prompt, max_tokens=150)
        import json
        clean = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return RiskResult(
            level=data.get("level", "medio"),
            is_opportunity=bool(data.get("is_opportunity", False)),
            rationale=data.get("rationale", "Análise de risco indisponível."),
        )
    except Exception as exc:
        logger.warning("RiskAgent failed for %s: %s", ticker, exc)
        return RiskResult(
            level="medio",
            is_opportunity=False,
            rationale="Análise de risco indisponível no momento.",
        )
