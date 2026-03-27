"""Auth business logic — registration, verification, login, refresh, password reset.

EXT-03 compliance: email_sender is injected via constructor — never called directly.
This makes the email sending swappable in tests (pass a stub) without touching production code.

Production usage:
    from app.modules.auth.email import brevo_email_sender
    service = AuthService(db, email_sender=brevo_email_sender)

Test usage:
    sent = []
    service = AuthService(db, email_sender=lambda to, subject, html: sent.append((to, subject, html)))
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Callable, Optional

import httpx
import redis.asyncio as aioredis
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.modules.auth.models import RefreshToken, TokenStatus, User, VerificationToken

# Type alias for the email sender callable
EmailSender = Callable[[str, str, str], None]

VERIFICATION_TOKEN_EXPIRE_HOURS = 24
RESET_TOKEN_EXPIRE_HOURS = 1
RESEND_RATE_LIMIT = 3
RESEND_WINDOW_SECONDS = 3600  # 1 hour


def _make_verification_jwt(user_id: str, purpose: str, expire_hours: int) -> str:
    """Create a short-lived JWT for email verification or password reset."""
    import jwt as pyjwt
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": user_id,
        "purpose": purpose,
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(hours=expire_hours),
    }
    return pyjwt.encode(payload, settings.JWT_PRIVATE_KEY, algorithm="RS256")


def _decode_verification_jwt(token: str) -> dict:
    """Decode a verification JWT. Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError."""
    import jwt as pyjwt
    return pyjwt.decode(token, settings.JWT_PUBLIC_KEY, algorithms=["RS256"])


async def brevo_email_sender(to_email: str, subject: str, html_content: str) -> None:
    """Production Brevo email sender.

    Fetched lazily — Brevo credentials come from settings (injected via env at startup).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            headers={
                "api-key": settings.BREVO_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "sender": {
                    "name": settings.BREVO_FROM_NAME,
                    "email": settings.BREVO_FROM_EMAIL,
                },
                "to": [{"email": to_email}],
                "subject": subject,
                "htmlContent": html_content,
            },
            timeout=10.0,
        )
        response.raise_for_status()


