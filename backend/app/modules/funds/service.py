"""FundsService — CVM fund search, info lookup, and position enrichment."""
from __future__ import annotations

import csv
import io
import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal

import requests
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.funds.models import FundInfo, FundQuote
from app.modules.funds.schemas import FundPosition, FundSearchResult

logger = logging.getLogger(__name__)

_CVM_CAD_URL = "https://dados.cvm.gov.br/dados/FI/CAD/DADOS/cad_fi.csv"
_CVM_INF_DIARIO_BASE = "https://dados.cvm.gov.br/dados/FI/DOC/INF_DIARIO/DADOS"
_FUND_NAV_REDIS_PREFIX = "fund:nav:"
_FUND_REGISTRY_REDIS_KEY = "fund:registry:cache"
_FUND_REGISTRY_TTL = 86400  # 24h


def normalize_cnpj(raw: str) -> str:
    """Strip formatting from CNPJ, returning 14 raw digits."""
    return re.sub(r"[^\d]", "", raw)


def format_cnpj(digits: str) -> str:
    """Format 14-digit CNPJ as XX.XXX.XXX/XXXX-XX."""
    d = digits.zfill(14)
    return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:14]}"


class FundsService:
    """Handles CVM fund registry lookups and position enrichment."""

    # ------------------------------------------------------------------ #
    # Fund search                                                          #
    # ------------------------------------------------------------------ #

    async def search_funds(
        self, db: AsyncSession, q: str, limit: int = 20
    ) -> list[FundSearchResult]:
        """Search fund_info table by name fragment or CNPJ."""
        q_clean = q.strip()
        if not q_clean:
            return []

        # Try CNPJ search first (if query looks numeric)
        cnpj_digits = re.sub(r"[^\d]", "", q_clean)
        if len(cnpj_digits) >= 8:
            result = await db.execute(
                select(FundInfo)
                .where(FundInfo.cnpj.like(f"{cnpj_digits}%"))
                .where(FundInfo.status == "EM FUNCIONAMENTO NORMAL")
                .limit(limit)
            )
            rows = result.scalars().all()
            if rows:
                return [FundSearchResult(cnpj=r.cnpj, name=r.name, admin=r.admin, fund_class=r.fund_class) for r in rows]

        # Full-text name search
        result = await db.execute(
            select(FundInfo)
            .where(FundInfo.name.ilike(f"%{q_clean}%"))
            .where(FundInfo.status == "EM FUNCIONAMENTO NORMAL")
            .order_by(FundInfo.name)
            .limit(limit)
        )
        rows = result.scalars().all()
        return [FundSearchResult(cnpj=r.cnpj, name=r.name, admin=r.admin, fund_class=r.fund_class) for r in rows]

    async def get_fund_info(self, db: AsyncSession, cnpj: str) -> FundInfo | None:
        """Return fund info for a given CNPJ (14 digits)."""
        cnpj = normalize_cnpj(cnpj)
        result = await db.execute(select(FundInfo).where(FundInfo.cnpj == cnpj))
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Fund positions (enriched with NAV from Redis)                       #
    # ------------------------------------------------------------------ #

    async def get_fund_positions(
        self, db: AsyncSession, tenant_id: str, redis_client=None
    ) -> list[FundPosition]:
        """Return fund positions enriched with current NAV from Redis."""
        from app.modules.portfolio.models import Transaction
        from app.modules.portfolio.cmp import build_position_from_history

        result = await db.execute(
            select(Transaction).where(
                Transaction.tenant_id == tenant_id,
                Transaction.asset_class == "fundo",
                Transaction.transaction_type.in_(["buy", "sell"]),
                Transaction.deleted_at.is_(None),
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()

        # Group by CNPJ
        by_cnpj: dict[str, list] = {}
        for tx in txs:
            by_cnpj.setdefault(tx.ticker, []).append(tx)

        positions: list[FundPosition] = []
        for cnpj, cnpj_txs in by_cnpj.items():
            try:
                pos = build_position_from_history(cnpj, "fundo", cnpj_txs, [])
            except ValueError:
                continue
            if pos.quantity <= Decimal("0"):
                continue

            # Resolve fund name
            fund = await self.get_fund_info(db, cnpj)
            name = fund.name if fund else format_cnpj(cnpj)

            current_nav: Decimal | None = None
            nav_stale = True
            unrealized_pnl: Decimal | None = None
            unrealized_pnl_pct: Decimal | None = None
            quote_date: date | None = None

            if redis_client is not None:
                key = f"{_FUND_NAV_REDIS_PREFIX}{cnpj}"
                raw = await redis_client.get(key)
                if raw:
                    try:
                        data = json.loads(raw)
                        current_nav = Decimal(str(data["nav"]))
                        nav_stale = False
                        quote_date = date.fromisoformat(data["date"]) if data.get("date") else None
                        unrealized_pnl = (current_nav - pos.cmp) * pos.quantity
                        if pos.total_cost > Decimal("0"):
                            unrealized_pnl_pct = (unrealized_pnl / pos.total_cost) * Decimal("100")
                    except (KeyError, ValueError):
                        pass
                else:
                    # Fallback to DB
                    q_result = await db.execute(
                        select(FundQuote)
                        .where(FundQuote.cnpj == cnpj)
                        .order_by(FundQuote.quote_date.desc())
                        .limit(1)
                    )
                    fq = q_result.scalar_one_or_none()
                    if fq:
                        current_nav = Decimal(str(fq.nav_per_quota))
                        nav_stale = False
                        quote_date = fq.quote_date
                        unrealized_pnl = (current_nav - pos.cmp) * pos.quantity
                        if pos.total_cost > Decimal("0"):
                            unrealized_pnl_pct = (unrealized_pnl / pos.total_cost) * Decimal("100")

            positions.append(FundPosition(
                cnpj=cnpj,
                name=name,
                quantity=pos.quantity,
                cmp=pos.cmp,
                total_cost=pos.total_cost,
                current_nav=current_nav,
                nav_stale=nav_stale,
                unrealized_pnl=unrealized_pnl,
                unrealized_pnl_pct=unrealized_pnl_pct,
                quote_date=quote_date,
            ))

        return positions

    # ------------------------------------------------------------------ #
    # NAV lookup helper (used by portfolio service for position enrichment)#
    # ------------------------------------------------------------------ #

    @staticmethod
    async def get_fund_nav_from_redis(redis_client, cnpj: str) -> tuple[Decimal | None, bool]:
        """Return (nav, is_stale) for a fund CNPJ from Redis.

        Used by portfolio service to enrich fund positions.
        """
        key = f"{_FUND_NAV_REDIS_PREFIX}{cnpj}"
        raw = await redis_client.get(key)
        if not raw:
            return None, True
        try:
            data = json.loads(raw)
            return Decimal(str(data["nav"])), False
        except (KeyError, ValueError, TypeError):
            return None, True

    # ------------------------------------------------------------------ #
    # Celery-facing sync helpers (called from tasks.py)                   #
    # ------------------------------------------------------------------ #

    @staticmethod
    def fetch_cvm_registry_sync() -> list[dict]:
        """Download cad_fi.csv from CVM and return active fund records."""
        logger.info("Downloading CVM fund registry from %s", _CVM_CAD_URL)
        resp = requests.get(_CVM_CAD_URL, timeout=60)
        resp.raise_for_status()
        # CVM CSV is latin-1 encoded
        text_content = resp.content.decode("latin-1")
        reader = csv.DictReader(io.StringIO(text_content), delimiter=";")
        funds = []
        for row in reader:
            sit = row.get("SIT", "").strip()
            if sit != "EM FUNCIONAMENTO NORMAL":
                continue
            cnpj_raw = row.get("CNPJ_FUNDO", "").strip()
            cnpj = normalize_cnpj(cnpj_raw)
            if len(cnpj) != 14:
                continue
            funds.append({
                "cnpj": cnpj,
                "name": row.get("DENOM_SOCIAL", "").strip()[:256],
                "admin": (row.get("ADMIN", "") or "").strip()[:128],
                "fund_class": (row.get("CLASSE", "") or "").strip()[:64],
                "status": sit[:64],
            })
        logger.info("CVM registry: %d active funds", len(funds))
        return funds

    @staticmethod
    def fetch_cvm_quotes_for_cnpjs_sync(cnpjs: set[str]) -> dict[str, dict]:
        """Download current-month INF_DIARIO CSV and extract NAV for tracked CNPJs.

        Returns dict: {cnpj: {nav, date, net_assets}} for each matched CNPJ.
        Downloads previous month as fallback if today's month has no data yet.
        """
        from datetime import date as date_type

        results: dict[str, dict] = {}
        today = date_type.today()

        for year_month in [
            f"{today.year}{today.month:02d}",
            f"{today.year}{(today.month - 1) if today.month > 1 else 12:02d}" if today.month > 1
            else f"{today.year - 1}12",
        ]:
            url = f"{_CVM_INF_DIARIO_BASE}/inf_diario_fi_{year_month}.csv"
            try:
                logger.info("Fetching CVM daily quotes: %s", url)
                resp = requests.get(url, timeout=120, stream=True)
                if resp.status_code == 404:
                    continue
                resp.raise_for_status()

                text_content = resp.content.decode("latin-1")
                reader = csv.DictReader(io.StringIO(text_content), delimiter=";")

                for row in reader:
                    cnpj_raw = row.get("CNPJ_FUNDO", "").strip()
                    cnpj = normalize_cnpj(cnpj_raw)
                    if cnpj not in cnpjs:
                        continue
                    try:
                        nav = float(row.get("VL_QUOTA", "0").replace(",", "."))
                        net_assets_raw = row.get("VL_PATRIM_LIQ", "0").replace(",", ".")
                        net_assets = float(net_assets_raw) if net_assets_raw else 0.0
                        dt = row.get("DT_COMPTC", "").strip()
                        if cnpj not in results or dt > results[cnpj]["date"]:
                            results[cnpj] = {"nav": nav, "date": dt, "net_assets": net_assets}
                    except (ValueError, KeyError):
                        continue

                if results:
                    break  # Got data from current month

            except requests.RequestException as e:
                logger.warning("CVM quote fetch failed for %s: %s", year_month, e)
                continue

        return results
