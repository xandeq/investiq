"""Celery task for Portfolio Advisor AI narrative (Phase 23 — ADVI-02).

Pattern: identical to wizard/tasks.py — sync Celery + asyncio.run for LLM call.
Job persistence: reuses WizardJob table with perfil="advisor" as discriminator.
Output: narrative text (educational, CVM-compliant) — NOT an allocation JSON.

CVM compliance rules baked into prompt:
  - Output must be educacional, not prescriptivo
  - No specific ticker recommendations in narrative
  - No guaranteed return promises
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from decimal import Decimal

from celery import shared_task
from sqlalchemy import select, update

logger = logging.getLogger(__name__)


def _get_sync_redis():
    import redis as sync_redis
    return sync_redis.from_url(
        os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True
    )


def _get_macro() -> dict[str, str]:
    r = _get_sync_redis()
    result = {}
    for k in ["selic", "cdi", "ipca"]:
        val = r.get(f"market:macro:{k}")
        if val:
            try:
                result[k] = f"{float(val):.2f}"
            except (ValueError, TypeError):
                result[k] = val
        else:
            result[k] = "N/D"
    return result


def _get_health_sync(tenant_id: str) -> dict | None:
    """Compute portfolio health synchronously for Celery context."""
    try:
        from sqlalchemy import func as sqlfunc
        from app.core.db_sync import get_sync_db_session
        from app.modules.portfolio.models import Transaction
        from app.modules.market_universe.models import ScreenerSnapshot
        from datetime import date, timedelta

        # ── Buy/sell positions (tenant-scoped) ──
        with get_sync_db_session(tenant_id) as session:
            txs = session.execute(
                select(
                    Transaction.ticker,
                    Transaction.transaction_type,
                    Transaction.total_value,
                ).where(
                    Transaction.transaction_type.in_(["buy", "sell"]),
                    Transaction.deleted_at.is_(None),
                )
            ).all()

            ttm_cutoff = date.today() - timedelta(days=365)
            passive_ttm = session.execute(
                select(sqlfunc.sum(Transaction.total_value)).where(
                    Transaction.transaction_type.in_(["dividend", "jscp"]),
                    Transaction.transaction_date >= ttm_cutoff,
                    Transaction.deleted_at.is_(None),
                )
            ).scalar() or Decimal("0")

        if not txs:
            return None

        positions: dict[str, Decimal] = {}
        for row in txs:
            delta = Decimal(str(row.total_value))
            if row.transaction_type == "sell":
                delta = -delta
            positions[row.ticker] = positions.get(row.ticker, Decimal("0")) + delta
        active = {t: v for t, v in positions.items() if v > Decimal("0")}
        if not active:
            return None

        total = sum(active.values())

        # ── Screener data (global tables — no RLS, pass None) ──
        with get_sync_db_session(None) as gsession:
            latest_sq = (
                select(
                    ScreenerSnapshot.ticker,
                    sqlfunc.max(ScreenerSnapshot.snapshot_date).label("max_date"),
                )
                .where(ScreenerSnapshot.ticker.in_(list(active.keys())))
                .group_by(ScreenerSnapshot.ticker)
                .subquery()
            )
            snaps_rows = gsession.execute(
                select(ScreenerSnapshot).join(
                    latest_sq,
                    (ScreenerSnapshot.ticker == latest_sq.c.ticker)
                    & (ScreenerSnapshot.snapshot_date == latest_sq.c.max_date),
                )
            ).scalars().all()
        snaps = {s.ticker: s for s in snaps_rows}

        # ── Sector map ──
        sector_map: dict[str, Decimal] = {}
        for ticker, cost in active.items():
            snap = snaps.get(ticker)
            sector = (snap.sector or "Outros") if snap else "Outros"
            sector_map[sector] = sector_map.get(sector, Decimal("0")) + cost

        biggest_sector, biggest_sector_val = max(sector_map.items(), key=lambda x: x[1])
        biggest_sector_pct = float(biggest_sector_val / total * 100)
        biggest_ticker, biggest_asset_val = max(active.items(), key=lambda x: x[1])
        biggest_asset_pct = float(biggest_asset_val / total * 100)

        # ── Underperformers ──
        underperformers = []
        underperformer_cost = Decimal("0")
        for ticker, cost in active.items():
            snap = snaps.get(ticker)
            if snap and snap.variacao_12m_pct is not None and snap.variacao_12m_pct < Decimal("-10"):
                underperformers.append((ticker, float(snap.variacao_12m_pct), cost))
        underperformers.sort(key=lambda x: x[1])
        underperformer_cost = sum(x[2] for x in underperformers)
        underperformer_ratio = float(underperformer_cost / total) if total > 0 else 0.0

        under_labels = [f"{t} ({v:.1f}%)" for t, v, _ in underperformers[:3]]

        # ── Score ──
        score = 100
        if biggest_sector_pct > 50:
            score -= 20
        if biggest_asset_pct > 30:
            score -= 25
        if len(active) < 5:
            score -= 15
        if underperformer_ratio > 0.30:
            score -= 20
        if passive_ttm == 0:
            score -= 10
        score = max(score, 10)

        biggest_risk = None
        if biggest_sector_pct > 50:
            biggest_risk = f"{biggest_sector_pct:.0f}% concentrado em {biggest_sector}"
        elif biggest_asset_pct > 30:
            biggest_risk = f"{biggest_asset_pct:.0f}% em um único ativo ({biggest_ticker})"
        elif len(active) < 5:
            biggest_risk = f"Apenas {len(active)} ativo(s) — baixa diversificação"

        passive_monthly = float(Decimal(str(passive_ttm)) / 12)

        return {
            "health_score": score,
            "biggest_risk": biggest_risk,
            "passive_income_monthly_brl": round(passive_monthly, 2),
            "underperformers": under_labels,
            "total_assets": len(active),
            "sector_concentration": f"{biggest_sector_pct:.0f}% em {biggest_sector}",
            "asset_concentration": f"{biggest_asset_pct:.0f}% em {biggest_ticker}",
        }

    except Exception as exc:
        logger.warning("_get_health_sync failed: %s", exc)
        return None


def _build_advisor_prompt(health: dict, macro: dict) -> str:
    score = health["health_score"]
    risk = health.get("biggest_risk") or "Nenhum risco de concentração identificado"
    income = health.get("passive_income_monthly_brl", 0)
    under = health.get("underperformers") or []
    under_text = ", ".join(under) if under else "nenhum identificado"

    score_label = (
        "equilibrado" if score >= 80
        else "com pontos de atenção" if score >= 60
        else "com riscos que merecem revisão"
    )

    return f"""Você é um educador financeiro brasileiro especializado em finanças pessoais.