class AuthService:
    """Auth business logic. email_sender is injected — supports EXT-03 adapter pattern."""

    def __init__(
        self,
        db: AsyncSession,
        email_sender: Optional[EmailSender] = None,
        redis_client=None,
    ):
        self.db = db
        # Default to production Brevo sender; tests inject a stub
        self.email_sender: EmailSender = email_sender or brevo_email_sender
        self._redis = redis_client

    async def _get_redis(self):
        """Lazily connect to Redis."""
        if self._redis is None:
            self._redis = await aioredis.from_url(settings.REDIS_URL)
        return self._redis

    # -----------------------------------------------------------------------
    # AUTH-01: Registration
    # -----------------------------------------------------------------------
    async def register(self, email: str, password: str) -> dict:
        """Register a new user. Returns {"user_id": str, "message": str}."""
        # Check for duplicate email
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        if result.scalar_one_or_none():
            raise ValueError("Email already registered")

        user_id = str(uuid.uuid4())
        trial_ends = datetime.now(tz=timezone.utc) + timedelta(days=14)
        user = User(
            id=user_id,
            tenant_id=user_id,  # v1: tenant_id == user.id
            email=email.lower(),
            hashed_password=hash_password(password),
            is_verified=False,
            trial_ends_at=trial_ends,
            trial_used=True,
        )
        self.db.add(user)
        await self.db.flush()  # Get ID without committing

        # Create and store verification token
        token = _make_verification_jwt(user_id, "verify", VERIFICATION_TOKEN_EXPIRE_HOURS)
        token_hash = hash_token(token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
        vt = VerificationToken(
            user_id=user_id,
            email=email.lower(),
            token_hash=token_hash,
            purpose="verify",
            expires_at=expires_at,
        )
        self.db.add(vt)
        await self.db.flush()

        # Send verification email — failure must not block registration
        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        html = (
            f"<p>Bem-vindo ao InvestIQ!</p>"
            f"<p><a href='{verify_url}'>Clique aqui para verificar seu email</a></p>"
            f"<p>Este link expira em 24 horas.</p>"
        )
        email_sent = True
        try:
            await self.email_sender(email, "Verifique seu email — InvestIQ", html)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error(
                "Failed to send verification email to %s: %s", email, exc
            )
            email_sent = False

        message = "Verification email sent" if email_sent else (
            "Account created. Email delivery is temporarily unavailable — "
            "please use 'Resend verification' on the login page to retry."
        )
        return {"user_id": user_id, "message": message}

    # -----------------------------------------------------------------------
    # AUTH-02: Email verification
    # -----------------------------------------------------------------------
    async def verify_email(self, token: str) -> dict:
        """Verify email via token link. Returns {"message": "Email verified"}."""
        try:
            payload = _decode_verification_jwt(token)
        except Exception as e:
            import jwt as pyjwt
            if isinstance(e, pyjwt.ExpiredSignatureError):
                raise ValueError("Verification link expired")
            raise ValueError("Invalid verification token")

        if payload.get("purpose") != "verify":
            raise ValueError("Invalid token purpose")

        token_hash = hash_token(token)
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.token_hash == token_hash,
                VerificationToken.purpose == "verify",
            )
        )
        vt = result.scalar_one_or_none()
        if not vt:
            raise ValueError("Verification token not found or already used")

        # Mark user as verified
        await self.db.execute(
            update(User).where(User.id == vt.user_id).values(is_verified=True)
        )
        # Remove used token
        await self.db.delete(vt)
        await self.db.flush()

        return {"message": "Email verified"}

    async def resend_verification(self, email: str) -> dict:
        """Resend verification email. Rate-limited to 3/hour via Redis."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()
        if not user or user.is_verified:
            # Silent success — no user enumeration
            return {"message": "If that email exists and is unverified, a new link was sent"}

        # Rate limit check via Redis
        redis = await self._get_redis()
        key = f"resend:{user.id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, RESEND_WINDOW_SECONDS)
        if count > RESEND_RATE_LIMIT:
            raise ValueError("Too many requests — try again in an hour")

        # Delete old verification tokens for this user
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.user_id == user.id,
                VerificationToken.purpose == "verify",
            )
        )
        for old_vt in result.scalars().all():
            await self.db.delete(old_vt)

        # Create new token
        token = _make_verification_jwt(user.id, "verify", VERIFICATION_TOKEN_EXPIRE_HOURS)
        token_hash = hash_token(token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=VERIFICATION_TOKEN_EXPIRE_HOURS)
        vt = VerificationToken(
            user_id=user.id,
            email=email.lower(),
            token_hash=token_hash,
            purpose="verify",
            expires_at=expires_at,
        )
        self.db.add(vt)
        await self.db.flush()

        verify_url = f"{settings.APP_URL}/verify-email?token={token}"
        html = (
            f"<p>Novo link de verificação InvestIQ</p>"
            f"<p><a href='{verify_url}'>Verificar email</a></p>"
            f"<p>Este link expira em 24 horas.</p>"
        )
        try:
            await self.email_sender(email, "Novo link de verificação — InvestIQ", html)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Failed to resend verification email to %s: %s", email, exc)
        return {"message": "If that email exists and is unverified, a new link was sent"}

    # -----------------------------------------------------------------------
    # AUTH-03: Login, refresh, logout
    # -----------------------------------------------------------------------
    async def login(self, email: str, password: str) -> dict:
        """Login. Returns {access_token, refresh_token} or raises ValueError."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        if not user or not verify_password(password, user.hashed_password):
            raise ValueError("Invalid credentials")

        if not user.is_verified:
            raise PermissionError("Email not verified")

        access_token = create_access_token(user.id, user.tenant_id)
        refresh_token = create_refresh_token(user.id)

        token_hash = hash_token(refresh_token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(days=7)
        rt = RefreshToken(
            user_id=user.id,
            token_hash=token_hash,
            status=TokenStatus.active,
            expires_at=expires_at,
        )
        self.db.add(rt)
        await self.db.flush()

        return {"access_token": access_token, "refresh_token": refresh_token}

    async def refresh(self, refresh_token: str) -> dict:
        """Rotate refresh token. Detects reuse and revokes all tokens on reuse."""
        try:
            payload = decode_token(refresh_token)
        except Exception:
            raise ValueError("Invalid refresh token")

        if payload.get("type") != "refresh":
            raise ValueError("Invalid token type")

        token_hash = hash_token(refresh_token)
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        stored_rt = result.scalar_one_or_none()

        if not stored_rt:
            raise ValueError("Refresh token not found")

        # Reuse detection: if token was already used, revoke ALL user tokens
        if stored_rt.status == TokenStatus.used:
            await self.db.execute(
                update(RefreshToken)
                .where(RefreshToken.user_id == stored_rt.user_id)
                .values(status=TokenStatus.revoked)
            )
            await self.db.flush()
            raise PermissionError("Refresh token reuse detected — all sessions revoked")

        if stored_rt.status == TokenStatus.revoked:
            raise ValueError("Refresh token revoked")

        user_id = payload["sub"]
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise ValueError("User not found")

        # Mark old token as used
        stored_rt.status = TokenStatus.used
        await self.db.flush()

        # Issue new tokens
        new_access = create_access_token(user.id, user.tenant_id)
        new_refresh = create_refresh_token(user.id)

        new_hash = hash_token(new_refresh)
        new_rt = RefreshToken(
            user_id=user.id,
            token_hash=new_hash,
            status=TokenStatus.active,
            expires_at=datetime.now(tz=timezone.utc) + timedelta(days=7),
        )
        self.db.add(new_rt)
        await self.db.flush()

        return {"access_token": new_access, "refresh_token": new_refresh}

    async def logout(self, refresh_token: Optional[str] = None) -> dict:
        """Revoke refresh token and clear session."""
        if refresh_token:
            token_hash = hash_token(refresh_token)
            result = await self.db.execute(
                select(RefreshToken).where(RefreshToken.token_hash == token_hash)
            )
            stored_rt = result.scalar_one_or_none()
            if stored_rt:
                stored_rt.status = TokenStatus.revoked
                await self.db.flush()
        return {"message": "Logged out"}

    # -----------------------------------------------------------------------
    # AUTH-04: Password reset
    # -----------------------------------------------------------------------
    async def forgot_password(self, email: str) -> dict:
        """Send password reset email. Always returns 200 — no user enumeration."""
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        user = result.scalar_one_or_none()

        # Always return success to prevent user enumeration
        if not user:
            return {"message": "If that email exists, a reset link was sent"}

        token = _make_verification_jwt(user.id, "reset", RESET_TOKEN_EXPIRE_HOURS)
        token_hash = hash_token(token)
        expires_at = datetime.now(tz=timezone.utc) + timedelta(hours=RESET_TOKEN_EXPIRE_HOURS)

        # Remove any existing reset tokens
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.user_id == user.id,
                VerificationToken.purpose == "reset",
            )
        )
        for old in result.scalars().all():
            await self.db.delete(old)

        vt = VerificationToken(
            user_id=user.id,
            email=email.lower(),
            token_hash=token_hash,
            purpose="reset",
            expires_at=expires_at,
        )
        self.db.add(vt)
        await self.db.flush()

        reset_url = f"{settings.APP_URL}/reset-password?token={token}"
        html = (
            f"<p>Solicitação de redefinição de senha — InvestIQ</p>"
            f"<p><a href='{reset_url}'>Redefinir senha</a></p>"
            f"<p>Este link expira em 1 hora. Se não foi você, ignore este email.</p>"
        )
        try:
            await self.email_sender(email, "Redefinição de senha — InvestIQ", html)
        except Exception as exc:
            import logging
            logging.getLogger(__name__).error("Failed to send reset email to %s: %s", email, exc)
        return {"message": "If that email exists, a reset link was sent"}

    async def reset_password(self, token: str, new_password: str) -> dict:
        """Reset password using a valid reset token. Revokes all refresh tokens."""
        try:
            payload = _decode_verification_jwt(token)
        except Exception as e:
            import jwt as pyjwt
            if isinstance(e, pyjwt.ExpiredSignatureError):
                raise ValueError("Reset link expired")
            raise ValueError("Invalid reset token")

        if payload.get("purpose") != "reset":
            raise ValueError("Invalid token purpose")

        token_hash = hash_token(token)
        result = await self.db.execute(
            select(VerificationToken).where(
                VerificationToken.token_hash == token_hash,
                VerificationToken.purpose == "reset",
            )
        )
        vt = result.scalar_one_or_none()
        if not vt:
            raise ValueError("Reset token not found or already used")

        # Update password
        new_hashed = hash_password(new_password)
        await self.db.execute(
            update(User).where(User.id == vt.user_id).values(hashed_password=new_hashed)
        )

        # Revoke all refresh tokens for this user
        await self.db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == vt.user_id)
            .values(status=TokenStatus.revoked)
        )

        # Remove used reset token
        await self.db.delete(vt)
        await self.db.flush()

        return {"message": "Password reset successfully"}
