# Phase 1: Foundation - Research

**Researched:** 2026-03-13
**Domain:** FastAPI + PostgreSQL RLS + JWT auth + Next.js 15 App Router (greenfield SaaS foundation)
**Confidence:** HIGH

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Email Verification (AUTH-02)**
- Blocked until verified — user hits a "check your email" screen, cannot enter the app until verified
- One-click token link (not OTP code) — user clicks link in email, immediately verified
- Link expiry: 24 hours
- Resend rate-limited: 3 requests per hour per user

**Session & Token Strategy (AUTH-03)**
- Tokens stored in httpOnly cookies — XSS-proof, SSR-friendly for Next.js
- Access token: 15-minute lifetime; Refresh token: 7-day lifetime with rotation
- No "Remember me" checkbox — always persistent (7-day refresh for all users)
- All sessions valid simultaneously — user can be logged in on desktop and mobile at the same time

**Transaction Schema (EXT-01/EXT-03)**
- Single polymorphic `transactions` table with `asset_class` enum (acao, FII, renda_fixa, BDR, ETF)
- Asset-specific columns are nullable (e.g., `coupon_rate` only applies to renda_fixa)
- Corporate actions stored in a **separate `corporate_actions` table** — clean separation from user transactions, easier to apply retroactively
- IR-required fields (`irrf_withheld`, `gross_profit`) stored **on the transaction row** — not computed on-the-fly
- One portfolio per tenant for v1 — no sub-portfolio concept yet

**Module/Folder Architecture (EXT-01)**
- **Backend**: Domain-driven modules at `app/modules/auth/`, `app/modules/portfolio/`, `app/modules/market_data/`, etc. Each module is self-contained (routes, models, schemas, services). Shared infra at `app/core/` (db, config, security, middleware, logging)
- **Frontend**: Feature-based at `src/features/auth/`, `src/features/portfolio/`, `src/features/dashboard/`. App Router pages in `app/` for routing only. Feature folders contain components, hooks, and API calls. Shared at `src/lib/` (API client, formatters, shared hooks)
- **Migrations**: Alembic with version-controlled migration files. Autogenerate from SQLAlchemy models, review before applying

### Claude's Discretion
- Exact Alembic migration naming convention
- Password hashing algorithm (bcrypt assumed — standard)
- Exact database index design beyond what's obvious from queries
- Email template design for verification and password reset
- Error response schema format (400/401/403/422 shapes)
- Logging format and levels

### Deferred Ideas (OUT OF SCOPE)
- Multiple named portfolios (Clear vs XP separation) — noted for Phase 2+ consideration
- OAuth social login (Google/GitHub) — explicitly out of scope in PROJECT.md for v1
- Session management UI (view/revoke active sessions) — future phase
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| AUTH-01 | User can create account with email and password | PyJWT RS256 + bcrypt + FastAPI endpoint pattern documented |
| AUTH-02 | User receives email verification after registration | Brevo transactional API + token-based verification flow documented |
| AUTH-03 | User can log in and maintain persistent session | httpOnly cookie pattern + refresh token rotation + PyJWT documented |
| AUTH-04 | User can recover password via email link | Same Brevo + token pattern as AUTH-02; separate endpoint |
| AUTH-05 | System isolates data by tenant via PostgreSQL RLS from first endpoint | RLS policy SQL + FastAPI middleware set_config pattern documented |
| EXT-01 | Module architecture allows adding new domains without modifying core | Domain-driven folder structure confirmed — no library needed, pure convention |
| EXT-02 | Plan system is configurable — new tiers addable without special deploy | Plan field on user/tenant table in schema phase; configurable via DB |
| EXT-03 | Financial skills encapsulated in independent adapters | Adapter pattern via module-level service abstraction documented |
</phase_requirements>

---

## Summary

Phase 1 establishes a multi-tenant SaaS foundation on a greenfield Python/TypeScript stack. The four plans (scaffolding, auth, RLS, schema) are sequentially dependent: Docker Compose must come first, auth depends on the DB being up, RLS depends on the schema existing, and the transaction data model finalizes the schema baseline.

The most critical architectural decision — PostgreSQL Row Level Security — must be implemented from the first migration because it cannot be retrofitted into a running system without a full data migration. Every table that will hold tenant data must have `tenant_id` and RLS enabled from day one. The FastAPI middleware that injects `SET LOCAL rls.tenant_id = '...'` must run on every DB session before any query executes.

