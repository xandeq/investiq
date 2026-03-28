"""Celery task for Wizard Onde Investir AI recommendation (Phase 11 — WIZ-01-05).

Pattern: sync Celery task + asyncio.run() for LLM call.
DB writes use superuser session (bypass RLS race condition).
DB reads use tenant-scoped sync session.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from datetime import datetime, timezone
from decimal import Decimal

from celery import shared_task
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

PRAZO_LABELS = {"6m": "6 meses", "1a": "1 ano", "2a": "2 anos", "5a": "5 anos"}
PERFIL_LABELS = {
    "conservador": "Conservador (baixo risco, prefere estabilidade)",
    "moderado": "Moderado (risco equilibrado, busca crescimento)",
    "arrojado": "Arrojado (alto risco, foco em crescimento acelerado)",
}
ASSET_LABELS = {"acoes": "Ações/BDR/ETF", "fiis": "FIIs", "renda_fixa": "Renda Fixa"}
PORTFOLIO_CLASS_MAP = {"acao": "acoes", "bdr": "acoes", "etf": "acoes", "fii": "fiis", "renda_fixa": "renda_fixa"}

# Ticker pattern: 3-6 uppercase letters followed by 1-2 digits (e.g. PETR4, HGLG11)
_TICKER_RE = re.compile(r'\b[A-Z]{3,6}\d{1,2}\b')


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


def _get_portfolio_allocation(tenant_id: str) -> dict | None:
    try:
        from app.core.db_sync import get_sync_db_session
        from app.modules.portfolio.models import Transaction
        from sqlalchemy import select

        with get_sync_db_session(tenant_id) as session:
            txs = session.execute(
                select(Transaction).where(
                    Transaction.transaction_type.in_(["buy", "sell"]),
                    Transaction.deleted_at.is_(None),
                )
            ).scalars().all()

        if not txs:
            return None

        invested: dict[str, Decimal] = {ac: Decimal("0") for ac in ["acoes", "fiis", "renda_fixa"]}
        for tx in txs:
            sim_class = PORTFOLIO_CLASS_MAP.get(tx.asset_class)
            if not sim_class:
                continue
            cost = tx.quantity * tx.unit_price + (tx.brokerage_fee or Decimal("0"))
            if tx.transaction_type == "buy":
                invested[sim_class] += cost
            else:
                invested[sim_class] -= cost

        total = sum(v for v in invested.values() if v > 0)
        if total <= 0:
            return None

        result = {"total": float(total)}
        for ac in ["acoes", "fiis", "renda_fixa"]:
            v = max(float(invested.get(ac, 0)), 0)
            result[ac] = {"pct": round(v / float(total) * 100, 1), "valor": round(v, 2)}
        return result
    except Exception as exc:
        logger.warning("_get_portfolio_allocation failed: %s", exc)
        return None


def _build_prompt(perfil: str, prazo: str, valor: float, macro: dict, portfolio: dict | None) -> str:
    prazo_label = PRAZO_LABELS.get(prazo, prazo)
    perfil_label = PERFIL_LABELS.get(perfil, perfil)

    portfolio_section = ""
    if portfolio:
        total = portfolio["total"]
        ac = portfolio.get("acoes", {})
        fi = portfolio.get("fiis", {})
        rf = portfolio.get("renda_fixa", {})
        portfolio_section = f"""
CARTEIRA ATUAL DO INVESTIDOR:
- Ações/BDR/ETF: {ac.get('pct', 0):.1f}% (R$ {ac.get('valor', 0):,.0f})
- FIIs: {fi.get('pct', 0):.1f}% (R$ {fi.get('valor', 0):,.0f})
- Renda Fixa: {rf.get('pct', 0):.1f}% (R$ {rf.get('valor', 0):,.0f})
- Total investido: R$ {total:,.0f}
"""
    else:
        portfolio_section = "\nO investidor ainda não possui carteira registrada no sistema.\n"

    return f"""Você é um consultor financeiro brasileiro especializado em alocação de portfólio.

REGRAS OBRIGATÓRIAS — leia com atenção:
1. Retorne APENAS um JSON válido, sem markdown, sem blocos de código, sem texto fora do JSON
2. NUNCA mencione tickers específicos (ex: PETR4, VALE3, HGLG11, KNRI11) na rationale
3. Os percentuais devem somar exatamente 100
4. A rationale deve ser em português (PT-BR), 2-4 parágrafos, referenciar os dados macro fornecidos

PERFIL DO INVESTIDOR:
- Perfil de risco: {perfil_label}
- Valor disponível para investir: R$ {valor:,.0f}
- Prazo do investimento: {prazo_label}

