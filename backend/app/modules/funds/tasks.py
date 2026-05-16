"""Celery tasks for CVM fund data refresh.

Two tasks:
  - refresh_fund_registry: daily, downloads cad_fi.csv → fund_info table
  - refresh_fund_quotes:   daily after market close, downloads INF_DIARIO CSV
                           for tracked CNPJs → fund_quotes table + Redis

Both run in sync Celery context (psycopg2, not asyncpg).
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

import psycopg2
import redis as redis_lib

from app.celery_app import celery_app
from app.modules.funds.service import FundsService

logger = logging.getLogger(__name__)


def _get_redis() -> redis_lib.Redis:
    url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
    return redis_lib.Redis.from_url(url)


def _get_db_conn():
    db_url = os.environ.get("DATABASE_URL", "")
    # asyncpg URL → psycopg2 URL
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


@celery_app.task(name="funds.refresh_fund_registry", bind=True, max_retries=3)
def refresh_fund_registry(self):
    """Download CVM fund registry (cad_fi.csv) and upsert into fund_info table.

    Runs once per day. On first run populates ~15k active funds.
    """
    try:
        funds = FundsService.fetch_cvm_registry_sync()
        if not funds:
            logger.warning("refresh_fund_registry: empty fund list from CVM")
            return {"status": "empty"}

        conn = _get_db_conn()
        cur = conn.cursor()
        upserted = 0
        for f in funds:
            cur.execute("""
                INSERT INTO fund_info (cnpj, name, admin, fund_class, status, updated_at)
                VALUES (%s, %s, %s, %s, %s, now())
                ON CONFLICT (cnpj) DO UPDATE SET
                    name = EXCLUDED.name,
                    admin = EXCLUDED.admin,
                    fund_class = EXCLUDED.fund_class,
                    status = EXCLUDED.status,
                    updated_at = now()
            """, (f["cnpj"], f["name"], f["admin"], f["fund_class"], f["status"]))
            upserted += 1

        conn.commit()
        cur.close()
        conn.close()
        logger.info("refresh_fund_registry: upserted %d funds", upserted)
        return {"status": "ok", "upserted": upserted}

    except Exception as exc:
        logger.error("refresh_fund_registry failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)


@celery_app.task(name="funds.refresh_fund_quotes", bind=True, max_retries=3)
def refresh_fund_quotes(self):
    """Refresh NAV quotes for all CNPJs currently held in portfolios.

    1. Query transactions table for distinct fund CNPJs.
    2. Download CVM INF_DIARIO CSV for current month.
    3. Upsert latest NAV into fund_quotes table.
    4. Write fund:nav:{cnpj} to Redis (TTL 48h).
    """
    try:
        conn = _get_db_conn()
        cur = conn.cursor()

        # Get all CNPJs currently held (fundo asset class)
        cur.execute("""
            SELECT DISTINCT ticker FROM transactions
            WHERE asset_class = 'fundo'
              AND deleted_at IS NULL
        """)
        cnpjs = {row[0] for row in cur.fetchall()}

        if not cnpjs:
            logger.info("refresh_fund_quotes: no tracked funds")
            cur.close()
            conn.close()
            return {"status": "ok", "funds": 0}

        quotes = FundsService.fetch_cvm_quotes_for_cnpjs_sync(cnpjs)

        r = _get_redis()
        updated = 0

        for cnpj, data in quotes.items():
            nav = data["nav"]
            dt = data["date"]
            net_assets = data.get("net_assets", 0.0)

            # Upsert into fund_quotes
            cur.execute("""
                INSERT INTO fund_quotes (id, cnpj, quote_date, nav_per_quota, net_assets_brl, updated_at)
                VALUES (gen_random_uuid()::text, %s, %s, %s, %s, now())
                ON CONFLICT (cnpj, quote_date) DO UPDATE SET
                    nav_per_quota = EXCLUDED.nav_per_quota,
                    net_assets_brl = EXCLUDED.net_assets_brl,
                    updated_at = now()
            """, (cnpj, dt, nav, net_assets))

            # Write to Redis (48h TTL — covers weekend gaps)
            r.setex(
                f"fund:nav:{cnpj}",
                172800,
                json.dumps({"nav": nav, "date": dt, "fetched_at": datetime.now(tz=timezone.utc).isoformat()}),
            )
            updated += 1

        conn.commit()
        cur.close()
        conn.close()
        logger.info("refresh_fund_quotes: updated %d CNPJs", updated)
        return {"status": "ok", "updated": updated}

    except Exception as exc:
        logger.error("refresh_fund_quotes failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
