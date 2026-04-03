"""Cause Agent — identifies the probable reason for a significant price drop.

Output: cause category + short explanation in PT-BR.
Categories: macro, setor, operacional, manipulacao, desconhecido
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CauseResult:
    category: str  # "macro" | "setor" | "operacional" | "manipulacao" | "desconhecido"
    is_systemic: bool  # True = market-wide risk (avoid), False = isolated (opportunity)
    explanation: str  # 1–2 sentences PT-BR
    confidence: str  # "alta" | "media" | "baixa"


async def analyze_cause(
    ticker: str,
    asset_type: str,  # "acao" | "crypto" | "renda_fixa"
    drop_pct: float,
    period: str,  # "diario" | "semanal"
    call_llm,  # injected to avoid circular imports
) -> CauseResult:
    """Identify probable cause of the price drop via LLM."""
    prompt = f"""Você é um analista financeiro sênior especializado no mercado brasileiro.

Ativo: {ticker} ({asset_type})
Queda: {abs(drop_pct):.1f}% ({period})
Data da análise: hoje

Tarefa: Identifique a causa mais provável desta queda e classifique o risco.

Responda EXCLUSIVAMENTE neste formato JSON (sem markdown):
{{
  "category": "<macro|setor|operacional|manipulacao|desconhecido>",
  "is_systemic": <true|false>,
  "explanation": "<1 frase explicando a causa provável em PT-BR>",
  "confidence": "<alta|media|baixa>"
}}

Categorias:
- macro: crise econômica, juros, câmbio, recessão global
- setor: regulação do setor, concorrência, comodities do setor
- operacional: acidente, escândalo, resultado ruim, mudança de gestão
- manipulacao: volume atípico sem notícia, pump-and-dump
- desconhecido: sem notícia clara identificável

Considerações para is_systemic:
- true: toda a bolsa cai junto (Selic, dólar, crise global) — risco sistêmico, evitar
- false: queda isolada neste ativo/setor — potencial oportunidade

Responda apenas o JSON."""

    try:
        text, _ = await call_llm(prompt, max_tokens=200)
        import json
        # Strip potential markdown fences
        clean = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
        data = json.loads(clean)
        return CauseResult(
            category=data.get("category", "desconhecido"),
            is_systemic=bool(data.get("is_systemic", False)),
            explanation=data.get("explanation", "Causa não identificada."),
            confidence=data.get("confidence", "baixa"),
        )
    except Exception as exc:
        logger.warning("CauseAgent failed for %s: %s", ticker, exc)
        return CauseResult(
            category="desconhecido",
            is_systemic=False,
            explanation="Análise de causa indisponível no momento.",
            confidence="baixa",
        )
