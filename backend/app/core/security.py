"""Security primitives for InvestIQ auth.

PyJWT RS256 sign/verify, bcrypt password hashing, httpOnly cookie helpers,
and FastAPI get_current_user dependency.

JWT keys loaded from AWS Secrets Manager at runtime (tools/investiq-jwt).
Never commit key material.
"""
from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt_lib
import jwt
from fastapi import Cookie, Depends, HTTPException, Request, status

from app.core.config import settings

# ---------------------------------------------------------------------------
# Password hashing
# Using bcrypt directly to avoid passlib compatibility issues with bcrypt 5.x.
# passlib 1.7.4 does not support bcrypt >= 4.0 cleanly.
# ---------------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash a plaintext password using bcrypt."""
    salt = _bcrypt_lib.gensalt()
    return _bcrypt_lib.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    try:
        return _bcrypt_lib.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# JWT RS256
# ---------------------------------------------------------------------------
ACCESS_TOKEN_EXPIRE_MINUTES = 15
REFRESH_TOKEN_EXPIRE_DAYS = 7


def _get_private_key() -> str:
    key = settings.JWT_PRIVATE_KEY
    # Try reading from file if env var is empty or malformed
    if not key or "BEGIN" not in key:
        key_file = os.path.join(os.path.dirname(__file__), "../../../../jwt_private.pem")
        key_file = os.path.normpath(key_file)
        if os.path.exists(key_file):
            with open(key_file) as f:
                return f.read()
        raise RuntimeError("JWT_PRIVATE_KEY not configured — fetch from AWS SM")
    # docker-compose may pass \n as literal backslash-n; convert back to real newlines
    if r"\n" in key:
        key = key.replace(r"\n", "\n")
    return key


def _get_public_key() -> str:
    key = settings.JWT_PUBLIC_KEY
    # Try reading from file if env var is empty or malformed
    if not key or "BEGIN" not in key:
        key_file = os.path.join(os.path.dirname(__file__), "../../../../jwt_public.pem")
        key_file = os.path.normpath(key_file)
        if os.path.exists(key_file):
            with open(key_file) as f:
                return f.read()
        raise RuntimeError("JWT_PUBLIC_KEY not configured — fetch from AWS SM")
    # docker-compose may pass \n as literal backslash-n; convert back to real newlines
    if r"\n" in key:
        key = key.replace(r"\n", "\n")
    return key


def create_access_token(sub: str, tenant_id: str) -> str:
    """Create RS256 access token with 15-minute expiry."""
    payload = {
        "sub": sub,
        "tenant_id": tenant_id,
        "type": "access",
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, _get_private_key(), algorithm="RS256")


def create_refresh_token(sub: str) -> str:
    """Create RS256 refresh token with 7-day expiry.

    Includes a random jti (JWT ID) to ensure uniqueness even when issued
    within the same second, preventing UNIQUE constraint failures on token_hash.
    """
    import uuid as _uuid
    payload = {
        "sub": sub,
        "type": "refresh",
        "jti": str(_uuid.uuid4()),  # Unique token ID — prevents duplicate hashes
        "iat": datetime.now(tz=timezone.utc),
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _get_private_key(), algorithm="RS256")


def decode_token(token: str) -> dict:
    """Decode and verify RS256 JWT. Raises jwt.ExpiredSignatureError or jwt.InvalidTokenError."""
    return jwt.decode(token, _get_public_key(), algorithms=["RS256"])


def hash_token(token: str) -> str:
    """SHA256 hash of a token — stored in DB, not the token itself."""
    return hashlib.sha256(token.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Cookie helpers
# ---------------------------------------------------------------------------
_IS_PRODUCTION = os.getenv("ENVIRONMENT", "development") == "production"


def set_auth_cookies(response, access_token: str, refresh_token: str) -> None:
    """Set httpOnly auth cookies on the response."""
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=_IS_PRODUCTION,
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=_IS_PRODUCTION,
        samesite="lax",
        path="/auth/refresh",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
    )


def clear_auth_cookies(response) -> None:
    """Clear both auth cookies (logout)."""
    response.delete_cookie(key="access_token")
    response.delete_cookie(key="refresh_token", path="/auth/refresh")


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_current_user(request: Request) -> dict:
    """FastAPI dependency: reads access_token cookie, returns {user_id, tenant_id}.

    Raises 401 if token is missing or invalid/expired.
    """
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token",
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    return {
        "user_id": payload["sub"],
        "tenant_id": payload["tenant_id"],
    }