The JWT library decision has been resolved: python-jose is effectively abandoned (last release 3 years ago, last commit ~1 year ago). FastAPI's own documentation was updated to drop python-jose in favor of PyJWT 2.8.x with the `pyjwt[crypto]` extra for RS256. Use PyJWT — not python-jose.

**Primary recommendation:** Scaffold Docker Compose + FastAPI + PostgreSQL first, then implement auth with PyJWT RS256 + httpOnly cookies, then layer RLS on top via FastAPI middleware calling `SET LOCAL`, then deploy the full transaction schema with Alembic. Never skip the RLS step or leave it for later.

---

## Standard Stack

### Core (Backend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.x | API framework | Locked by project |
| SQLAlchemy | 2.x async | ORM + async DB access | Locked by project |
| asyncpg | 0.29.x | PostgreSQL async driver | Fastest Python PostgreSQL driver, required by SQLAlchemy async |
| Alembic | 1.13.x | DB migrations | Standard companion to SQLAlchemy |
| PyJWT | 2.8.x | JWT encode/decode | FastAPI docs now recommend over python-jose; `pyjwt[crypto]` for RS256 |
| bcrypt / passlib | passlib[bcrypt] 1.7.4 | Password hashing | Industry standard; passlib wraps bcrypt cleanly |
| pydantic-settings | 2.x | Config/env management | Replaces pydantic BaseSettings, standard for FastAPI 2.x |
| httpx | 0.27.x | HTTP client + test client | Required for async FastAPI testing with AsyncClient |

### Core (Frontend)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js | 15.2.3+ | Frontend framework | Locked by project; use 15.2.3+ (CVE-2025-29927 patched) |
| Tailwind CSS | 3.4.x | Styling | Locked — shadcn/ui not fully compatible with Tailwind 4.x |
| shadcn/ui | latest | Component library | Locked by project |

### Supporting (Backend)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-multipart | 0.0.9 | Form data parsing | Required by FastAPI for OAuth2PasswordRequestForm |
| celery | 5.x | Async task queue | Email sending, background jobs — add in Plan 01-02 |
| redis (redis-py) | 5.x | Cache + Celery broker | Rate limiting, token blacklist, Celery backend |
| jinja2 | 3.x | Email templates | HTML email rendering for verification/reset emails |
| itsdangerous | 2.x | Signed tokens | Alternative for email verification tokens (simpler than JWT for one-time use) |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| PyJWT | python-jose | python-jose is abandoned — do not use |
| passlib[bcrypt] | argon2-cffi | argon2 is more modern but passlib wraps both; bcrypt is sufficient and battle-tested |
| Alembic autogenerate | Manual migrations | Autogenerate misses some changes (RLS policies, custom functions) — always review output |
| `SET LOCAL rls.tenant_id` | Per-user DB roles | Per-user roles don't work with connection pools; session variable is the correct approach |

### Installation

```bash
# Backend
pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg alembic \
  "pyjwt[crypto]" "passlib[bcrypt]" pydantic-settings \
  httpx python-multipart celery redis jinja2 itsdangerous

# Test dependencies
pip install pytest pytest-asyncio anyio httpx asgi-lifespan

# Frontend
npx shadcn@latest init  # installs next, tailwind, shadcn
```

---

## Architecture Patterns

### Recommended Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app factory, lifespan, router registration
│   ├── core/
│   │   ├── config.py        # pydantic-settings (reads env vars)
│   │   ├── db.py            # engine, session factory, get_db dependency
│   │   ├── security.py      # JWT sign/verify, password hashing
│   │   ├── middleware.py    # RLS tenant injection middleware
│   │   └── logging.py       # structlog or stdlib logging config
│   └── modules/
│       ├── auth/
│       │   ├── router.py    # /auth endpoints
│       │   ├── models.py    # User, RefreshToken SQLAlchemy models
│       │   ├── schemas.py   # Pydantic request/response schemas
│       │   └── service.py   # register, login, verify, refresh logic
│       └── portfolio/       # Phase 2 — empty placeholder for EXT-01 demo
│           └── __init__.py
├── alembic/
│   ├── env.py               # async migration environment
│   └── versions/            # migration files
├── tests/
│   ├── conftest.py          # async fixtures, test DB session
│   ├── test_auth.py
│   └── test_rls.py          # tenant isolation assertions
├── Dockerfile
└── docker-compose.yml

