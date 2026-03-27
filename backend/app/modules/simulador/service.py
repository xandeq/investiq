"""Simulador de Alocação service — SIM-01, SIM-02, SIM-03.

Deterministic, AI-free allocation engine. No external API calls per request.
CDI fetched from Redis (set by Phase 2 macro Celery task).
TaxEngine loaded per-request from global DB (tax_config table).

Allocation profiles and expected return parameters are hardcoded constants
following the agreed sign-off from Phase 10 planning. A DB-driven config
can replace them in a future phase without any API changes.
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal, ROUND_HALF_UP
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.simulador.schemas import (
    AllocationBreakdown,
    AllocationClass,
    Cenario,
    ClassResult,
    CurrentClassAllocation,
    PortfolioDelta,
    RebalancingItem,
    SimuladorResponse,
    HOLDING_PERIODS,
    CVM_DISCLAIMER,
)
from app.modules.market_universe.models import TaxConfig
from app.modules.market_universe.tax_engine import TaxEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Allocation profiles — % per asset class (must sum to 100)
# ---------------------------------------------------------------------------

PROFILES: dict[str, dict[str, int]] = {
    "conservador": {"acoes": 5,  "fiis": 5,  "renda_fixa": 80, "caixa": 10},
    "moderado":    {"acoes": 20, "fiis": 15, "renda_fixa": 55, "caixa": 10},
    "arrojado":    {"acoes": 45, "fiis": 25, "renda_fixa": 25, "caixa":  5},
}

ASSET_LABELS: dict[str, str] = {
    "acoes":     "Ações",
    "fiis":      "FIIs",
    "renda_fixa": "Renda Fixa",
    "caixa":     "Caixa / DI",
}

# Expected gross annual returns (%) per scenario for equity-like classes.
# renda_fixa and caixa use CDI multipliers instead (see CDI_MULTIPLIERS).
FIXED_ANNUAL_RETURNS: dict[str, dict[str, Decimal]] = {
    "acoes": {
        "pessimista": Decimal("-5"),
        "base":       Decimal("10"),
        "otimista":   Decimal("25"),
    },
    "fiis": {
        "pessimista": Decimal("6"),
        "base":       Decimal("9"),
        "otimista":   Decimal("13"),
    },
}

# CDI multipliers for renda_fixa and caixa (applied to CDI annual rate)
CDI_MULTIPLIERS: dict[str, dict[str, Decimal]] = {
    "renda_fixa": {
        "pessimista": Decimal("0.85"),
        "base":       Decimal("1.00"),
        "otimista":   Decimal("1.05"),
    },
    "caixa": {
        "pessimista": Decimal("0.80"),
        "base":       Decimal("0.85"),
        "otimista":   Decimal("0.90"),
    },
}

# IR on equity gains (acoes): 15% capital gains (PF, not day-trade)
ACOES_IR = Decimal("15")

# Portfolio asset_class → simulator class mapping
PORTFOLIO_CLASS_MAP: dict[str, str] = {
    "acao":       "acoes",
    "bdr":        "acoes",
    "etf":        "acoes",
    "fii":        "fiis",
    "renda_fixa": "renda_fixa",
}

CENARIO_NAMES = {
    "pessimista": "Pessimista",
    "base":       "Base",
    "otimista":   "Otimista",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_redis():
    import redis as redis_lib
    return redis_lib.Redis.from_url(
        os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
        decode_responses=True,
    )


def _get_cdi_annual() -> Decimal | None:
    try:
        r = _get_redis()
        raw = r.get("market:macro:cdi")
        if raw:
            return Decimal(str(raw))
    except Exception as exc:
        logger.warning("_get_cdi_annual: Redis error: %s", exc)
    return None


def _compound_period(annual_pct: Decimal, holding_days: int) -> Decimal:
    """Compound annual rate to a period return: (1 + r)^(d/365) - 1 in %."""
    r = float(annual_pct) / 100
    compound = (1 + r) ** (holding_days / 365) - 1
    return Decimal(str(round(compound * 100, 4)))


def _d2(val: Decimal) -> Decimal:
    return val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Class result builder
# ---------------------------------------------------------------------------

def _build_class_result(
    asset_class: str,
    pct_alocado: int,
    valor_total: Decimal,
    annual_return_pct: Decimal,
    holding_days: int,
    engine: TaxEngine | None,
) -> ClassResult:
    valor_alocado = _d2(valor_total * Decimal(pct_alocado) / Decimal("100"))
    period_return = _compound_period(annual_return_pct, holding_days)

    if asset_class == "acoes":
        if period_return > 0:
            ir_rate = ACOES_IR
            net_return = period_return * (Decimal("1") - ACOES_IR / Decimal("100"))
        else:
            ir_rate = Decimal("0")
            net_return = period_return
        is_exempt = False
    elif asset_class == "fiis":
        ir_rate = Decimal("0")
        net_return = period_return
        is_exempt = True
    else:
        # renda_fixa or caixa — use TaxEngine IR regressivo
        if engine:
            try:
                ir_rate = engine.get_rate("renda_fixa", holding_days)
                net_return = engine.net_return(period_return, "renda_fixa", holding_days)
            except ValueError:
                ir_rate = Decimal("0")
                net_return = period_return
        else:
            ir_rate = Decimal("0")
            net_return = period_return
        is_exempt = False

    valor_final = _d2(valor_alocado * (Decimal("1") + net_return / Decimal("100")))

    return ClassResult(
        asset_class=asset_class,
        label=ASSET_LABELS[asset_class],
        pct_alocado=Decimal(pct_alocado),
        valor_alocado=valor_alocado,
        retorno_bruto_pct=_d2(period_return),
        ir_rate_pct=ir_rate,
        retorno_liquido_pct=_d2(net_return),
        valor_final=valor_final,
        is_exempt=is_exempt,
    )


# ---------------------------------------------------------------------------
# Cenario builder
# ---------------------------------------------------------------------------

def _build_cenario(
    key: str,
    perfil: str,
    valor: Decimal,
    holding_days: int,
    cdi_annual: Decimal | None,
    engine: TaxEngine | None,
) -> Cenario:
    profile = PROFILES[perfil]
    classes: list[ClassResult] = []

    for ac in ["acoes", "fiis", "renda_fixa", "caixa"]:
        pct = profile[ac]
        if pct == 0:
            # Build a zero-allocation row for completeness
            classes.append(ClassResult(
                asset_class=ac,
                label=ASSET_LABELS[ac],
                pct_alocado=Decimal("0"),
                valor_alocado=Decimal("0"),
                retorno_bruto_pct=Decimal("0"),
                ir_rate_pct=Decimal("0"),
                retorno_liquido_pct=Decimal("0"),
                valor_final=Decimal("0"),
                is_exempt=(ac == "fiis"),
            ))
            continue

        if ac in FIXED_ANNUAL_RETURNS:
            annual = FIXED_ANNUAL_RETURNS[ac][key]
        else:
            # CDI-based
            if cdi_annual:
                mult = CDI_MULTIPLIERS[ac][key]
                annual = cdi_annual * mult
            else:
                # Fallback: approximate CDI at 10.5% if Redis unavailable
                annual = Decimal("10.5") * CDI_MULTIPLIERS[ac][key]

        cr = _build_class_result(ac, pct, valor, annual, holding_days, engine)
        classes.append(cr)

    total_bruto = sum(cr.valor_final for cr in classes)
    total_liquido = total_bruto  # net is already computed per class
    retorno_bruto_pct = _d2((total_bruto - valor) / valor * Decimal("100"))
    retorno_liquido_pct = retorno_bruto_pct  # same since IR is per class

    return Cenario(
        nome=CENARIO_NAMES[key],
        key=key,
        total_investido=valor,
        total_bruto=_d2(total_bruto),
        total_liquido=_d2(total_liquido),
        retorno_bruto_pct=retorno_bruto_pct,
        retorno_liquido_pct=retorno_liquido_pct,
        classes=classes,
    )


# ---------------------------------------------------------------------------
# Portfolio delta builder — SIM-03
# ---------------------------------------------------------------------------

async def _get_portfolio_delta(
    tenant_db: AsyncSession,
    perfil: str,
    valor: Decimal,
) -> PortfolioDelta | None:
    try:
        from app.modules.portfolio.models import Transaction
        result = await tenant_db.execute(
            select(Transaction).where(
                Transaction.transaction_type.in_(["buy", "sell"]),
                Transaction.deleted_at.is_(None),
            )
        )
        txs = result.scalars().all()
        if not txs:
            return None

        # Compute net invested per simulator asset class
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

        # Filter to classes with positive investment
        total = sum(v for v in invested.values() if v > 0)
        if total <= 0:
            return None

        current_alloc: dict[str, CurrentClassAllocation] = {}
        for ac in ["acoes", "fiis", "renda_fixa", "caixa"]:
            inv = max(invested.get(ac, Decimal("0")), Decimal("0"))
            pct = _d2(inv / total * Decimal("100")) if total > 0 else Decimal("0")
            current_alloc[ac] = CurrentClassAllocation(pct=pct, valor=_d2(inv))

        profile = PROFILES[perfil]
        rebalancing: list[RebalancingItem] = []
        for ac in ["acoes", "fiis", "renda_fixa", "caixa"]:
            ideal_pct = Decimal(str(profile[ac]))
            curr_pct = current_alloc[ac].pct
            delta_pct = _d2(ideal_pct - curr_pct)
            valor_delta = _d2(abs(delta_pct) * valor / Decimal("100"))

            if delta_pct > Decimal("1"):
                action = "adicionar"
            elif delta_pct < Decimal("-1"):
                action = "reduzir"
            else:
                action = "manter"

            rebalancing.append(RebalancingItem(
                asset_class=ac,
                label=ASSET_LABELS[ac],
                current_pct=curr_pct,
                ideal_pct=ideal_pct,
                delta_pct=delta_pct,
                action=action,
                valor_delta=valor_delta,
            ))

        return PortfolioDelta(
            total_portfolio=_d2(total),
            current_allocation=current_alloc,
            rebalancing=rebalancing,
        )

    except Exception as exc:
        logger.warning("_get_portfolio_delta: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

async def build_simulation(
    valor: Decimal,
    prazo: str,
    perfil: str,
    global_db: AsyncSession,
    tenant_db: AsyncSession | None,
) -> SimuladorResponse:
    holding_days = HOLDING_PERIODS[prazo]

    # Load TaxEngine
    tax_rows = (await global_db.execute(select(TaxConfig))).scalars().all()
    engine = TaxEngine(tax_rows) if tax_rows else None

    # CDI from Redis
    cdi_annual = _get_cdi_annual()

    # Allocation breakdown
    profile = PROFILES[perfil]
    allocation = AllocationBreakdown(
        acoes=AllocationClass(
            pct=Decimal(profile["acoes"]),
            valor=_d2(valor * Decimal(profile["acoes"]) / Decimal("100")),
        ),
        fiis=AllocationClass(
            pct=Decimal(profile["fiis"]),
            valor=_d2(valor * Decimal(profile["fiis"]) / Decimal("100")),
        ),
        renda_fixa=AllocationClass(
            pct=Decimal(profile["renda_fixa"]),
            valor=_d2(valor * Decimal(profile["renda_fixa"]) / Decimal("100")),
        ),
        caixa=AllocationClass(
            pct=Decimal(profile["caixa"]),
            valor=_d2(valor * Decimal(profile["caixa"]) / Decimal("100")),
        ),
    )

    # 3 scenarios
    cenarios = [
        _build_cenario("pessimista", perfil, valor, holding_days, cdi_annual, engine),
        _build_cenario("base",       perfil, valor, holding_days, cdi_annual, engine),
        _build_cenario("otimista",   perfil, valor, holding_days, cdi_annual, engine),
    ]

    # Portfolio delta (SIM-03)
    portfolio_delta = None
    if tenant_db:
        portfolio_delta = await _get_portfolio_delta(tenant_db, perfil, valor)

    return SimuladorResponse(
        perfil=perfil,
        prazo=prazo,
        holding_days=holding_days,
        valor_inicial=valor,
        disclaimer=CVM_DISCLAIMER,
        allocation=allocation,
        cenarios=cenarios,
        portfolio_delta=portfolio_delta,
        cdi_annual_pct=cdi_annual,
    )
