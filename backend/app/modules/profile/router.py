"""Investor Profile router.

Endpoints:
  GET  /profile                  — return current investor profile (404 if not configured yet)
  POST /profile                  — create or update investor profile (upsert)
  GET  /profile/email-prefs      — get email notification preferences
  PATCH /profile/email-prefs     — update email notification preferences
  GET  /profile/ai-mode          — get AI quality mode ("standard" | "ultra")
  PATCH /profile/ai-mode         — toggle AI quality mode (pro users only)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.middleware import get_authed_db, get_current_tenant_id
from app.core.security import get_current_user
from app.modules.auth.models import User
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


# ── Email preferences ──────────────────────────────────────────────────────────

class EmailPrefsResponse(BaseModel):
    email_digest_enabled: bool


class EmailPrefsUpdate(BaseModel):
    email_digest_enabled: bool


@router.get("/email-prefs", response_model=EmailPrefsResponse)
async def get_email_prefs(
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
) -> EmailPrefsResponse:
    """Return the current email notification preferences for the authenticated user."""
    result = await db.execute(
        select(User).where(User.id == current_user["user_id"])
    )
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return EmailPrefsResponse(email_digest_enabled=user.email_digest_enabled)


@router.patch("/email-prefs", response_model=EmailPrefsResponse)
async def update_email_prefs(
    data: EmailPrefsUpdate,
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
) -> EmailPrefsResponse:
    """Update email notification preferences.

    - email_digest_enabled: opt in/out of the weekly portfolio digest email
    """
    await db.execute(
        update(User)
        .where(User.id == current_user["user_id"])
        .values(email_digest_enabled=data.email_digest_enabled)
    )
    await db.flush()
    return EmailPrefsResponse(email_digest_enabled=data.email_digest_enabled)


# ── AI Mode preferences ────────────────────────────────────────────────────────

class AIModeResponse(BaseModel):
    ai_mode: str  # "standard" | "ultra"
    plan: str


class AIModeUpdate(BaseModel):
    ai_mode: str  # "standard" | "ultra"


@router.get("/ai-mode", response_model=AIModeResponse)
async def get_ai_mode(
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
) -> AIModeResponse:
    """Return the current AI quality mode for the authenticated user."""
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return AIModeResponse(
        ai_mode=getattr(user, "ai_mode", "standard") or "standard",
        plan=user.plan,
    )


@router.patch("/ai-mode", response_model=AIModeResponse)
async def update_ai_mode(
    data: AIModeUpdate,
    db: AsyncSession = Depends(get_authed_db),
    current_user: dict = Depends(get_current_user),
) -> AIModeResponse:
    """Toggle AI quality mode.

    - "standard": uses gpt-4o-mini / deepseek-chat (faster, lower cost)
    - "ultra": uses Claude Sonnet / GPT-4o / Perplexity / DeepSeek-R1 (best quality)

    Ultra mode is only available for pro plan users.
    """
    if data.ai_mode not in ("standard", "ultra"):
        raise HTTPException(status_code=400, detail="ai_mode deve ser 'standard' ou 'ultra'.")

    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if data.ai_mode == "ultra" and user.plan != "pro":
        raise HTTPException(
            status_code=403,
            detail="Modo Ultra requer plano Pro. Faça upgrade para acessar modelos premium.",
        )

    await db.execute(
        update(User)
        .where(User.id == current_user["user_id"])
        .values(ai_mode=data.ai_mode)
    )
    await db.flush()
    return AIModeResponse(ai_mode=data.ai_mode, plan=user.plan)
