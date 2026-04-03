"""Analysis history retrieval and version diffing (Phase 15).

Provides:
- get_analysis_history(): retrieve past completed/stale analyses for a tenant+ticker
- compute_analysis_diff(): compute human-readable diff between two analysis results
- get_completeness_flag(): convert data_completeness % to green/yellow/red
"""
from __future__ import annotations

import json
import logging
from datetime import datetime

from sqlalchemy import select

from app.core.db_sync import get_superuser_sync_db_session
from app.modules.analysis.models import AnalysisJob

logger = logging.getLogger(__name__)


def get_completeness_flag(completeness_dict: dict) -> str:
    """Return green/yellow/red based on data completeness percentage.

    Thresholds: green >= 80%, yellow >= 50%, red < 50%.
    Returns red on missing or unparseable completeness value.
    """
    try:
        pct_str = completeness_dict.get("completeness", "0%")
        pct = int(str(pct_str).rstrip("%"))
    except (ValueError, TypeError):
        return "red"

    if pct >= 80:
        return "green"
    elif pct >= 50:
        return "yellow"
    return "red"


def get_analysis_history(
    ticker: str,
    tenant_id: str,
    analysis_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Return past completed and stale analyses for a tenant+ticker combination.

    Tenant-scoped: NEVER returns other tenants' data.
    Ordered by completed_at descending (newest first).

    Args:
        ticker: Stock ticker (e.g. "PETR4"). Case-insensitive (normalized to upper).
        tenant_id: Authenticated tenant ID — always required.
        analysis_type: Optional filter ("dcf"|"earnings"|"dividend"|"sector").
        limit: Max number of records to return (default 10, max 50).

    Returns:
        List of dicts with keys: job_id, analysis_type, status, completed_at,
        data_timestamp, data_version_id, result (parsed JSON or None).
    """
    limit = min(limit, 50)

    with get_superuser_sync_db_session() as session:
        stmt = (
            select(AnalysisJob)
            .where(
                AnalysisJob.ticker == ticker.upper(),
                AnalysisJob.tenant_id == tenant_id,
                AnalysisJob.status.in_(["completed", "stale"]),
            )
        )
        if analysis_type:
            stmt = stmt.where(AnalysisJob.analysis_type == analysis_type)

        stmt = stmt.order_by(AnalysisJob.completed_at.desc()).limit(limit)
        rows = session.execute(stmt).scalars().all()

    return [
        {
            "job_id": row.id,
            "analysis_type": row.analysis_type,
            "ticker": row.ticker,
            "status": row.status,
            "completed_at": row.completed_at.isoformat() if row.completed_at else None,
            "data_timestamp": row.data_timestamp.isoformat() if row.data_timestamp else None,
            "data_version_id": row.data_version_id,
            "result": json.loads(row.result_json) if row.result_json else None,
        }
        for row in rows
    ]


# Metric keys to track per analysis_type for diffing
_DIFF_METRICS: dict[str, dict[str, str]] = {
    "dcf": {"fair_value": "Fair value"},
    "earnings": {"eps_cagr_5y": "EPS CAGR 5Y"},
    "dividend": {"current_yield": "Dividend yield", "payout_ratio": "Payout ratio"},
    "sector": {"peers_found": "Peers found"},
}


def compute_analysis_diff(
    old_result: dict, new_result: dict, analysis_type: str
) -> dict:
    """Compute human-readable diff between two analysis results.

    Only surfaces changes >= 1% to avoid noise from floating-point rounding.
    Skips fields where old_value is 0 (division by zero risk).

    Returns:
        {
            "changed_fields": [
                {"field": str, "old_value": float, "new_value": float,
                 "pct_change": float, "label": str}
            ],
            "summary": str
        }
    """
    changed = []
    metrics = _DIFF_METRICS.get(analysis_type, {})

    for field, label in metrics.items():
        old_val = old_result.get(field)
        new_val = new_result.get(field)

        if old_val is None or new_val is None:
            continue
        if old_val == 0:
            continue  # avoid ZeroDivisionError

        pct = round(((new_val - old_val) / abs(old_val)) * 100, 1)
        if abs(pct) < 1.0:
            continue  # suppress noise below 1%

        sign = "+" if pct > 0 else ""
        changed.append(
            {
                "field": field,
                "old_value": old_val,
                "new_value": new_val,
                "pct_change": pct,
                "label": f"{label} changed {sign}{pct}%",
            }
        )

    summary = "; ".join(c["label"] for c in changed) if changed else "No significant changes"
    return {"changed_fields": changed, "summary": summary}
