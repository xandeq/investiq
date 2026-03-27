"""Full auth test suite — AUTH-01 through AUTH-04 and EXT-03.

Tests cover:
  AUTH-01: Registration, duplicate email, password hashing
  AUTH-02: Email verification flow, blocked login before verify, expired tokens
  AUTH-03: Login cookies (httpOnly), refresh token rotation, reuse detection, logout
  AUTH-04: Forgot-password, reset-password, password changed
  EXT-03: Email adapter swappable — stub injected, no real HTTP

TDD note: These were written BEFORE implementation (RED phase).
"""
from __future__ import annotations

import re

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import register_and_verify, _extract_token_from_html


# =============================================================================
# AUTH-01: Registration
# =============================================================================

@pytest.mark.anyio
async def test_register(client, email_stub):
    """POST /auth/register → 201 with user_id, verification email sent."""
    resp = await client.post(
        "/auth/register",
        json={"email": "alice@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "user_id" in data
    assert data["message"] == "Verification email sent"

    # Verification email was sent (EXT-03 stub)
    assert len(email_stub.sent) == 1
    to, subject, html = email_stub.sent[0]
    assert to == "alice@example.com"
    assert "verify" in subject.lower() or "verif" in html.lower()
    assert "token=" in html  # Contains clickable link


@pytest.mark.anyio
async def test_register_password_hashed_not_plaintext(client, db_session):
    """Registered user's password is stored as bcrypt hash, not plaintext."""
    await client.post(
        "/auth/register",
        json={"email": "hashtest@example.com", "password": "PlainText123!"},
    )

    from sqlalchemy import select
    from app.modules.auth.models import User
    result = await db_session.execute(select(User).where(User.email == "hashtest@example.com"))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.hashed_password != "PlainText123!"
    assert user.hashed_password.startswith("$2b$") or user.hashed_password.startswith("$2a$")


@pytest.mark.anyio
async def test_register_duplicate_email(client):
    """Registering same email twice → 409 on second attempt."""
    payload = {"email": "duplicate@example.com", "password": "SecurePass123!"}
    resp1 = await client.post("/auth/register", json=payload)
    assert resp1.status_code == 201

    resp2 = await client.post("/auth/register", json=payload)
    assert resp2.status_code == 409
    assert "already registered" in resp2.json()["detail"]["error"].lower()


@pytest.mark.anyio
async def test_register_weak_password(client):
    """Password shorter than 8 characters → 422 validation error."""
    resp = await client.post(
        "/auth/register",
        json={"email": "weakpass@example.com", "password": "short"},
    )
    assert resp.status_code == 422


@pytest.mark.anyio
async def test_register_invalid_email(client):
    """Invalid email format → 422 validation error."""
    resp = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "password": "SecurePass123!"},
    )
    assert resp.status_code == 422


# =============================================================================
# AUTH-02: Email verification
# =============================================================================

