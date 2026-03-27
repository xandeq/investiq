"""Investor Profile router.

Endpoints:
  GET  /profile  — return current investor profile (404 if not configured yet)
  POST /profile  — create or update investor profile (upsert)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.modules.profile.models import InvestorProfile
from app.modules.profile.schemas import InvestorProfileResponse, InvestorProfileUpsert

router = APIRouter()

_PROFILE_FIELDS = [
    "idade", "renda_mensal", "patrimonio_total",
    "objetivo", "horizonte_anos", "tolerancia_risco", "percentual_renda_fixa_alvo",
]


def _compute_completion(profile: InvestorProfile) -> int:
    """Return completion percentage based on filled optional fields."""
    filled = sum(1 for f in _PROFILE_FIELDS if getattr(profile, f) is not None)
    return round(filled / len(_PROFILE_FIELDS) * 100)


def _to_response(profile: InvestorProfile) -> InvestorProfileResponse:
    resp = InvestorProfileResponse.model_validate(profile)
    resp.completion_pct = _compute_completion(profile)
    return resp


@router.get("", response_model=InvestorProfileResponse)
async def get_profile(
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> InvestorProfileResponse:
    """Return the investor profile for the authenticated tenant.

    Returns 404 if the profile has not been created yet.
    """
    result = await db.execute(
        select(InvestorProfile).where(InvestorProfile.tenant_id == tenant_id)
    )
    profile = result.scalar_one_or_none()
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não configurado.")
    return _to_response(profile)


@router.post("", response_model=InvestorProfileResponse)
async def upsert_profile(
    data: InvestorProfileUpsert,
    db: AsyncSession = Depends(get_authed_db),
    tenant_id: str = Depends(get_current_tenant_id),
) -> InvestorProfileResponse:
    """Create or update the investor profile.

    If the profile does not exist, it is created.
    If it exists, only the provided fields are updated (partial update via model_dump).
    """
    result = await db.execute(
        select(InvestorProfile).where(InvestorProfile.tenant_id == tenant_id)
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        profile = InvestorProfile(tenant_id=tenant_id)
        db.add(profile)

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    await db.flush()
    return _to_response(profile)
