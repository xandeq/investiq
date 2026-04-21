"""Recalibração semanal de pesos de padrões baseado em outcomes reais.

Pattern weights are stored in-memory (module-level dict) and also pushed
to Redis so that all Celery workers pick up the same weights.

Redis key: signal_engine:pattern_weights (JSON, no TTL — valid until next recal)
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default weights (mutable — updated by recalibrate_and_notify)
# ---------------------------------------------------------------------------

PATTERN_WEIGHTS: dict[str, float] = {
    "breakout": 1.0,
    "pullback_ema20": 1.0,
    "rsi_divergence": 1.0,
    "flag": 1.0,
    "oco": 1.0,
    "squeeze_bb": 1.0,
    "volume_climax": 1.0,
    "gap_fill": 1.0,
}

_REDIS_KEY = "signal_engine:pattern_weights"

# Thresholds
MIN_SAMPLES_TO_DISABLE = 30   # need N>=30 outcomes to disable a pattern
MIN_SAMPLES_TO_ADJUST = 10    # need N>=10 to apply a boost
DISABLE_THRESHOLD = 0.0       # expectancy < 0 with N>=30 → disable (weight=0.0)
BOOST_THRESHOLD = 0.5         # expectancy > 0.5 with N>=10 → boost (weight=1.2)
BOOST_WEIGHT = 1.2


# ---------------------------------------------------------------------------
# Weight retrieval
# ---------------------------------------------------------------------------

def get_pattern_weights(db_session=None) -> dict[str, float]:
    """Return pattern weights adjusted by expectancy from DB outcomes.

    Logic:
    - expectancy < 0 with samples >= MIN_SAMPLES_TO_DISABLE → weight = 0.0
    - expectancy > BOOST_THRESHOLD with samples >= MIN_SAMPLES_TO_ADJUST → weight = 1.2
    - otherwise → weight = 1.0

    Falls back to module-level PATTERN_WEIGHTS if db_session is None or query fails.
    Also checks Redis cache before hitting DB.
    """
    if db_session is None:
        return dict(PATTERN_WEIGHTS)

    # Try fetching expectancy data via outcome_tracker service (sync version)
    try:
        expectancy_data = _fetch_expectancy_sync(db_session)
    except Exception as exc:
        logger.warning("get_pattern_weights: DB query failed (%s) — using defaults", exc)
        return dict(PATTERN_WEIGHTS)

    weights = dict(PATTERN_WEIGHTS)  # start from defaults

    for pattern, stats in expectancy_data.items():
        exp = stats.get("expectancy", 0.0)
        n = stats.get("n", 0)

        if n >= MIN_SAMPLES_TO_DISABLE and exp < DISABLE_THRESHOLD:
            weights[pattern] = 0.0
            logger.info(
                "calibration: pattern '%s' DISABLED (expectancy=%.3f, n=%d)",
                pattern, exp, n,
            )
        elif n >= MIN_SAMPLES_TO_ADJUST and exp > BOOST_THRESHOLD:
            weights[pattern] = BOOST_WEIGHT
            logger.info(
                "calibration: pattern '%s' BOOSTED (expectancy=%.3f, n=%d)",
                pattern, exp, n,
            )

    return weights


def _fetch_expectancy_sync(db_session) -> dict[str, Any]:
    """Synchronous DB query for expectancy by pattern (aggregated across all tenants).

    Uses raw SQL to avoid asyncpg — called from Celery sync context.
    """
    result = db_session.execute(
        __import__("sqlalchemy").text(
            """
            SELECT pattern,
                   COUNT(*)::int                                  AS n,
                   AVG(CAST(r_multiple AS FLOAT))                AS expectancy,
                   SUM(CASE WHEN CAST(r_multiple AS FLOAT) > 0
                             THEN 1 ELSE 0 END)::FLOAT / COUNT(*) AS win_rate
            FROM signal_outcomes
            WHERE status = 'closed'
              AND r_multiple IS NOT NULL
              AND pattern IS NOT NULL
            GROUP BY pattern
            HAVING COUNT(*) >= 3
            """
        )
    )
    return {
        row[0]: {"n": row[1], "expectancy": float(row[2]), "win_rate": float(row[3])}
        for row in result.fetchall()
    }


# ---------------------------------------------------------------------------
# Recalibration task helper
# ---------------------------------------------------------------------------

def recalibrate_and_notify(
    redis_client=None,
    telegram_token: str = "",
    chat_id: str = "",
    db_session=None,
) -> dict:
    """Recalibrate pattern weights and push to Redis; notify via Telegram if changed.

    Steps:
    1. Calculate expectancy per pattern (all tenants, aggregated) from DB.
    2. Determine new weights (disable / boost / default).
    3. Push updated weights to Redis for all workers.
    4. Send Telegram notification if any pattern changed state.
    5. Return report dict with changes.

    Args:
        redis_client: Synchronous Redis client (optional — skips push if None).
        telegram_token: Telegram bot token (optional).
        chat_id: Telegram chat ID (optional).
        db_session: Sync SQLAlchemy session (optional — uses defaults if None).

    Returns:
        dict with keys: weights, disabled, boosted, errors.
    """
    report: dict = {
        "weights": {},
        "disabled": [],
        "boosted": [],
        "errors": [],
    }

    try:
        new_weights = get_pattern_weights(db_session=db_session)
        report["weights"] = new_weights

        # Identify changes
        for pattern, new_w in new_weights.items():
            old_w = PATTERN_WEIGHTS.get(pattern, 1.0)
            if new_w == 0.0 and old_w != 0.0:
                report["disabled"].append(pattern)
            elif new_w == BOOST_WEIGHT and old_w != BOOST_WEIGHT:
                report["boosted"].append(pattern)

        # Update in-memory weights
        PATTERN_WEIGHTS.update(new_weights)

        # Push to Redis
        if redis_client is not None:
            try:
                redis_client.set(_REDIS_KEY, json.dumps(new_weights))
                logger.info("calibration: pushed weights to Redis key %s", _REDIS_KEY)
            except Exception as exc:
                msg = f"Redis push failed: {exc}"
                logger.warning("calibration: %s", msg)
                report["errors"].append(msg)

        # Telegram notification if any pattern changed
        if (report["disabled"] or report["boosted"]) and telegram_token and chat_id:
            _send_calibration_alert(telegram_token, chat_id, report)

    except Exception as exc:
        msg = f"recalibrate_and_notify error: {exc}"
        logger.error("calibration: %s", msg)
        report["errors"].append(msg)

    return report


def _send_calibration_alert(token: str, chat_id: str, report: dict) -> None:
    """Send Telegram message summarising calibration changes."""
    import requests

    lines = ["<b>InvestIQ — Recalibracao de Padroes</b>", ""]
    if report["disabled"]:
        lines.append("Padroes DESABILITADOS (expectancy negativa):")
        for p in report["disabled"]:
            lines.append(f"  - {p}")
    if report["boosted"]:
        lines.append("Padroes com BOOST (expectancy > 0.5R):")
        for p in report["boosted"]:
            lines.append(f"  - {p}")

    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        resp = requests.post(
            url,
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("calibration: Telegram send failed: %s", exc)