frontend/
├── app/                     # Next.js App Router pages (routing only)
│   ├── (auth)/
│   │   ├── login/page.tsx
│   │   ├── register/page.tsx
│   │   └── verify-email/page.tsx
│   └── layout.tsx
├── src/
│   ├── features/
│   │   └── auth/
│   │       ├── components/  # LoginForm, RegisterForm
│   │       ├── hooks/       # useAuth, useSession
│   │       └── api.ts       # fetch wrappers for auth endpoints
│   └── lib/
│       ├── api-client.ts    # base fetch with cookie forwarding
│       └── formatters.ts
├── middleware.ts             # JWT verification at edge (route protection)
└── components.json          # shadcn config
```

### Pattern 1: RLS Tenant Injection Middleware

**What:** FastAPI dependency/middleware that reads the authenticated user's `tenant_id` from the JWT and sets a PostgreSQL session variable before every query. RLS policies read this variable to filter rows.

**When to use:** Every DB session — no exceptions. Applied at the `get_db` dependency level.

```python
# app/core/db.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text
from typing import AsyncGenerator

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db(tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        # SET LOCAL scopes the variable to this transaction only
        # Safe with connection pools — variable cannot leak to next request
        await session.execute(text("SET LOCAL rls.tenant_id = :tid"), {"tid": tenant_id})
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

```python
# app/modules/auth/router.py — dependency chain
from fastapi import Depends
from app.core.security import get_current_tenant_id

async def get_tenant_db(
    tenant_id: str = Depends(get_current_tenant_id),
    db: AsyncSession = Depends(get_db),  # get_db wraps with SET LOCAL
):
    yield db
```

```sql
-- Migration: enable RLS on every tenant table
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions FORCE ROW LEVEL SECURITY;  -- applies to table owner too

CREATE POLICY tenant_isolation ON transactions
  USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid)
  WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid);
```

### Pattern 2: PyJWT RS256 Token Pair (httpOnly Cookies)

**What:** Access token (15 min) + refresh token (7 days) stored in separate httpOnly cookies. RS256 requires a key pair — private key signs, public key verifies. Stateless access, stateful refresh (stored in DB for rotation).

**When to use:** All authenticated endpoints. Refresh token endpoint rotates: issues new refresh, invalidates old.

```python
# app/core/security.py
import jwt  # pyjwt[crypto]
from datetime import datetime, timedelta, UTC
from cryptography.hazmat.primitives import serialization

PRIVATE_KEY = settings.JWT_PRIVATE_KEY  # RSA PEM string from env/secrets
PUBLIC_KEY = settings.JWT_PUBLIC_KEY

def create_access_token(sub: str, tenant_id: str) -> str:
    payload = {
        "sub": sub,
        "tenant_id": tenant_id,
        "exp": datetime.now(UTC) + timedelta(minutes=15),
        "type": "access",
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

def create_refresh_token(sub: str) -> str:
    payload = {
        "sub": sub,
        "exp": datetime.now(UTC) + timedelta(days=7),
        "type": "refresh",
    }
    return jwt.encode(payload, PRIVATE_KEY, algorithm="RS256")

def decode_token(token: str) -> dict:
    return jwt.decode(token, PUBLIC_KEY, algorithms=["RS256"])
```

```python
# Setting httpOnly cookies on login response (FastAPI)
from fastapi import Response

def set_auth_cookies(response: Response, access_token: str, refresh_token: str):
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,         # HTTPS only in production
        samesite="lax",
        max_age=900,         # 15 minutes
        path="/",
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=604800,      # 7 days
        path="/auth/refresh",  # scoped to refresh endpoint only
    )
```

### Pattern 3: Alembic Async Configuration

**What:** Alembic `env.py` configured for async SQLAlchemy. Uses `async_engine_from_config` + `run_sync` pattern.

```python
# alembic/env.py (key async sections)
from sqlalchemy.ext.asyncio import async_engine_from_config
import asyncio

def run_migrations_online():
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
    )

    async def do_run_migrations(connection):
        await connection.run_sync(run_migrations)  # run_migrations is synchronous

    async def run_async_migrations():
        async with connectable.connect() as connection:
            await do_run_migrations(connection)

    asyncio.run(run_async_migrations())
```

### Pattern 4: Email Verification Flow

**What:** On registration, generate a signed token (itsdangerous URLSafeTimedSerializer or a short-lived JWT), store hash in DB, send link via Brevo API, verify on click.

```python
# Using itsdangerous for verification tokens (simpler than JWT for one-time use)
from itsdangerous import URLSafeTimedSerializer

serializer = URLSafeTimedSerializer(settings.SECRET_KEY)

def generate_verification_token(email: str) -> str:
    return serializer.dumps(email, salt="email-verify")

def verify_token(token: str, max_age: int = 86400) -> str:
    # raises SignatureExpired or BadSignature on failure
    return serializer.loads(token, salt="email-verify", max_age=max_age)
```

```python
# Brevo transactional email via HTTP (no SDK required)
import httpx

async def send_verification_email(to_email: str, token: str):
    verify_url = f"{settings.APP_URL}/verify-email?token={token}"
    payload = {
        "sender": {"name": settings.BREVO_FROM_NAME, "email": settings.BREVO_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": "Verifique seu email — InvestIQ",
        "htmlContent": f'<p>Clique para verificar: <a href="{verify_url}">Verificar email</a></p>',
    }
    async with httpx.AsyncClient() as client:
        r = await client.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers={"api-key": settings.BREVO_API_KEY},
        )
        r.raise_for_status()
```

### Anti-Patterns to Avoid

- **`SET` instead of `SET LOCAL` for RLS context:** `SET` persists for the entire connection lifetime. With a connection pool, the next request picks up a connection that still has the previous tenant's `rls.tenant_id` set. Always use `SET LOCAL` (transaction-scoped).
- **Running Alembic migrations on app startup in async context:** `alembic upgrade head` is a CLI tool. Call it in the Docker Compose `command:` before uvicorn starts, not from within the FastAPI lifespan.
- **python-jose for JWT:** Abandoned library. Do not use — use PyJWT 2.8.x.
- **Tokens in localStorage:** XSS-accessible. Use httpOnly cookies as locked.
- **RLS without `FORCE ROW LEVEL SECURITY`:** Table owners bypass RLS by default. Add `FORCE ROW LEVEL SECURITY` so even the app DB user cannot bypass policies.
- **Non-LEAKPROOF functions in RLS policies:** Prevents PostgreSQL from using indexes. Use `current_setting()` directly in the policy expression (it is LEAKPROOF) — do not wrap it in a custom function.
- **Testing with the superuser role:** Superusers bypass RLS entirely. Tests must connect as the application role (not postgres superuser) to verify policies work.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Password hashing | Custom hash logic | `passlib[bcrypt]` | Salt rounds, timing attacks, upgrade paths |
| JWT sign/verify | Custom crypto | `pyjwt[crypto]` | Constant-time comparison, algorithm confusion attacks |
| Email verification tokens | Custom HMAC | `itsdangerous` URLSafeTimedSerializer | Expiry, signature verification, salt scoping |
| DB migration | Manual SQL scripts | Alembic | Revision history, rollback, autogenerate |
| Email delivery | SMTP from scratch | Brevo API (already in AWS SM) | Deliverability, SPF/DKIM, bounce handling |
| Rate limiting | In-memory counter | Redis + slowapi (or manual Redis INCR/EXPIRE) | Multi-process safety, no state loss on restart |
| Cookie security | Manual headers | FastAPI `response.set_cookie()` | Correct SameSite, Secure, HttpOnly attributes |

**Key insight:** JWT and RLS have well-documented attack surfaces. The libraries exist specifically to handle the edge cases (algorithm confusion, timing attacks, session fixation). Rolling your own means inheriting all the bugs those libraries already fixed.

---

## Common Pitfalls

### Pitfall 1: `SET` vs `SET LOCAL` for RLS Context Leaking

**What goes wrong:** A request sets `rls.tenant_id` using `SET` (not `SET LOCAL`). The connection is returned to the pool. The next request from a different tenant picks up that connection — and its queries silently return the previous tenant's data.

**Why it happens:** PostgreSQL `SET` is connection-scoped (persists until changed or connection closed). Connection pools reuse connections across requests.

**How to avoid:** Always use `SET LOCAL rls.tenant_id = :tid` in the `get_db` dependency. `SET LOCAL` is transaction-scoped and automatically resets when the transaction ends.

**Warning signs:** Intermittent data leaks between tenants in load tests; tests pass in isolation but fail concurrently.

### Pitfall 2: Testing RLS as Superuser

**What goes wrong:** Tests connect to the database as the `postgres` superuser (or any superuser). PostgreSQL superusers bypass RLS unconditionally. Tests pass — isolation looks fine — but the actual app user has different behavior.

**Why it happens:** Default Docker PostgreSQL setups use superuser credentials. Dev convenience overrides security testing.

**How to avoid:** Create a dedicated application DB role in the migration baseline (e.g., `CREATE ROLE app_user LOGIN`). Run tests using that role. Assert that cross-tenant queries return empty, not unauthorized errors.

**Warning signs:** RLS tests pass but production shows data leakage; `EXPLAIN` shows sequential scans bypassing policies.

### Pitfall 3: Alembic Autogenerate Missing RLS Policies

**What goes wrong:** Alembic `--autogenerate` creates table and column migrations but does not detect `ENABLE ROW LEVEL SECURITY`, `FORCE ROW LEVEL SECURITY`, or `CREATE POLICY` statements. These silently disappear after a fresh migration run.

**Why it happens:** Alembic's autogenerate compares SQLAlchemy metadata to the DB schema. RLS is outside SQLAlchemy's model layer.

**How to avoid:** Always add RLS policy SQL manually in the migration file using `op.execute()` after autogenerate output. Add a comment marking it as manual. Document in a "migration checklist" that every table migration must review RLS.

**Warning signs:** Fresh database (e.g., CI environment) has tables but no isolation; existing DB works because policies were applied manually.

### Pitfall 4: Refresh Token Reuse Not Detected

**What goes wrong:** Stolen refresh token is used to get a new access token. The legitimate user's token was already rotated — they get a 401 and assume it's a bug. Attacker stays authenticated.

**Why it happens:** Rotation without reuse detection only invalidates the old token; it doesn't alert on the old token being used again.

**How to avoid:** Store refresh tokens in a `refresh_tokens` table with `status` (active/used/revoked). On rotation: mark old token as `used`, issue new token. If a `used` token is presented: revoke ALL tokens for that user (session hijack detected).

**Warning signs:** Active sessions on devices the user doesn't own; no alert on concurrent use of the same refresh token.

### Pitfall 5: Next.js Middleware Authentication Bypass (CVE-2025-29927)

**What goes wrong:** Route protection relies entirely on Next.js `middleware.ts` to verify JWT. A specific header manipulation bypasses the middleware check entirely.

**Why it happens:** Next.js had a middleware security flaw patched in 15.2.3, 14.2.25, 13.5.9, and 12.3.5.

**How to avoid:** Use Next.js 15.2.3+. Additionally, never rely solely on middleware — validate auth in Server Components and API routes too. Defense in depth.

**Warning signs:** Using Next.js 15.0.x–15.2.2 with middleware-only route protection.

### Pitfall 6: Docker Compose Database URL for Alembic

**What goes wrong:** Alembic is run outside Docker but DATABASE_URL uses the container hostname (`postgres`) instead of `localhost`. Or vice versa — app runs inside Docker but Alembic env.py uses `localhost`.

**Why it happens:** `asyncpg` URL scheme (`postgresql+asyncpg://`) works in the app but Alembic may need a sync URL for the CLI.

**How to avoid:** Alembic CLI should use a sync URL (`postgresql://`) or configure the async pattern properly. Run Alembic from within Docker (`docker compose exec backend alembic upgrade head`) so hostname resolution is consistent.

---

## Code Examples

### Verified: Async SQLAlchemy Session Dependency
```python
# Source: berkkaraal.com (verified against SQLAlchemy 2.x async docs)
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from typing import AsyncGenerator

engine = create_async_engine(
    settings.DATABASE_URL,  # postgresql+asyncpg://user:pass@host/db
    echo=settings.SQLALCHEMY_ECHO,
    pool_pre_ping=True,     # detect stale connections
)
async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        yield session
```

### Verified: RLS Policy SQL
```sql
-- Source: crunchydata.com (authoritative PostgreSQL source)
-- Run as superuser in migration; app_user must be the role the app connects as

-- 1. Create application role (not superuser)
CREATE ROLE app_user LOGIN PASSWORD 'change_me';
GRANT CONNECT ON DATABASE investiq TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;

-- 2. Enable RLS on tenant tables
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions FORCE ROW LEVEL SECURITY;

-- 3. Create isolation policy
CREATE POLICY tenant_isolation ON transactions
  AS PERMISSIVE
  FOR ALL
  TO app_user
  USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid)
  WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid);

-- 4. Application sets context per transaction (never per connection)
-- SET LOCAL rls.tenant_id = 'uuid-here';
```

### Verified: PyJWT RS256 Key Generation
```bash
# Generate RS256 key pair for JWT signing
openssl genrsa -out private_key.pem 2048
openssl rsa -in private_key.pem -pubout -out public_key.pem
# Store both in AWS Secrets Manager (tools/investiq-jwt or similar)
# NEVER commit key files to git
```

### Verified: Async Test Pattern
```python
# Source: FastAPI official docs (async-tests)
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

@pytest.mark.anyio
async def test_register():
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as client:
        response = await client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123!"
        })
    assert response.status_code == 201
```

### Verified: RLS Isolation Test
```python
# Tests must run as app_user, not superuser
@pytest.mark.anyio
async def test_tenant_isolation(db_as_app_user):
    """Tenant A cannot see Tenant B's transactions."""
    # Insert transaction for tenant B
    await db_as_app_user.execute(
        text("SET LOCAL rls.tenant_id = :tid"),
        {"tid": str(TENANT_B_ID)}
    )
    await db_as_app_user.execute(
        text("INSERT INTO transactions (tenant_id, ...) VALUES (:tid, ...)"),
        {"tid": str(TENANT_B_ID), ...}
    )

    # Query as tenant A — should return empty
    await db_as_app_user.execute(
        text("SET LOCAL rls.tenant_id = :tid"),
        {"tid": str(TENANT_A_ID)}
    )
    result = await db_as_app_user.execute(
        text("SELECT * FROM transactions")
    )
    rows = result.fetchall()
    assert len(rows) == 0  # RLS blocked tenant B's data
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| python-jose for JWT | PyJWT 2.8.x | FastAPI docs updated ~2024 | python-jose is abandoned — do not use |
| Tailwind 4.x | Tailwind 3.4.x | 2025 — shadcn/ui not yet compatible | Must stay on 3.4.x until shadcn catches up |
| `@app.on_event("startup")` | `lifespan` context manager | FastAPI 0.93+ | `on_event` deprecated; use `@asynccontextmanager lifespan` |
| `pydantic.BaseSettings` | `pydantic-settings` package | Pydantic v2 | Separate package install required |
| sync SQLAlchemy session | `async_sessionmaker` + `AsyncSession` | SQLAlchemy 2.0 | Fully async; different import paths |
| `pytest-asyncio` with loop scope | `anyio` + `pytest-anyio` | 2024+ | anyio is the FastAPI-aligned async test runner |

**Deprecated/outdated:**
- `python-jose`: Do not use. Abandoned, security concerns, FastAPI moved away.
- `from fastapi import __version__` checking: check package directly.
- SQLAlchemy 1.x session patterns: all use `with Session()` — in 2.x it's `async with AsyncSession()`.

---

## Open Questions

1. **python-jose fallback if RS256 issues arise**
   - What we know: PyJWT 2.8.x with `pyjwt[crypto]` supports RS256 natively; same API surface
   - What's unclear: Whether any existing code in the project (prototype scripts) uses python-jose already
   - Recommendation: Use PyJWT from the start, document the decision in a code comment

2. **Redis for rate limiting vs. in-DB counter**
   - What we know: Redis is in the stack (Celery broker); email resend rate limit is 3/hour/user
   - What's unclear: Whether Redis should be introduced in Plan 01-02 or deferred to when Celery is needed
   - Recommendation: Introduce Redis in Plan 01-01 scaffolding (Docker Compose) so it's available; use simple `INCR/EXPIRE` pattern for rate limiting without adding slowapi dependency

3. **Brevo sender domain verification**
   - What we know: Brevo API key is in AWS Secrets Manager at `tools/brevo`; from email is configured
   - What's unclear: Whether the Brevo account has sender domain verified for `@investiq.com.br`
   - Recommendation: Verify Brevo sender domain before running Plan 01-02 auth tests; if not verified, email sends will fail silently or go to spam

4. **JWT key storage in Docker Compose environment**
   - What we know: RS256 requires a private key (PEM). AWS Secrets Manager is the mandatory store for secrets.
   - What's unclear: How the PEM key is injected into Docker Compose containers at runtime without writing to disk
   - Recommendation: Store RSA key pair in AWS SM (`tools/investiq-jwt`). Fetch at container startup via entrypoint script, write to `/run/secrets/` (tmpfs), reference via env var. Or pass as multi-line env var directly.

---

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + anyio (async) |
| Config file | `backend/pytest.ini` — Wave 0 gap |
| Quick run command | `pytest tests/ -x -q` |
| Full suite command | `pytest tests/ -v --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AUTH-01 | POST /auth/register creates user with hashed password | unit + integration | `pytest tests/test_auth.py::test_register -x` | Wave 0 |
| AUTH-02 | Registration sends verification email; login blocked until verified | integration | `pytest tests/test_auth.py::test_email_verification_flow -x` | Wave 0 |
| AUTH-03 | Login sets httpOnly cookies; refresh token rotates; concurrent sessions allowed | integration | `pytest tests/test_auth.py::test_login_cookies -x` | Wave 0 |
| AUTH-04 | POST /auth/forgot-password sends reset email; link resets password | integration | `pytest tests/test_auth.py::test_password_reset -x` | Wave 0 |
| AUTH-05 | Tenant A queries return no rows from Tenant B's data | integration (RLS) | `pytest tests/test_rls.py -x` | Wave 0 |
| EXT-01 | Adding `app/modules/portfolio/` requires zero changes in `app/core/` or `app/modules/auth/` | structural (manual) | manual-only — folder structure review | N/A |
| EXT-02 | Plan field on user/tenant table is a DB-configurable enum, not hardcoded | unit | `pytest tests/test_schema.py::test_plan_enum -x` | Wave 0 |
| EXT-03 | Email adapter in `app/modules/auth/service.py` can swap Brevo for stub in tests | unit | `pytest tests/test_auth.py::test_email_adapter_swappable -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/ -x -q` (fail-fast, quiet)
- **Per wave merge:** `pytest tests/ -v --tb=short`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/pytest.ini` — pytest config with anyio_mode = "auto"
- [ ] `backend/tests/conftest.py` — async DB fixture using `app_user` role (not superuser), test DB setup/teardown
- [ ] `backend/tests/test_auth.py` — all AUTH-01 through AUTH-04 tests
- [ ] `backend/tests/test_rls.py` — tenant isolation assertions (AUTH-05)
- [ ] `backend/tests/test_schema.py` — schema validation (EXT-02, EXT-03)
- [ ] Framework install: `pip install pytest anyio pytest-anyio httpx asgi-lifespan`

---

## Sources

### Primary (HIGH confidence)
- PyPI / GitHub: python-jose — confirmed abandoned (last release 3 years ago)
- GitHub fastapi/fastapi discussions #11345 and #9587 — FastAPI team confirmed python-jose replacement with PyJWT
- crunchydata.com/blog/row-level-security-for-tenants-in-postgres — authoritative PostgreSQL RLS SQL patterns
- bytebase.com/blog/postgres-row-level-security-footguns — RLS pitfalls, SET vs SET LOCAL, LEAKPROOF functions
- berkkaraal.com/blog/2024/09/19/setup-fastapi-project-with-async-sqlalchemy-2-alembic-postgresql-and-docker — async SQLAlchemy 2.x + Alembic + Docker patterns
- fastapi.tiangolo.com/advanced/async-tests — official async test pattern with httpx AsyncClient

### Secondary (MEDIUM confidence)
- medium.com/@jagan_reddy/jwt-in-fastapi-the-secure-way-refresh-tokens-explained — refresh token rotation pattern (Jan 2026)
- developers.brevo.com/docs/send-a-transactional-email — Brevo HTTP API (no SDK required)
- blog.greeden.me — Next.js 15 httpOnly cookie auth patterns (Oct 2025)

### Tertiary (LOW confidence)
- Various Medium articles on FastAPI + RLS multitenancy — patterns consistent across sources but not all verified against official docs

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — locked by project + verified python-jose abandonment via official FastAPI discussions
- Architecture: HIGH — RLS patterns from authoritative PostgreSQL sources; async SQLAlchemy from official-adjacent tutorial
- Pitfalls: HIGH — SET vs SET LOCAL from bytebase authoritative source; CVE-2025-29927 is public record; RLS superuser bypass is documented PostgreSQL behavior
- Brevo integration: MEDIUM — API documented at developers.brevo.com; key already in AWS SM but sender domain verification status unknown

**Research date:** 2026-03-13
**Valid until:** 2026-04-13 (stable ecosystem; main risk is shadcn/ui Tailwind 4.x compatibility window)
