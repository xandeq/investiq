"""Schemas for /wizard endpoints (Phase 11 — WIZ-01 through WIZ-05)."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

CVM_DISCLAIMER = (
    "Análise informativa — não constitui recomendação de investimento (CVM Res. 19/2021)"
)

HOLDING_PERIODS: dict[str, int] = {"6m": 180, "1a": 365, "2a": 730, "5a": 1825}

PrazoLabel = Literal["6m", "1a", "2a", "5a"]
PerfilLabel = Literal["conservador", "moderado", "arrojado"]


class WizardStartRequest(BaseModel):
    perfil: PerfilLabel
    prazo: PrazoLabel
    valor: float = Field(..., gt=0, description="Valor disponível para investir (R$)")


class WizardStartResponse(BaseModel):
    job_id: str
    status: str  # pending
    disclaimer: str = CVM_DISCLAIMER


class WizardAllocation(BaseModel):
    acoes_pct: float
    fiis_pct: float
    renda_fixa_pct: float
    caixa_pct: float
    rationale: str


class WizardPortfolioClass(BaseModel):
    pct: float
    valor: float


class WizardPortfolioContext(BaseModel):
    total: float
    acoes: WizardPortfolioClass
    fiis: WizardPortfolioClass
    renda_fixa: WizardPortfolioClass


class WizardDeltaItem(BaseModel):
    asset_class: str
    label: str
    current_pct: float
    suggested_pct: float
    delta_pct: float
    action: str        # adicionar | reduzir | manter
    valor_delta: float


class WizardResult(BaseModel):
    allocation: WizardAllocation
    macro: dict[str, str]
    portfolio_context: WizardPortfolioContext | None = None
    delta: list[WizardDeltaItem] | None = None
    provider_used: str | None = None
    completed_at: str | None = None


class WizardJobResponse(BaseModel):
    job_id: str
    status: str           # pending | running | completed | failed
    perfil: str
    prazo: str
    valor: float
    disclaimer: str = CVM_DISCLAIMER
    result: WizardResult | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