REGRAS OBRIGATÓRIAS:
1. Sua resposta deve ser EDUCACIONAL, não prescritiva — explique conceitos, não dê ordens
2. NUNCA mencione tickers específicos (ex: PETR4, VALE3, KNRI11) — use apenas classes de ativos
3. NUNCA prometa retornos ou garantias
4. Responda em português (PT-BR), 3-4 parágrafos fluentes, tom consultivo
5. Retorne APENAS o texto da análise — sem JSON, sem markdown, sem títulos

DIAGNÓSTICO DA CARTEIRA:
- Score de saúde: {score}/100 — portfólio {score_label}
- Principal risco identificado: {risk}
- Renda passiva mensal (últimos 12 meses): R$ {income:,.2f}
- Ativos com queda > 10% no ano: {under_text}
- Concentração setorial: {health.get('sector_concentration', 'N/D')}
- Concentração por ativo: {health.get('asset_concentration', 'N/D')}

CONTEXTO MACROECONÔMICO:
- SELIC: {macro.get('selic', 'N/D')}% a.a.
- CDI: {macro.get('cdi', 'N/D')}% a.a.
- IPCA: {macro.get('ipca', 'N/D')}%

Escreva uma análise educacional que:
1. Contextualize o score de saúde ({score}/100) de forma didática
2. Explique o risco de concentração identificado e por que ele importa
3. Comente sobre a renda passiva no contexto da taxa Selic atual
4. Sugira, de forma genérica, quais TIPOS de ativos (classes, não tickers) poderiam complementar o perfil atual"""


def _update_advisor_job(job_id: str, status: str, result_json: str | None = None, error: str | None = None) -> None:
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.wizard.models import WizardJob

        now = datetime.now(timezone.utc)
        values: dict = {"status": status}
        if result_json is not None:
            values["result_json"] = result_json
        if error is not None:
            values["error_message"] = error[:500]
        if status in ("completed", "failed"):
            values["completed_at"] = now

        with get_superuser_sync_db_session() as session:
            session.execute(update(WizardJob).where(WizardJob.id == job_id).values(**values))
    except Exception as exc:
        logger.error("_update_advisor_job failed for job %s: %s", job_id, exc)


@shared_task(name="advisor.run_analysis", bind=True, max_retries=0)
def run_analysis(self, job_id: str, tenant_id: str, use_free_tier: bool = False) -> None:
    """Run AI portfolio analysis narrative for the advisor feature.

    Steps:
    1. Set job status → running
    2. Compute health metrics synchronously (SQL only)
    3. Fetch macro from Redis
    4. Build CVM-compliant educational prompt
    5. Call LLM (asyncio.run) with fallback chain
    6. Store narrative + health snapshot in result_json
    7. Mark completed / failed
    """
    logger.info("Advisor analysis started: job=%s tenant=%s", job_id, tenant_id)
    _update_advisor_job(job_id, "running")

    try:
        from app.modules.ai.provider import call_llm

        health = _get_health_sync(tenant_id)
        if not health:
            _update_advisor_job(job_id, "failed", error="Portfólio vazio — nenhuma transação encontrada")
            return

        macro = _get_macro()
        prompt = _build_advisor_prompt(health, macro)

        narrative = None
        provider_used = "unknown"
        last_error = None

        for attempt in range(3):
            try:
                if attempt > 0:
                    logger.info("Advisor retry %d for job %s", attempt, job_id)

                narrative = asyncio.run(call_llm(
                    prompt,
                    system="Você é um educador financeiro brasileiro. Responda em texto corrido, sem JSON, sem markdown.",
                    tier="free" if use_free_tier else "paid",
                    max_tokens=1000,
                ))
                provider_used = "free-pool" if use_free_tier else "openai/gpt-4o-mini"
                last_error = None
                break

            except Exception as exc:
                last_error = str(exc)
                logger.warning("Advisor attempt %d failed: %s", attempt + 1, exc)

        if last_error or not narrative:
            _update_advisor_job(job_id, "failed", error=f"After 3 attempts: {last_error}")
            return

        result = {
            "narrative": narrative.strip(),
            "health_score": health["health_score"],
            "biggest_risk": health.get("biggest_risk"),
            "passive_income_monthly_brl": str(health.get("passive_income_monthly_brl", "0")),
            "underperformers": health.get("underperformers", []),
            "provider_used": provider_used,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _update_advisor_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        logger.info("Advisor analysis completed: job=%s", job_id)

    except Exception as exc:
        logger.error("Advisor task unhandled error for job %s: %s", job_id, exc)
        _update_advisor_job(job_id, "failed", error=str(exc)[:500])