@pytest.mark.anyio
async def test_login_before_verification_blocked(client, email_stub):
    """Login with valid credentials before email verification → 403."""
    await client.post(
        "/auth/register",
        json={"email": "unverified@example.com", "password": "SecurePass123!"},
    )

    resp = await client.post(
        "/auth/login",
        json={"email": "unverified@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == 403
    detail = resp.json()["detail"]
    assert detail["is_verified"] is False
    assert "not verified" in detail["error"].lower()


@pytest.mark.anyio
async def test_email_verification_flow(client, email_stub):
    """Register → click verify link → login succeeds."""
    # Register
    resp = await client.post(
        "/auth/register",
        json={"email": "verify@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == 201

    # Extract token from email
    _, _, html = email_stub.sent[-1]
    token = _extract_token_from_html(html)

    # Verify email
    resp2 = await client.get(f"/auth/verify-email?token={token}")
    assert resp2.status_code == 200
    assert resp2.json()["message"] == "Email verified"

    # Login now succeeds
    resp3 = await client.post(
        "/auth/login",
        json={"email": "verify@example.com", "password": "SecurePass123!"},
    )
    assert resp3.status_code == 200


@pytest.mark.anyio
async def test_verify_email_invalid_token(client):
    """Verification with invalid token → 400."""
    resp = await client.get("/auth/verify-email?token=invalid.token.here")
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_verify_email_marks_user_verified(client, email_stub, db_session):
    """After verification, User.is_verified becomes True in the database."""
    resp = await client.post(
        "/auth/register",
        json={"email": "mark.verified@example.com", "password": "SecurePass123!"},
    )
    user_id = resp.json()["user_id"]

    _, _, html = email_stub.sent[-1]
    token = _extract_token_from_html(html)
    await client.get(f"/auth/verify-email?token={token}")

    from sqlalchemy import select
    from app.modules.auth.models import User
    result = await db_session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.is_verified is True


# =============================================================================
# AUTH-03: Login and session
# =============================================================================

@pytest.mark.anyio
async def test_login_cookies(client, email_stub):
    """Successful login sets httpOnly access_token and refresh_token cookies."""
    await register_and_verify(client, email_stub, "cookietest@example.com")

    resp = await client.post(
        "/auth/login",
        json={"email": "cookietest@example.com", "password": "SecurePass123!"},
    )
    assert resp.status_code == 200

    # Verify cookies are present in response headers
    cookies = resp.cookies
    assert "access_token" in cookies or "access_token" in resp.headers.get("set-cookie", "")

    # Verify httpOnly flag is set (check Set-Cookie header)
    set_cookie_headers = resp.headers.get_list("set-cookie") if hasattr(resp.headers, 'get_list') else [
        v for k, v in resp.headers.items() if k.lower() == "set-cookie"
    ]
    cookie_str = " ".join(set_cookie_headers).lower()
    assert "httponly" in cookie_str
    assert "access_token" in cookie_str
    assert "refresh_token" in cookie_str


@pytest.mark.anyio
async def test_login_wrong_password(client, email_stub):
    """Login with wrong password → 401."""
    await register_and_verify(client, email_stub, "wrongpass@example.com")
    resp = await client.post(
        "/auth/login",
        json={"email": "wrongpass@example.com", "password": "WrongPassword!"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_login_nonexistent_user(client):
    """Login with email that doesn't exist → 401."""
    resp = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "AnyPassword123!"},
    )
    assert resp.status_code == 401


@pytest.mark.anyio
async def test_refresh_rotation(client, email_stub, db_session):
    """POST /auth/refresh → new tokens issued, old refresh token status=used."""
    await register_and_verify(client, email_stub, "refresh@example.com")
    login_resp = await client.post(
        "/auth/login",
        json={"email": "refresh@example.com", "password": "SecurePass123!"},
    )
    assert login_resp.status_code == 200

    # Get the refresh token from cookies
    refresh_cookie = None
    for header_val in [v for k, v in login_resp.headers.items() if k.lower() == "set-cookie"]:
        if "refresh_token=" in header_val:
            # Extract value
            match = re.search(r"refresh_token=([^;]+)", header_val)
            if match:
                refresh_cookie = match.group(1)

    assert refresh_cookie, "refresh_token cookie not found in login response"

    # Call /auth/refresh
    refresh_resp = await client.post(
        "/auth/refresh",
        cookies={"refresh_token": refresh_cookie},
    )
    assert refresh_resp.status_code == 200

    # Old token should now be status=used in DB
    from sqlalchemy import select
    from app.core.security import hash_token
    from app.modules.auth.models import RefreshToken, TokenStatus

    old_hash = hash_token(refresh_cookie)
    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.token_hash == old_hash)
    )
    old_rt = result.scalar_one_or_none()
    assert old_rt is not None
    assert old_rt.status == TokenStatus.used


@pytest.mark.anyio
async def test_refresh_reuse_revokes_all(client, email_stub, db_session):
    """Using a used refresh token → 401 + all refresh tokens for user are revoked."""
    await register_and_verify(client, email_stub, "reuse@example.com")
    login_resp = await client.post(
        "/auth/login",
        json={"email": "reuse@example.com", "password": "SecurePass123!"},
    )

    # Extract refresh token
    refresh_cookie = None
    for header_val in [v for k, v in login_resp.headers.items() if k.lower() == "set-cookie"]:
        if "refresh_token=" in header_val:
            match = re.search(r"refresh_token=([^;]+)", header_val)
            if match:
                refresh_cookie = match.group(1)

    assert refresh_cookie

    # Use token once (valid rotation)
    r1 = await client.post("/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert r1.status_code == 200

    # Use SAME (now-used) token again → reuse detection
    r2 = await client.post("/auth/refresh", cookies={"refresh_token": refresh_cookie})
    assert r2.status_code == 401

    # All tokens for user should now be revoked
    from sqlalchemy import select
    from app.modules.auth.models import RefreshToken, TokenStatus, User
    result = await db_session.execute(select(User).where(User.email == "reuse@example.com"))
    user = result.scalar_one_or_none()

    result2 = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == user.id)
    )
    all_tokens = result2.scalars().all()
    # All tokens should be either used or revoked (none active)
    active_tokens = [t for t in all_tokens if t.status == TokenStatus.active]
    assert len(active_tokens) == 0, f"Expected 0 active tokens, found {len(active_tokens)}"


@pytest.mark.anyio
async def test_logout(client, email_stub):
    """POST /auth/logout → 200, cookies cleared."""
    await register_and_verify(client, email_stub, "logout@example.com")
    await client.post(
        "/auth/login",
        json={"email": "logout@example.com", "password": "SecurePass123!"},
    )

    resp = await client.post("/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Logged out"

    # Verify cookies are cleared (Set-Cookie with max-age=0 or delete)
    set_cookies = [v for k, v in resp.headers.items() if k.lower() == "set-cookie"]
    cookie_str = " ".join(set_cookies).lower()
    # FastAPI delete_cookie sets max-age=0
    assert "access_token" in cookie_str


# =============================================================================
# AUTH-04: Password reset
# =============================================================================

@pytest.mark.anyio
async def test_forgot_password_always_200(client):
    """POST /auth/forgot-password always returns 200 — prevents user enumeration."""
    resp = await client.post(
        "/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )
    assert resp.status_code == 200
    assert "sent" in resp.json()["message"].lower() or "exists" in resp.json()["message"].lower()


@pytest.mark.anyio
async def test_password_reset(client, email_stub):
    """Complete password reset flow: forgot → email → reset → login with new password."""
    await register_and_verify(client, email_stub, "resetme@example.com")
    email_stub.sent.clear()  # Clear verification email

    # Request reset
    resp = await client.post(
        "/auth/forgot-password",
        json={"email": "resetme@example.com"},
    )
    assert resp.status_code == 200
    assert len(email_stub.sent) == 1

    _, _, html = email_stub.sent[-1]
    token = _extract_token_from_html(html)

    # Reset password
    resp2 = await client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "NewPassword456!"},
    )
    assert resp2.status_code == 200

    # Login with old password → 401
    resp3 = await client.post(
        "/auth/login",
        json={"email": "resetme@example.com", "password": "SecurePass123!"},
    )
    assert resp3.status_code == 401

    # Login with new password → 200
    resp4 = await client.post(
        "/auth/login",
        json={"email": "resetme@example.com", "password": "NewPassword456!"},
    )
    assert resp4.status_code == 200


@pytest.mark.anyio
async def test_reset_revokes_all_refresh_tokens(client, email_stub, db_session):
    """After password reset, all refresh tokens for the user are revoked."""
    await register_and_verify(client, email_stub, "revokeall@example.com")
    # Login first to create a refresh token
    await client.post(
        "/auth/login",
        json={"email": "revokeall@example.com", "password": "SecurePass123!"},
    )

    email_stub.sent.clear()
    await client.post("/auth/forgot-password", json={"email": "revokeall@example.com"})
    _, _, html = email_stub.sent[-1]
    token = _extract_token_from_html(html)

    await client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "NewPass789!"},
    )

    from sqlalchemy import select
    from app.modules.auth.models import RefreshToken, TokenStatus, User
    result = await db_session.execute(select(User).where(User.email == "revokeall@example.com"))
    user = result.scalar_one_or_none()

    result2 = await db_session.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.status == TokenStatus.active,
        )
    )
    active = result2.scalars().all()
    assert len(active) == 0


@pytest.mark.anyio
async def test_reset_invalid_token(client):
    """POST /auth/reset-password with invalid token → 400."""
    resp = await client.post(
        "/auth/reset-password",
        json={"token": "invalid.token.value", "new_password": "NewPassword456!"},
    )
    assert resp.status_code == 400


# =============================================================================
# EXT-03: Email adapter swappable
# =============================================================================

@pytest.mark.anyio
async def test_email_adapter_swappable(db_session, fake_redis):
    """AuthService with injected stub — stub is called, no real HTTP request made."""
    from app.modules.auth.service import AuthService

    captured: list[tuple[str, str, str]] = []

    async def mock_sender(to_email: str, subject: str, html: str) -> None:
        captured.append((to_email, subject, html))

    service = AuthService(db_session, email_sender=mock_sender, redis_client=fake_redis)
    result = await service.register("stub@example.com", "StubPass123!")
    assert result["message"] == "Verification email sent"

    # Mock was called exactly once
    assert len(captured) == 1
    assert captured[0][0] == "stub@example.com"
    assert "token=" in captured[0][2]
