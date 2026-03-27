"""Daily insights generation — rule-based alerts without LLM calls."""
from __future__ import annotations
import logging
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from celery import shared_task

logger = logging.getLogger(__name__)

CDI_THRESHOLD_FOR_SELIC_ALERT = Decimal("13")
CONCENTRATION_THRESHOLD = Decimal("30")
DROP_THRESHOLD = Decimal("-15")


def _get_all_tenants() -> list[str]:
    try:
        from app.core.db_sync import get_superuser_sync_db_session
        from sqlalchemy import text
        with get_superuser_sync_db_session() as session:
            rows = session.execute(text("SELECT DISTINCT tenant_id FROM transactions WHERE deleted_at IS NULL")).fetchall()
            return [r[0] for r in rows]
    except Exception as exc:
        logger.error("Failed to get tenants: %s", exc)
        return []


def _get_positions(tenant_id: str) -> list[dict]:
    try:
        from app.core.db_sync import get_sync_db_session
        from sqlalchemy import text
        with get_sync_db_session(tenant_id) as session:
            rows = session.execute(text(
                "SELECT ticker, asset_class, SUM(CASE WHEN transaction_type='buy' THEN quantity ELSE -quantity END) as qty, "
                "SUM(CASE WHEN transaction_type='buy' THEN total_value ELSE -total_value END) as cost "
                "FROM transactions WHERE deleted_at IS NULL AND transaction_type IN ('buy','sell') "
                "GROUP BY ticker, asset_class HAVING SUM(CASE WHEN transaction_type='buy' THEN quantity ELSE -quantity END) > 0"
            )).fetchall()
            return [{"ticker": r[0], "asset_class": r[1], "qty": r[2], "cost": Decimal(str(r[3]))} for r in rows]
    except Exception:
        return []


def _get_macro() -> dict:
    try:
        import os, redis as sync_redis, json
        r = sync_redis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"), decode_responses=True)
        return {k: r.get(f"market:macro:{k}") or "0" for k in ["selic", "cdi"]}
    except Exception:
        return {}


def _save_insight(tenant_id: str, type_: str, title: str, body: str, severity: str, ticker: str | None = None) -> None:
    try:
        from app.core.db_sync import get_sync_db_session
        from sqlalchemy import text
        with get_sync_db_session(tenant_id) as session:
            session.execute(text(
                "INSERT INTO user_insights (id, tenant_id, type, title, body, severity, ticker, seen, created_at) "
                "VALUES (:id, :tid, :type, :title, :body, :sev, :ticker, false, :now)"
            ), {"id": str(uuid.uuid4()), "tid": tenant_id, "type": type_, "title": title,
                "body": body, "sev": severity, "ticker": ticker, "now": datetime.now(tz=timezone.utc)})
    except Exception as exc:
        logger.error("Failed to save insight: %s", exc)


@shared_task(name="app.modules.insights.tasks.generate_daily_insights")
def generate_daily_insights() -> None:
    tenants = _get_all_tenants()
    macro = _get_macro()
    selic = Decimal(macro.get("selic", "0") or "0")
    logger.info("Generating insights for %d tenants", len(tenants))

    for tenant_id in tenants:
        positions = _get_positions(tenant_id)
        if not positions:
            continue

        total_cost = sum(p["cost"] for p in positions)
        if total_cost <= 0:
            continue

        for p in positions:
            pct = p["cost"] / total_cost * 100
            if pct >= CONCENTRATION_THRESHOLD:
                _save_insight(tenant_id, "concentration",
                    f"Concentração alta em {p['ticker']}",
                    f"{p['ticker']} representa {pct:.1f}% da carteira. Alta concentração aumenta o risco específico.",
                    "warning", p["ticker"])

        # SELIC alert: if < 10% renda fixa and SELIC > 13%
        rf_pct = sum(p["cost"] for p in positions if p["asset_class"] == "renda_fixa") / total_cost * 100
        if selic >= CDI_THRESHOLD_FOR_SELIC_ALERT and rf_pct < 10:
            _save_insight(tenant_id, "selic_alert",
                f"SELIC em {selic}% — renda fixa sub-representada",
                f"Com SELIC em {selic}% a.a., sua alocação em renda fixa ({rf_pct:.1f}%) pode estar perdendo oportunidade de risco/retorno.",
                "warning")

        # Diversification alert: fewer than 3 distinct tickers
        if len(positions) <= 2:
            _save_insight(tenant_id, "low_diversification",
                "Carteira pouco diversificada",
                f"Você tem apenas {len(positions)} ativo{'s' if len(positions) != 1 else ''} na carteira. Diversificar entre mais ativos reduz o risco específico.",
                "info")

        # All equity alert: no renda_fixa or caixa at all
        has_rf = any(p["asset_class"] in ("renda_fixa", "caixa") for p in positions)
        if not has_rf and len(positions) >= 3:
            _save_insight(tenant_id, "no_fixed_income",
                "Carteira 100% em renda variável",
                "Sua carteira não possui renda fixa ou caixa. Considere uma reserva de emergência ou alocação defensiva.",
                "info")

        # Asset class concentration: >70% in a single class
        classes = {}
        for p in positions:
            classes[p["asset_class"]] = classes.get(p["asset_class"], Decimal("0")) + p["cost"]
        for ac, ac_cost in classes.items():
            ac_pct = ac_cost / total_cost * 100
            if ac_pct >= 70 and len(classes) > 1:
                ac_labels = {"acao": "Ações", "fii": "FIIs", "renda_fixa": "Renda Fixa", "etf": "ETFs", "bdr": "BDRs"}
                ac_label = ac_labels.get(ac, ac)
                _save_insight(tenant_id, "class_concentration",
                    f"{ac_label} representam {ac_pct:.0f}% da carteira",
                    f"Alta concentração em uma única classe de ativo ({ac_label}: {ac_pct:.1f}%) aumenta o risco setorial. Considere diversificar entre classes.",
                    "warning")

    logger.info("Daily insights generation complete")
