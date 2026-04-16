"""Dashboard Celery tasks — portfolio EOD snapshot.

snapshot_portfolio_daily_value:
  Runs at 18h30 BRT (after B3 closes at 17h30).
  For every active tenant with at least one position:
  1. Reads all their buy/sell transactions (sync DB)
  2. Reads current prices from Redis (batch MGET)
  3. Computes total_value (current prices × quantity) and total_invested (CMP × quantity)
  4. Upserts one row in portfolio_daily_value for today

Design decisions:
- Uses UPSERT (INSERT ... ON CONFLICT DO UPDATE) so re-running on the same day
  overwrites the snapshot with the latest prices instead of failing.
- Tickers with no Redis quote fall back to CMP (cost basis) for total_value,
  setting data_stale implicitly. This avoids under-counting portfolio value
  when brapi quotes are stale.
- No asyncpg: sync psycopg2 + sync redis — correct for Celery worker context.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

import redis as sync_redis
from celery import shared_task
from sqlalchemy import text

from app.core.db_sync import get_sync_db_session, get_superuser_sync_db_session

logger = logging.getLogger(__name__)


def _get_redis() -> sync_redis.Redis:
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    return sync_redis.Redis.from_url(url, decode_responses=True)


def _parse_price(raw: str | None) -> Decimal | None:
    if not raw:
        return None
    try:
        data = json.loads(raw)
        price = data.get("price") or data.get("regularMarketPrice")
        return Decimal(str(price)) if price is not None else None
    except Exception:
        return None


def _get_all_active_tenants(session) -> list[str]:
    """Return distinct tenant_ids that have at least one non-deleted buy transaction."""
    rows = session.execute(text(
        "SELECT DISTINCT tenant_id FROM transactions "
        "WHERE transaction_type IN ('buy', 'sell') AND deleted_at IS NULL"
    )).fetchall()
    return [r[0] for r in rows]


def _get_tenant_positions(session, tenant_id: str) -> list[dict]:
    """Compute current positions for a tenant using raw SQL CMP logic.

    Returns list of {ticker, quantity, cmp, total_cost} for non-zero positions.
    This is a simplified version of the Python CMP engine using pure SQL aggregation.
    CMP = total_cost / total_quantity (FIFO approximation at batch level).
    """
    rows = session.execute(text("""
        SELECT
            ticker,
            SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE -quantity END) AS net_qty,
            SUM(CASE WHEN transaction_type = 'buy' THEN total_value ELSE 0 END) AS total_bought,
            SUM(CASE WHEN transaction_type = 'sell' THEN total_value ELSE 0 END) AS total_sold
        FROM transactions
        WHERE tenant_id = :tid
          AND transaction_type IN ('buy', 'sell')
          AND deleted_at IS NULL
        GROUP BY ticker
        HAVING SUM(CASE WHEN transaction_type = 'buy' THEN quantity ELSE -quantity END) > 0
    """), {"tid": tenant_id}).fetchall()

    positions = []
    for r in rows:
        ticker, net_qty, total_bought, total_sold = r
        net_qty = Decimal(str(net_qty))
        total_bought = Decimal(str(total_bought or 0))
        if net_qty <= 0:
            continue
        # CMP = remaining cost basis / remaining qty
        cmp = total_bought / net_qty if net_qty > 0 else Decimal("0")
        positions.append({
            "ticker": str(ticker),
            "quantity": net_qty,
            "cmp": cmp,
            "total_cost": cmp * net_qty,
        })
    return positions


@shared_task(name="app.modules.dashboard.tasks.snapshot_portfolio_daily_value")
def snapshot_portfolio_daily_value() -> None:
    """Compute and store EOD portfolio value snapshot for all active tenants."""
    today = date.today()
    r = _get_redis()

    with get_superuser_sync_db_session() as session:
        tenants = _get_all_active_tenants(session)

    if not tenants:
        logger.info("snapshot_portfolio_daily_value: no active tenants")
        return

    logger.info("snapshot_portfolio_daily_value: processing %d tenants for %s", len(tenants), today)

    # Collect all unique tickers across all tenants for batch Redis read
    all_positions: dict[str, list[dict]] = {}
    all_tickers: set[str] = set()

    with get_superuser_sync_db_session() as session:
        for tenant_id in tenants:
            positions = _get_tenant_positions(session, tenant_id)
            all_positions[tenant_id] = positions
            for p in positions:
                all_tickers.add(p["ticker"].upper())

    # Batch-read all prices in ONE Redis MGET call
    if all_tickers:
        ticker_list = list(all_tickers)
        keys = [f"market:quote:{t}" for t in ticker_list]
        raw_values = r.mget(keys)
        price_map: dict[str, Decimal | None] = {
            ticker: _parse_price(raw)
            for ticker, raw in zip(ticker_list, raw_values)
        }
    else:
        price_map = {}

    # Compute and upsert snapshot per tenant
    snapshots_saved = 0
    with get_superuser_sync_db_session() as session:
        for tenant_id, positions in all_positions.items():
            if not positions:
                continue

            total_value = Decimal("0")
            total_invested = Decimal("0")

            for p in positions:
                ticker = p["ticker"].upper()
                qty = p["quantity"]
                cmp = p["cmp"]
                price = price_map.get(ticker)

                # Fall back to CMP if Redis quote is stale/missing
                effective_price = price if price is not None and price > 0 else cmp
                total_value += effective_price * qty
                total_invested += cmp * qty

            if total_value <= 0:
                continue

            # UPSERT: update if same tenant+date already exists (re-run safety)
            session.execute(text("""
                INSERT INTO portfolio_daily_value
                    (id, tenant_id, snapshot_date, total_value, total_invested, created_at)
                VALUES
                    (:id, :tid, :date, :val, :invested, :now)
                ON CONFLICT (tenant_id, snapshot_date)
                DO UPDATE SET
                    total_value = EXCLUDED.total_value,
                    total_invested = EXCLUDED.total_invested
            """), {
                "id": str(uuid.uuid4()),
                "tid": tenant_id,
                "date": today,
                "val": total_value.quantize(Decimal("0.01")),
                "invested": total_invested.quantize(Decimal("0.01")),
                "now": datetime.now(tz=timezone.utc),
            })
            snapshots_saved += 1

    logger.info(
        "snapshot_portfolio_daily_value: saved %d/%d snapshots for %s",
        snapshots_saved, len(tenants), today,
    )
