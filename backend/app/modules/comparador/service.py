"""Comparador RF vs RV service — COMP-01, COMP-02.

Data sources (all pre-fetched, zero per-request external API calls):
  - RF catalog + TaxEngine  → fixed_income_catalog DB table (Phase 7/8)
  - Tesouro rates            → Redis tesouro:rates:* (Phase 7 beat task)
  - CDI annual rate          → Redis market:macro:cdi (Phase 2 beat task)
  - IBOVESPA historical      → brapi.dev ^BVSP, cached in Redis 24h
  - Portfolio return         → tenant DB (transactions)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.comparador.schemas import ComparadorRow, HOLDING_PERIODS
from app.modules.market_universe.models import FixedIncomeCatalog, TaxConfig
from app.modules.market_universe.tax_engine import TaxEngine

logger = logging.getLogger(__name__)

_IBOVESPA_CACHE_KEY = "comparador:ibovespa:returns"
_IBOVESPA_TTL = 86400  # 24h


def _get_redis():
    import redis as redis_lib
    return redis_lib.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )


def _safe_dec(val) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError):
        return None


# ---------------------------------------------------------------------------
# CDI — from Redis macro cache (set by refresh_macro Celery task)
# ---------------------------------------------------------------------------

def _get_cdi_annual() -> Decimal | None:
    try:
        r = _get_redis()
        raw = r.get("market:macro:cdi")
        return _safe_dec(raw)
    except Exception as exc:
        logger.warning("_get_cdi_annual: Redis error: %s", exc)
        return None


def _compound_return(annual_pct: Decimal, holding_days: int) -> Decimal:
    """Compound annual rate for holding_days: (1 + r)^(d/365) - 1 in %."""
    r = float(annual_pct) / 100
    compound = (1 + r) ** (holding_days / 365) - 1
    return Decimal(str(round(compound * 100, 4)))


# ---------------------------------------------------------------------------
# IBOVESPA — yfinance ^BVSP, Redis-cached 24h
# ---------------------------------------------------------------------------

def _compute_ibovespa_returns() -> dict[str, str | None]:
    """Fetch ^BVSP via brapi.dev and compute returns for all holding periods.

    yfinance is NOT used here — Yahoo Finance blocks ^BVSP from Brazilian IPs,
    returning empty responses that cause JSON parse errors in yfinance 0.2.x.
    brapi.dev is the canonical source for B3 market data in this project.
    """
    try:
        from app.modules.market_data.adapters.brapi import BrapiClient
        import pandas as pd

        client = BrapiClient()
        end = date.today()
        # Fetch 6 years to cover the longest holding period
        start = end - timedelta(days=365 * 6)
        points = client.fetch_historical("^BVSP", range="5y")

        if not points:
            logger.warning("IBOVESPA: brapi returned empty history for ^BVSP")
            return {k: None for k in HOLDING_PERIODS}

        # Build a date-indexed Series of closing prices
        closes = pd.Series(
            {pd.Timestamp(p["date"], unit="s").date(): p["close"] for p in points}
        ).sort_index()

        result: dict[str, str | None] = {}
        for label, days in HOLDING_PERIODS.items():
            cutoff = end - timedelta(days=days)
            subset = closes[closes.index >= cutoff]
            if subset.empty:
                result[label] = None
                continue
            start_price = float(subset.iloc[0])
            end_price = float(closes.iloc[-1])
            if start_price <= 0:
                result[label] = None
                continue
            pct = (end_price - start_price) / start_price * 100
            result[label] = str(round(pct, 4))
        return result
    except Exception as exc:
        logger.warning("_compute_ibovespa_returns: %s", exc)
        return {k: None for k in HOLDING_PERIODS}


def _get_ibovespa_returns() -> tuple[dict[str, Decimal | None], bool]:
    """Return (returns_dict, is_stale). Reads from Redis cache; recomputes if missing."""
    try:
        r = _get_redis()
        cached = r.get(_IBOVESPA_CACHE_KEY)
        if cached:
            raw = json.loads(cached)
            return {k: _safe_dec(v) for k, v in raw.items()}, False
    except Exception as exc:
        logger.warning("IBOVESPA cache read failed: %s", exc)

    # Recompute
    computed = _compute_ibovespa_returns()
    try:
        r = _get_redis()
        r.setex(_IBOVESPA_CACHE_KEY, _IBOVESPA_TTL, json.dumps(computed))
    except Exception as exc:
        logger.warning("IBOVESPA cache write failed: %s", exc)

    return {k: _safe_dec(v) for k, v in computed.items()}, True


# ---------------------------------------------------------------------------
# Tesouro rates — from Redis tesouro:rates:* (Phase 7)
# ---------------------------------------------------------------------------

def _get_best_tesouro_by_type() -> dict[str, dict]:
    """Return best (lowest vencimento) Tesouro rate per tipo_titulo from Redis."""
    try:
        r = _get_redis()
        keys = r.keys("tesouro:rates:*")
        by_type: dict[str, dict] = {}
        for key in keys:
            raw = r.get(key)
            if not raw:
                continue
            data = json.loads(raw)
            tipo = data.get("tipo_titulo", "")
            if not tipo:
                continue
            if tipo not in by_type:
                by_type[tipo] = data
            else:
                # Keep highest rate
                existing = _safe_dec(by_type[tipo].get("taxa_indicativa"))
                current = _safe_dec(data.get("taxa_indicativa"))
                if current and existing and current > existing:
                    by_type[tipo] = data
        return by_type
    except Exception as exc:
        logger.warning("_get_best_tesouro_by_type: %s", exc)
        return {}


# ---------------------------------------------------------------------------
# Portfolio return — COMP-02
# ---------------------------------------------------------------------------

async def _get_portfolio_return(
    db: AsyncSession, tenant_id: str
) -> tuple[Decimal | None, int | None]:
    """Compute (annualized_net_pct, holding_days) from user's portfolio.

    Returns (None, None) if portfolio is empty or too short.
    Annualized = (total_portfolio_value / total_invested) ^ (365/days) - 1
    """
    try:
        from app.modules.portfolio.models import Transaction
        result = await db.execute(
            select(Transaction).where(
                Transaction.transaction_type.in_(["buy", "sell"]),
                Transaction.deleted_at.is_(None),
            ).order_by(Transaction.transaction_date)
        )
        txs = result.scalars().all()
        if not txs:
            return None, None

        # Total invested (buys - sell proceeds)
        total_invested = Decimal("0")
        for tx in txs:
            cost = tx.quantity * tx.unit_price + (tx.brokerage_fee or Decimal("0"))
            if tx.transaction_type == "buy":
                total_invested += cost
            else:
                total_invested -= cost

        if total_invested <= 0:
            return None, None

        # Realized P&L
        realized = sum((tx.gross_profit or Decimal("0")) for tx in txs if tx.transaction_type == "sell")

        # Unrealized: we need current positions — approximation via total_value
        # Simple: total_return_pct = realized / total_invested (ignores unrealized)
        # Better: fetch from portfolio service is too expensive here; use realized only as proxy
        oldest_date = txs[0].transaction_date
        holding_days = (date.today() - oldest_date).days
        if holding_days < 30:
            return None, None

        # Annualized return
        total_return = float(realized / total_invested)
        annualized = ((1 + total_return) ** (365 / holding_days) - 1) * 100
        return Decimal(str(round(annualized, 4))), holding_days

    except Exception as exc:
        logger.warning("_get_portfolio_return: %s", exc)
        return None, None


# ---------------------------------------------------------------------------
# CDB equivalent (COMP-02)
# ---------------------------------------------------------------------------

def _cdb_equivalent(net_pct: Decimal, holding_days: int, engine: TaxEngine) -> Decimal | None:
    """Find gross CDB rate that yields net_pct after IR for holding_days.

    gross_cdb = net_pct / (1 - IR_rate/100)
    """
    try:
        ir_rate = engine.get_rate("renda_fixa", holding_days)
        if ir_rate >= Decimal("100"):
            return None
        gross = net_pct / (Decimal("1") - ir_rate / Decimal("100"))
        return gross.quantize(Decimal("0.01"))
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Main comparison builder
# ---------------------------------------------------------------------------

async def build_comparison(
    prazo: str,
    valor_inicial: Decimal | None,
    global_db: AsyncSession,
    tenant_db: AsyncSession | None,
    tenant_id: str | None,
) -> dict:
    holding_days = HOLDING_PERIODS[prazo]

    # Load TaxEngine
    tax_rows = (await global_db.execute(select(TaxConfig))).scalars().all()
    engine = TaxEngine(tax_rows) if tax_rows else None

    # Load RF catalog
    catalog_rows = (await global_db.execute(select(FixedIncomeCatalog))).scalars().all()

    rows: list[ComparadorRow] = []

    # ── 1. RF catalog rows (CDB, LCI, LCA) ──────────────────────────────────
    for cat in catalog_rows:
        # Filter for rows whose tenor covers holding_days
        min_days = cat.min_months * 30
        max_days = (cat.max_months * 30) if cat.max_months else None
        if holding_days < min_days:
            continue
        if max_days and holding_days > max_days:
            continue

        # Use mid-rate
        gross = cat.min_rate_pct
        if cat.max_rate_pct:
            gross = (cat.min_rate_pct + cat.max_rate_pct) / Decimal("2")

        asset_class_map = {"CDB": "renda_fixa", "LCI": "LCI", "LCA": "LCA"}
        ac = asset_class_map.get(cat.instrument_type, "renda_fixa")

        if engine:
            try:
                ir_rate = engine.get_rate(ac, holding_days)
                net = engine.net_return(gross, ac, holding_days)
                is_exempt = engine.is_exempt(ac)
            except ValueError:
                continue
        else:
            ir_rate = Decimal("0")
            net = gross
            is_exempt = False

        net_value = None
        if valor_inicial:
            net_value = valor_inicial * (Decimal("1") + net / Decimal("100"))
            net_value = net_value.quantize(Decimal("0.01"))

        risk = "Baixo"
        rows.append(ComparadorRow(
            label=cat.label,
            category=cat.instrument_type.lower(),
            gross_pct=gross,
            ir_rate_pct=ir_rate,
            net_pct=net,
            net_value=net_value,
            is_exempt=is_exempt,
            risk_label=risk,
            data_source="catalog",
            note="Taxa de referência de mercado" if not is_exempt else "Isento de IR (PF)",
        ))

    # ── 2. Tesouro Direto ───────────────────────────────────────────────────
    tesouro_by_type = _get_best_tesouro_by_type()
    for tipo, data in tesouro_by_type.items():
        taxa = _safe_dec(data.get("taxa_indicativa"))
        if not taxa:
            continue

        if engine:
            try:
                ir_rate = engine.get_rate("renda_fixa", holding_days)
                net = engine.net_return(taxa, "renda_fixa", holding_days)
            except ValueError:
                continue
        else:
            ir_rate = Decimal("22.50")
            net = taxa * Decimal("0.775")

        net_value = None
        if valor_inicial:
            net_value = (valor_inicial * (Decimal("1") + net / Decimal("100"))).quantize(Decimal("0.01"))

        rows.append(ComparadorRow(
            label=f"Tesouro {tipo}",
            category="tesouro",
            gross_pct=taxa,
            ir_rate_pct=ir_rate,
            net_pct=net,
            net_value=net_value,
            is_exempt=False,
            risk_label="Baixíssimo",
            data_source="redis",
            note=f"Venc. {data.get('vencimento', '')}",
        ))

    # ── 3. CDI (benchmark reference) ────────────────────────────────────────
    cdi_annual = _get_cdi_annual()
    if cdi_annual:
        cdi_compound = _compound_return(cdi_annual, holding_days)
        if engine:
            try:
                ir_rate_cdi = engine.get_rate("renda_fixa", holding_days)
                cdi_net = engine.net_return(cdi_compound, "renda_fixa", holding_days)
            except ValueError:
                ir_rate_cdi = Decimal("0")
                cdi_net = cdi_compound
        else:
            ir_rate_cdi = Decimal("0")
            cdi_net = cdi_compound

        net_value = None
        if valor_inicial:
            net_value = (valor_inicial * (Decimal("1") + cdi_net / Decimal("100"))).quantize(Decimal("0.01"))

        rows.append(ComparadorRow(
            label=f"CDI {prazo} (referência)",
            category="cdi",
            gross_pct=cdi_compound,
            ir_rate_pct=ir_rate_cdi,
            net_pct=cdi_net,
            net_value=net_value,
            is_exempt=False,
            risk_label="Baixíssimo",
            data_source="bcb",
            note=f"CDI a.a.: {cdi_annual:.2f}%",
        ))

    # ── 4. IBOVESPA histórico ───────────────────────────────────────────────
    ibov_returns, ibov_stale = _get_ibovespa_returns()
    ibov_net = ibov_returns.get(prazo)
    if ibov_net is not None:
        net_value = None
        if valor_inicial:
            net_value = (valor_inicial * (Decimal("1") + ibov_net / Decimal("100"))).quantize(Decimal("0.01"))

        rows.append(ComparadorRow(
            label=f"IBOVESPA histórico {prazo}",
            category="ibovespa",
            gross_pct=ibov_net,
            ir_rate_pct=Decimal("0"),
            net_pct=ibov_net,
            net_value=net_value,
            is_exempt=True,
            risk_label="Alto",
            data_source="yfinance",
            note="Retorno histórico — não garante retorno futuro",
        ))

    # ── 5. Carteira do usuário (COMP-02) ────────────────────────────────────
    portfolio_net: Decimal | None = None
    portfolio_cdb_eq: Decimal | None = None

    if tenant_db and tenant_id:
        port_return, port_days = await _get_portfolio_return(tenant_db, tenant_id)
        if port_return is not None:
            portfolio_net = port_return
            net_value = None
            if valor_inicial:
                # Annualized → holding_days
                period_return = _compound_return(portfolio_net, holding_days)
                net_value = (valor_inicial * (Decimal("1") + period_return / Decimal("100"))).quantize(Decimal("0.01"))
                period_net = period_return
            else:
                period_net = _compound_return(portfolio_net, holding_days)

            if engine:
                portfolio_cdb_eq = _cdb_equivalent(period_net, holding_days, engine)

            rows.append(ComparadorRow(
                label="Minha carteira (a.a.)",
                category="portfolio",
                gross_pct=portfolio_net,
                ir_rate_pct=None,
                net_pct=period_net,
                net_value=net_value,
                is_exempt=False,
                risk_label="Variável",
                data_source="portfolio",
                is_portfolio=True,
                note=f"Retorno anualizado · {port_days} dias de histórico",
            ))

    # ── Mark best net_pct row (excluding portfolio) ──────────────────────────
    best_category: str | None = None
    non_portfolio = [r for r in rows if not r.is_portfolio and r.net_pct is not None]
    if non_portfolio:
        best = max(non_portfolio, key=lambda r: r.net_pct)
        best.is_best = True
        best_category = best.category

    return {
        "rows": rows,
        "best_category": best_category,
        "portfolio_cdb_equivalent": portfolio_cdb_eq,
        "ibovespa_data_stale": ibov_stale,
        "cdi_annual_pct": cdi_annual,
    }
