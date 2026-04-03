"""Analyzer — orchestrates the 4 AI agents for a detected opportunity.

Pipeline: Cause → Fundamentals → Risk → (Recommendation if is_opportunity)

All agents are called sequentially (each depends on previous output).
LLM calls use the existing analysis providers chain (OpenRouter → Groq).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

from app.modules.analysis.providers import call_analysis_llm
from app.modules.opportunity_detector.agents.cause import CauseResult, analyze_cause
from app.modules.opportunity_detector.agents.fundamentals import FundamentalsResult, analyze_fundamentals
from app.modules.opportunity_detector.agents.risk import RiskResult, analyze_risk
from app.modules.opportunity_detector.agents.recommendation import (
    RecommendationResult,
    generate_recommendation,
)

logger = logging.getLogger(__name__)


@dataclass
class OpportunityReport:
    ticker: str
    asset_type: str  # "acao" | "crypto" | "renda_fixa"
    drop_pct: float
    period: str  # "diario" | "semanal"
    current_price: float
    currency: str  # "BRL" | "USD"

    cause: CauseResult = field(default=None)
    fundamentals: FundamentalsResult = field(default=None)
    risk: RiskResult = field(default=None)
    recommendation: Optional[RecommendationResult] = None

    def alert_message(self) -> str:
        """Format a short alert message for Telegram/email."""
        emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴", "evitar": "⛔"}.get(
            self.risk.level if self.risk else "medio", "🔴"
        )
        currency_symbol = "R$" if self.currency == "BRL" else "US$"
        lines = [
            f"{emoji} *{self.ticker}* caiu *{abs(self.drop_pct):.1f}%* ({self.period})",
            f"Preço atual: {currency_symbol} {self.current_price:,.2f}",
            f"Causa: {self.cause.explanation if self.cause else 'N/D'}",
        ]
        if self.fundamentals and self.fundamentals.quality != "indisponivel":
            lines.append(f"Fundamentos: {self.fundamentals.summary}")
        if self.risk:
            lines.append(f"Risco: {self.risk.level} — {self.risk.rationale}")
        if self.recommendation and self.risk and self.risk.is_opportunity:
            rec = self.recommendation
            lines.append(
                f"💡 Sugestão: aportar R$ {rec.suggested_amount_brl:,.0f}. "
                f"Target: +{rec.target_upside_pct:.0f}% em {rec.timeframe_days}d. "
                f"Stop: -{rec.stop_loss_pct:.0f}%."
            )
            lines.append(f"_{rec.disclaimer}_")
        else:
            lines.append("_Não identificado como oportunidade de compra no momento._")
        return "\n".join(lines)

    def alert_html(self) -> str:
        """Format HTML body for email."""
        emoji = {"baixo": "🟢", "medio": "🟡", "alto": "🔴", "evitar": "⛔"}.get(
            self.risk.level if self.risk else "medio", "🔴"
        )
        currency_symbol = "R$" if self.currency == "BRL" else "US$"
        rec_html = ""
        if self.recommendation and self.risk and self.risk.is_opportunity:
            rec = self.recommendation
            rec_html = f"""
            <div style="background:#f0fdf4;border-left:4px solid #16a34a;padding:12px;margin-top:12px;border-radius:4px;">
              <strong>💡 Sugestão de aporte</strong><br>
              Valor: <strong>R$ {rec.suggested_amount_brl:,.0f}</strong> |
              Target: <strong>+{rec.target_upside_pct:.0f}%</strong> em {rec.timeframe_days} dias |
              Stop-loss: <strong>-{rec.stop_loss_pct:.0f}%</strong><br>
              <em style="color:#666;font-size:12px;">{rec.disclaimer}</em>
            </div>"""
        return f"""
        <div style="font-family:sans-serif;max-width:520px;margin:auto;padding:24px;">
          <h2>{emoji} Oportunidade Detectada — {self.ticker}</h2>
          <table style="width:100%;border-collapse:collapse;">
            <tr><td><strong>Queda</strong></td><td>{abs(self.drop_pct):.1f}% ({self.period})</td></tr>
            <tr><td><strong>Preço atual</strong></td><td>{currency_symbol} {self.current_price:,.2f}</td></tr>
            <tr><td><strong>Causa</strong></td><td>{self.cause.explanation if self.cause else 'N/D'}</td></tr>
            <tr><td><strong>Fundamentos</strong></td><td>{self.fundamentals.summary if self.fundamentals else 'N/D'}</td></tr>
            <tr><td><strong>Risco</strong></td><td>{self.risk.level if self.risk else 'N/D'} — {self.risk.rationale if self.risk else ''}</td></tr>
          </table>
          {rec_html}
        </div>"""


async def run_analysis(
    ticker: str,
    asset_type: str,
    drop_pct: float,
    period: str,
    current_price: float,
    currency: str,
    quote_data: dict,
) -> OpportunityReport:
    """Run full 4-agent pipeline for a detected opportunity."""
    report = OpportunityReport(
        ticker=ticker,
        asset_type=asset_type,
        drop_pct=drop_pct,
        period=period,
        current_price=current_price,
        currency=currency,
    )

    # Agent 1: Cause
    try:
        report.cause = await analyze_cause(
            ticker=ticker,
            asset_type=asset_type,
            drop_pct=drop_pct,
            period=period,
            call_llm=call_analysis_llm,
        )
        logger.info("CauseAgent done for %s: %s (systemic=%s)", ticker, report.cause.category, report.cause.is_systemic)
    except Exception as exc:
        logger.error("CauseAgent exception for %s: %s", ticker, exc)

    # Agent 2: Fundamentals
    try:
        report.fundamentals = await analyze_fundamentals(
            ticker=ticker,
            asset_type=asset_type,
            quote_data=quote_data,
            call_llm=call_analysis_llm,
        )
        logger.info("FundamentalsAgent done for %s: %s", ticker, report.fundamentals.quality)
    except Exception as exc:
        logger.error("FundamentalsAgent exception for %s: %s", ticker, exc)

    # Agent 3: Risk
    try:
        report.risk = await analyze_risk(
            ticker=ticker,
            drop_pct=drop_pct,
            cause=report.cause,
            fundamentals=report.fundamentals,
            call_llm=call_analysis_llm,
        )
        logger.info("RiskAgent done for %s: level=%s opportunity=%s", ticker, report.risk.level, report.risk.is_opportunity)
    except Exception as exc:
        logger.error("RiskAgent exception for %s: %s", ticker, exc)

    # Agent 4: Recommendation (only if is_opportunity)
    if report.risk and report.risk.is_opportunity:
        try:
            report.recommendation = await generate_recommendation(
                ticker=ticker,
                asset_type=asset_type,
                current_price=current_price,
                drop_pct=drop_pct,
                risk_level=report.risk.level,
                cause_explanation=report.cause.explanation if report.cause else "",
                fundamentals_summary=report.fundamentals.summary if report.fundamentals else "",
                call_llm=call_analysis_llm,
            )
            logger.info("RecommendationAgent done for %s: R$%.0f target +%.0f%%", ticker, report.recommendation.suggested_amount_brl, report.recommendation.target_upside_pct)
        except Exception as exc:
            logger.error("RecommendationAgent exception for %s: %s", ticker, exc)

    return report
