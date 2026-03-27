"""Schemas for /simulador endpoints (Phase 10 — SIM-01, SIM-02, SIM-03)."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

CVM_DISCLAIMER = (
    "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"
)

HOLDING_PERIODS: dict[str, int] = {"6m": 180, "1a": 365, "2a": 730, "5a": 1825}

PrazoLabel = Literal["6m", "1a", "2a", "5a"]
PerfilLabel = Literal["conservador", "moderado", "arrojado"]


class SimuladorRequest(BaseModel):
    valor: float = Field(..., gt=0, description="Valor disponível para investir (R$)")
    prazo: PrazoLabel = Field(..., description="Prazo do investimento: 6m | 1a | 2a | 5a")
    perfil: PerfilLabel = Field(..., description="Perfil de risco: conservador | moderado | arrojado")


class AllocationClass(BaseModel):
    pct: Decimal
    valor: Decimal


class AllocationBreakdown(BaseModel):
    acoes: AllocationClass
    fiis: AllocationClass
    renda_fixa: AllocationClass
    caixa: AllocationClass


class ClassResult(BaseModel):
    asset_class: str       # acoes | fiis | renda_fixa | caixa
    label: str
    pct_alocado: Decimal
    valor_alocado: Decimal
    retorno_bruto_pct: Decimal
    ir_rate_pct: Decimal
    retorno_liquido_pct: Decimal
    valor_final: Decimal
    is_exempt: bool


class Cenario(BaseModel):
    nome: str              # Pessimista | Base | Otimista
    key: str               # pessimista | base | otimista
    total_investido: Decimal
    total_bruto: Decimal
    total_liquido: Decimal
    retorno_bruto_pct: Decimal
    retorno_liquido_pct: Decimal
    classes: list[ClassResult]


class CurrentClassAllocation(BaseModel):
    pct: Decimal
    valor: Decimal


class RebalancingItem(BaseModel):
    asset_class: str
    label: str
    current_pct: Decimal
    ideal_pct: Decimal
    delta_pct: Decimal
    action: str            # adicionar | reduzir | manter
    valor_delta: Decimal   # amount to add/remove (always positive)


class PortfolioDelta(BaseModel):
    total_portfolio: Decimal
    current_allocation: dict[str, CurrentClassAllocation]
    rebalancing: list[RebalancingItem]


class SimuladorResponse(BaseModel):
    perfil: str
    prazo: str
    holding_days: int
    valor_inicial: Decimal
    disclaimer: str = CVM_DISCLAIMER
    allocation: AllocationBreakdown
    cenarios: list[Cenario]
    portfolio_delta: PortfolioDelta | None = None
    cdi_annual_pct: Decimal | None = None
