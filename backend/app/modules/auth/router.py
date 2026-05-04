"""FastAPI router for all /auth/* endpoints.

Register in app/main.py:
    from app.modules.auth.router import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["auth"])
"""

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import clear_auth_cookies, set_auth_cookies
from app.modules.auth.schemas import (
    ErrorResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
)
from app.modules.auth.service import AuthService, brevo_email_sender

router = APIRouter()


def _get_service(db: AsyncSession = Depends(get_db)) -> AuthService:
    """Production dependency — uses real Brevo email sender."""
    return AuthService(db, email_sender=brevo_email_sender)


# ---------------------------------------------------------------------------
# AUTH-01: Registration
# ---------------------------------------------------------------------------
@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=RegisterResponse,
)
async def register(
    body: RegisterRequest,
    service: AuthService = Depends(_get_service),
):
    """Register a new user. Sends verification email."""
    try:
        result = await service.register(body.email, body.password)
        return result
    except ValueError as e:
        if "already registered" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"error": str(e)},
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": str(e)})


# ---------------------------------------------------------------------------
# AUTH-02: Email verification
# ---------------------------------------------------------------------------
@router.get("/verify-email", response_model=MessageResponse)
async def verify_email(
    token: str,
    service: AuthService = Depends(_get_service),
):
    """Verify email address via one-click token link."""
    try:
        result = await service.verify_email(token)
        return result
    except ValueError as e:
        if "expired" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"error": str(e)},
            )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": str(e)})


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    body: ResendVerificationRequest,
    service: AuthService = Depends(_get_service),
):
    """Resend verification email. Rate limited to 3/hour per user."""
    try:
        return await service.resend_verification(body.email)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail={"error": str(e)})


# ---------------------------------------------------------------------------
# AUTH-03: Login, refresh, logout
# ---------------------------------------------------------------------------
@router.post("/login", response_model=MessageResponse)
async def login(
    body: LoginRequest,
    response: Response,
    service: AuthService = Depends(_get_service),
):
    """Login with email+password. Sets httpOnly cookies on success."""
    try:
        tokens = await service.login(body.email, body.password)
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return {"message": "Logged in successfully"}
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": str(e), "is_verified": False},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": str(e)},
        )


@router.post("/refresh", response_model=MessageResponse)
async def refresh_token(
    response: Response,
    refresh_token: str = Cookie(default=None),
    service: AuthService = Depends(_get_service),
):
    """Rotate refresh token. Issues new access+refresh cookies."""
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": "No refresh token"},
        )
    try:
        tokens = await service.refresh(refresh_token)
        set_auth_cookies(response, tokens["access_token"], tokens["refresh_token"])
        return {"message": "Tokens refreshed"}
    except PermissionError as e:
        # Token reuse detected — clear cookies
        clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": str(e)},
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": str(e)},
        )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str = Cookie(default=None),
    service: AuthService = Depends(_get_service),
):
    """Logout — revokes refresh token and clears cookies."""
    await service.logout(refresh_token)
    clear_auth_cookies(response)
    return {"message": "Logged out"}


# ---------------------------------------------------------------------------
# AUTH-04: Password reset
# ---------------------------------------------------------------------------
@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    """Send password reset email. Always returns 200 — no user enumeration."""
    return await service.forgot_password(body.email)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    service: AuthService = Depends(_get_service),
):
    """Reset password using a valid token."""
    try:
        return await service.reset_password(body.token, body.new_password)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": str(e)},
        )