CONTEXTO MACROECONÔMICO ATUAL (use estes dados na rationale):
- SELIC: {macro.get('selic', 'N/D')}% a.a.
- CDI: {macro.get('cdi', 'N/D')}% a.a.
- IPCA (12 meses): {macro.get('ipca', 'N/D')}%
{portfolio_section}
Retorne EXATAMENTE este JSON (sem nenhum texto antes ou depois):
{{
  "acoes_pct": <número inteiro 0-100>,
  "fiis_pct": <número inteiro 0-100>,
  "renda_fixa_pct": <número inteiro 0-100>,
  "caixa_pct": <número inteiro 0-100>,
  "rationale": "<texto em português PT-BR, 2-4 parágrafos separados por \\n\\n>"
}}"""


def _parse_and_validate(raw: str) -> dict:
    """Parse LLM JSON output and validate allocation fields."""
    # Strip markdown code blocks if present
    text = raw.strip()
    if "```" in text:
        text = re.sub(r"```(?:json)?", "", text).strip().rstrip("`").strip()

    # Find first { and last }
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in LLM response")
    text = text[start:end]

    data = json.loads(text)

    # Validate required fields
    for field in ["acoes_pct", "fiis_pct", "renda_fixa_pct", "caixa_pct", "rationale"]:
        if field not in data:
            raise ValueError(f"Missing field: {field}")

    # Validate sum
    total = float(data["acoes_pct"]) + float(data["fiis_pct"]) + float(data["renda_fixa_pct"]) + float(data["caixa_pct"])
    if abs(total - 100) > 3:
        raise ValueError(f"Percentages sum to {total}, expected ~100")

    # Check for tickers in rationale
    rationale = str(data.get("rationale", ""))
    match = _TICKER_RE.search(rationale)
    if match:
        raise ValueError(f"Ticker detected in rationale: {match.group()}")

    return data


def _update_job(job_id: str, status: str, result_json: str | None = None, error: str | None = None, retry_count: int | None = None) -> None:
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from app.modules.wizard.models import WizardJob

        now = datetime.now(timezone.utc)
        values = {"status": status}
        if result_json is not None:
            values["result_json"] = result_json
        if error is not None:
            values["error_message"] = error[:500]
        if retry_count is not None:
            values["retry_count"] = retry_count
        if status in ("completed", "failed"):
            values["completed_at"] = now

        with get_superuser_sync_db_session() as session:
            session.execute(update(WizardJob).where(WizardJob.id == job_id).values(**values))
    except Exception as exc:
        logger.error("_update_job failed for job %s: %s", job_id, exc)


@shared_task(name="wizard.run_recommendation", bind=True, max_retries=0)
def run_recommendation(self, job_id: str, tenant_id: str, perfil: str, prazo: str, valor: float, use_free_tier: bool = False) -> None:
    """Run AI allocation recommendation for the Wizard Onde Investir.

    Steps:
    1. Set job status → running
    2. Fetch macro from Redis
    3. Fetch portfolio allocation from tenant DB
    4. Build prompt
    5. Call LLM (asyncio.run)
    6. Parse + validate JSON (ticker check, sum check)
    7. Retry with stronger prompt if validation fails (up to 2 retries)
    8. Store result and mark completed / failed
    """
    logger.info("Wizard recommendation started: job=%s perfil=%s prazo=%s", job_id, perfil, prazo)
    _update_job(job_id, "running")

    try:
        from app.modules.ai.provider import call_llm

        macro = _get_macro()
        portfolio = _get_portfolio_allocation(tenant_id)
        prompt = _build_prompt(perfil, prazo, valor, macro, portfolio)

        raw = None
        last_error = None
        provider_used = "unknown"

        for attempt in range(3):
            try:
                if attempt > 0:
                    logger.info("Wizard retry %d for job %s", attempt, job_id)
                    _update_job(job_id, "running", retry_count=attempt)
                    # Reinforce no-ticker rule on retry
                    extra = "\n\nIMPORTANTE: NÃO mencione nenhum ticker (ex: PETR4, VALE3) na rationale. Use apenas nomes genéricos de classes de ativos."
                    prompt_used = prompt + extra
                else:
                    prompt_used = prompt

                raw = asyncio.run(call_llm(
                    prompt_used,
                    system="Você é um consultor financeiro brasileiro. Responda APENAS com JSON válido.",
                    tier="free" if use_free_tier else "paid",
                    max_tokens=800,
                ))

                # Try to detect which provider was used from logs (not directly exposed)
                provider_used = "openai/gpt-4o-mini" if not use_free_tier else "free-pool"

                data = _parse_and_validate(raw)
                last_error = None
                break

            except Exception as exc:
                last_error = str(exc)
                logger.warning("Wizard attempt %d failed: %s", attempt + 1, exc)

        if last_error:
            _update_job(job_id, "failed", error=f"After 3 attempts: {last_error}")
            return

        # Build delta if portfolio available
        delta = None
        if portfolio:
            delta = []
            suggested = {
                "acoes": float(data["acoes_pct"]),
                "fiis": float(data["fiis_pct"]),
                "renda_fixa": float(data["renda_fixa_pct"]),
                "caixa": float(data["caixa_pct"]),
            }
            labels = {"acoes": "Ações", "fiis": "FIIs", "renda_fixa": "Renda Fixa", "caixa": "Caixa"}
            for ac in ["acoes", "fiis", "renda_fixa", "caixa"]:
                curr_pct = portfolio.get(ac, {}).get("pct", 0) if ac != "caixa" else 0.0
                sug_pct = suggested[ac]
                d = round(sug_pct - curr_pct, 1)
                action = "adicionar" if d > 1 else ("reduzir" if d < -1 else "manter")
                delta.append({
                    "asset_class": ac,
                    "label": labels[ac],
                    "current_pct": curr_pct,
                    "suggested_pct": sug_pct,
                    "delta_pct": d,
                    "action": action,
                    "valor_delta": round(abs(d) * valor / 100, 2),
                })

        result = {
            "allocation": {
                "acoes_pct": float(data["acoes_pct"]),
                "fiis_pct": float(data["fiis_pct"]),
                "renda_fixa_pct": float(data["renda_fixa_pct"]),
                "caixa_pct": float(data["caixa_pct"]),
                "rationale": data["rationale"],
            },
            "macro": macro,
            "portfolio_context": portfolio,
            "delta": delta,
            "provider_used": provider_used,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _update_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        logger.info("Wizard recommendation completed: job=%s", job_id)

    except Exception as exc:
        logger.error("Wizard task unhandled error for job %s: %s", job_id, exc)
        _update_job(job_id, "failed", error=str(exc)[:500])
