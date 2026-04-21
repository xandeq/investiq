"""Celery task for Portfolio Advisor AI narrative (Phase 24 — ADVI-02).

Pattern: identical to wizard/tasks.py — sync Celery + asyncio.run for LLM call.
Job persistence: reuses WizardJob table with perfil="advisor" as discriminator.
Output: structured JSON (diagnostico, pontos_positivos, pontos_de_atencao,
        sugestoes, proximos_passos) from run_portfolio_advisor() skill.

CVM compliance rules baked into prompt (inside run_portfolio_advisor):
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
    ptax = r.get("market:macro:ptax_usd")
    result["ptax_usd"] = f"{float(ptax):.4f}" if ptax else "N/D"
    return result


def _get_portfolio_data_sync(tenant_id: str) -> dict | None:
    """Collect all portfolio data needed by run_portfolio_advisor() synchronously.

    Returns dict with keys: health, positions, pnl, allocation.
    Returns None if the tenant has no active positions.
    """
    try:
        from sqlalchemy import func as sqlfunc
        from app.core.db_sync import get_sync_db_session
        from app.modules.portfolio.models import Transaction
        from app.modules.market_universe.models import ScreenerSnapshot
        from datetime import date, timedelta

        with get_sync_db_session(tenant_id) as session:
            txs = session.execute(
                select(
                    Transaction.ticker,
                    Transaction.transaction_type,
                    Transaction.total_value,
                    Transaction.asset_class,
                    Transaction.quantity,
                    Transaction.unit_price,
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

        # Net cost-basis positions
        position_cost: dict[str, Decimal] = {}
        position_qty: dict[str, Decimal] = {}
        asset_class_map: dict[str, str] = {}
        for row in txs:
            delta_val = Decimal(str(row.total_value))
            delta_qty = Decimal(str(row.quantity or 0))
            if row.transaction_type == "sell":
                delta_val = -delta_val
                delta_qty = -delta_qty
            position_cost[row.ticker] = position_cost.get(row.ticker, Decimal("0")) + delta_val
            position_qty[row.ticker] = position_qty.get(row.ticker, Decimal("0")) + delta_qty
            asset_class_map[row.ticker] = row.asset_class or "outros"

        active = {t: v for t, v in position_cost.items() if v > Decimal("0")}
        if not active:
            return None

        total_cost = sum(active.values())

        # Screener snapshots for price + sector data
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

        # Build positions list for run_portfolio_advisor()
        positions: list[dict] = []
        for ticker, cost in active.items():
            snap = snaps.get(ticker)
            cmp = float(snap.regular_market_price) if snap and snap.regular_market_price else None
            qty = float(position_qty.get(ticker, Decimal("0")))
            avg_cost = float(cost / position_qty[ticker]) if position_qty.get(ticker) and position_qty[ticker] != 0 else None
            upnl = (cmp - float(avg_cost)) * qty if cmp and avg_cost else None
            upnl_pct = (upnl / float(cost) * 100) if upnl is not None and float(cost) > 0 else None
            positions.append({
                "ticker": ticker,
                "asset_class": asset_class_map.get(ticker, "outros"),
                "quantity": round(qty, 4),
                "cmp": round(cmp, 2) if cmp else None,
                "total_cost": round(float(cost), 2),
                "current_price": round(cmp, 2) if cmp else None,
                "unrealized_pnl": round(upnl, 2) if upnl is not None else None,
                "unrealized_pnl_pct": round(upnl_pct, 2) if upnl_pct is not None else None,
            })

        # PnL summary
        unrealized_total = sum(
            p["unrealized_pnl"] for p in positions if p.get("unrealized_pnl") is not None
        )
        pnl = {
            "realized_pnl_total": 0.0,  # simplified — realized PnL from sells not tracked here
            "unrealized_pnl_total": round(unrealized_total, 2),
            "total_portfolio_value": round(float(total_cost) + unrealized_total, 2),
        }

        # Allocation by asset class
        alloc_map: dict[str, Decimal] = {}
        for ticker, cost in active.items():
            ac = asset_class_map.get(ticker, "outros")
            alloc_map[ac] = alloc_map.get(ac, Decimal("0")) + cost
        allocation: list[dict] = [
            {
                "asset_class": ac,
                "total_value": round(float(val), 2),
                "percentage": round(float(val / total_cost * 100), 1),
            }
            for ac, val in sorted(alloc_map.items(), key=lambda x: x[1], reverse=True)
        ]

        # Health metrics (for health card context in prompt)
        sector_map: dict[str, Decimal] = {}
        for ticker, cost in active.items():
            snap = snaps.get(ticker)
            sector = (snap.sector or "Outros") if snap else "Outros"
            sector_map[sector] = sector_map.get(sector, Decimal("0")) + cost

        biggest_sector, biggest_sector_val = max(sector_map.items(), key=lambda x: x[1])
        biggest_sector_pct = float(biggest_sector_val / total_cost * 100)
        biggest_ticker, biggest_asset_val = max(active.items(), key=lambda x: x[1])
        biggest_asset_pct = float(biggest_asset_val / total_cost * 100)

        underperformers = []
        underperformer_cost = Decimal("0")
        for ticker, cost in active.items():
            snap = snaps.get(ticker)
            if snap and snap.variacao_12m_pct is not None and snap.variacao_12m_pct < Decimal("-10"):
                underperformers.append((ticker, float(snap.variacao_12m_pct), cost))
        underperformers.sort(key=lambda x: x[1])
        underperformer_cost = sum(x[2] for x in underperformers)
        underperformer_ratio = float(underperformer_cost / total_cost) if total_cost > 0 else 0.0
        under_labels = [f"{t} ({v:.1f}%)" for t, v, _ in underperformers[:3]]

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

        health = {
            "health_score": score,
            "biggest_risk": biggest_risk,
            "passive_income_monthly_brl": round(float(Decimal(str(passive_ttm)) / 12), 2),
            "underperformers": under_labels,
            "total_assets": len(active),
            "sector_concentration": f"{biggest_sector_pct:.0f}% em {biggest_sector}",
            "asset_concentration": f"{biggest_asset_pct:.0f}% em {biggest_ticker}",
        }

        return {
            "health": health,
            "positions": positions,
            "pnl": pnl,
            "allocation": allocation,
        }

    except Exception as exc:
        logger.warning("_get_portfolio_data_sync failed: %s", exc)
        return None


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


@shared_task(name="advisor.refresh_universe_entry_signals", bind=False, max_retries=1)
def refresh_universe_entry_signals_batch() -> int:
    """Nightly Celery beat task: build entry signals for screener universe.

    Algorithm (no LLM — deterministic from ScreenerSnapshot data):
    1. Read top-100 tickers by market_cap from latest ScreenerSnapshot.
    2. Filter for buy candidates: variacao_12m_pct < -0.10 OR dy > 0.06.
    3. Map each ScreenerSnapshot row to EntrySignal with fixed timeframe/stop.
    4. Sort by best entry opportunity (deepest discount first, then highest DY).
    5. Store in Redis key "entry_signals:universe" with 24h TTL.

    Mapping ScreenerSnapshot → EntrySignal:
      ticker             → ticker
      variacao_12m_pct   → target_upside_pct (negate: deep discount = recovery potential)
      dy                 → included in scoring (used as proxy for income support)
      suggested_amount   → R$1,000 fixed default
      timeframe_days     → 90 (fixed swing-trade horizon)
      stop_loss_pct      → 8.0 (fixed standard stop)
    """
    try:
        from app.core.db_sync import get_sync_db_session
        from app.modules.market_universe.models import ScreenerSnapshot
        from app.modules.advisor.schemas import EntrySignal
        from datetime import datetime, timezone
        from sqlalchemy import func as sqlfunc

        with get_sync_db_session(None) as session:
            # Latest snapshot date
            latest_date = session.execute(
                select(sqlfunc.max(ScreenerSnapshot.snapshot_date))
            ).scalar()

            if latest_date is None:
                logger.warning("refresh_universe_entry_signals: no screener data")
                return 0

            # Top 100 by market_cap (largest, most liquid assets)
            top_snaps = session.execute(
                select(ScreenerSnapshot).where(
                    ScreenerSnapshot.snapshot_date == latest_date,
                    ScreenerSnapshot.market_cap.isnot(None),
                ).order_by(ScreenerSnapshot.market_cap.desc()).limit(100)
            ).scalars().all()

        if not top_snaps:
            logger.warning("refresh_universe_entry_signals: no snapshots found")
            return 0

        now = datetime.now(timezone.utc)
        signals: list[dict] = []

        for snap in top_snaps:
            var_12m = float(snap.variacao_12m_pct or 0)
            dy = float(snap.dy or 0)

            # Buy candidate filter: deep discount OR good dividend yield
            # variacao_12m_pct is fractional (e.g. -0.15 = -15%)
            is_discounted = var_12m < -0.10
            has_income = dy > 0.06

            if not (is_discounted or has_income):
                continue

            # target_upside_pct: if deeply discounted, recovery to zero = -var_12m
            # e.g. variacao_12m = -0.20 → target_upside = 20.0%
            target_upside = max(0.0, -var_12m * 100)

            signal_dict = EntrySignal(
                ticker=snap.ticker,
                suggested_amount_brl="1000.00",
                target_upside_pct=round(target_upside, 2),
                timeframe_days=90,
                stop_loss_pct=8.0,
                rsi=None,
                ma_signal="buy" if is_discounted else "neutral",
                generated_at=now,
            ).model_dump(mode="json")
            signals.append(signal_dict)

        # Sort: deepest discount first (highest target_upside_pct), then best DY
        signals.sort(key=lambda x: x["target_upside_pct"], reverse=True)

        # Store in Redis with 24h TTL
        r = _get_sync_redis()
        r.setex(
            "entry_signals:universe",
            86400,
            json.dumps(signals, default=str),
        )

        logger.info("refresh_universe_entry_signals: stored %d signals", len(signals))
        return len(signals)

    except Exception as exc:
        logger.error("refresh_universe_entry_signals_batch failed: %s", exc)
        raise


@shared_task(name="advisor.run_analysis", bind=True, max_retries=0)
def run_analysis(self, job_id: str, tenant_id: str, use_free_tier: bool = False) -> None:
    """Run AI portfolio analysis using run_portfolio_advisor() skill.

    Steps:
    1. Set job status → running
    2. Collect portfolio data synchronously (positions, pnl, allocation, health)
    3. Fetch macro rates from Redis
    4. Call run_portfolio_advisor() async (asyncio.run)
    5. Store structured result in result_json
    6. Mark completed / failed
    """
    logger.info("Advisor analysis started: job=%s tenant=%s", job_id, tenant_id)
    _update_advisor_job(job_id, "running")

    try:
        from app.modules.ai.skills.portfolio_advisor import run_portfolio_advisor

        portfolio_data = _get_portfolio_data_sync(tenant_id)
        if not portfolio_data:
            _update_advisor_job(job_id, "failed", error="Portfólio vazio — nenhuma transação encontrada")
            return

        health = portfolio_data["health"]
        macro = _get_macro()

        last_error = None
        advisor_result = None

        for attempt in range(3):
            try:
                if attempt > 0:
                    logger.info("Advisor retry %d for job %s", attempt, job_id)

                advisor_result = asyncio.run(run_portfolio_advisor(
                    positions=portfolio_data["positions"],
                    pnl=portfolio_data["pnl"],
                    allocation=portfolio_data["allocation"],
                    macro=macro,
                    tier="free" if use_free_tier else "paid",
                ))
                last_error = None
                break

            except Exception as exc:
                last_error = str(exc)
                logger.warning("Advisor attempt %d failed for job %s: %s", attempt + 1, job_id, exc)

        if last_error or not advisor_result:
            _update_advisor_job(job_id, "failed", error=f"After 3 attempts: {last_error}")
            return

        result = {
            "diagnostico": advisor_result.get("diagnostico", ""),
            "pontos_positivos": advisor_result.get("pontos_positivos", []),
            "pontos_de_atencao": advisor_result.get("pontos_de_atencao", []),
            "sugestoes": advisor_result.get("sugestoes", []),
            "proximos_passos": advisor_result.get("proximos_passos", []),
            "disclaimer": advisor_result.get("disclaimer", ""),
            # Health snapshot (for context in UI)
            "health_score": health["health_score"],
            "biggest_risk": health.get("biggest_risk"),
            "passive_income_monthly_brl": str(health.get("passive_income_monthly_brl", "0")),
            "underperformers": health.get("underperformers", []),
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }

        _update_advisor_job(job_id, "completed", result_json=json.dumps(result, ensure_ascii=False))
        logger.info("Advisor analysis completed: job=%s", job_id)

    except Exception as exc:
        logger.error("Advisor task unhandled error for job %s: %s", job_id, exc)
        _update_advisor_job(job_id, "failed", error=str(exc)[:500])
