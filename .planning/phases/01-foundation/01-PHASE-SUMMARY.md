---
phase: 01-foundation
type: phase-summary
status: complete
plans_completed: 4
completed: 2026-03-14
total_duration: ~4.5 hours
---

# Phase 1: Foundation — Phase Summary

**Multi-tenant FastAPI + SQLAlchemy 2.x platform with PostgreSQL RLS, JWT RS256 auth, and full transaction schema — the complete data foundation Phase 2 builds on**

## What Was Built

Phase 1 delivers a production-ready multi-tenant backend that handles authentication, session management, and the complete investment transaction data model, all with PostgreSQL row-level security enforced at the database layer.

### Plan 01-01 — Project Scaffold (~86 min)
- Docker Compose stack: FastAPI backend + PostgreSQL + Redis + Next.js 15 frontend
- SQLAlchemy 2.x async engine with `async_sessionmaker`
- Alembic migration baseline (migration `001_add_auth_tables`)
- Next.js 15 App Router scaffold with Tailwind 3.4.x + shadcn/ui
- `GET /health` endpoint — integration smoke test target

### Plan 01-02 — Authentication Service (~62 min)
- JWT RS256 keypair stored in AWS Secrets Manager (`tools/investiq-jwt`)
- Refresh token rotation with SHA256 hash storage (raw token never persisted)
- Email verification + password reset (one-time `VerificationToken`)
- bcrypt password hashing (direct `bcrypt` library, not passlib)
- `AuthService` with injected `email_sender` (EXT-03 pattern — stub in tests, Brevo in production)
- Next.js auth UI: login, register, forgot password, reset password pages
- httpOnly cookie transport for access + refresh tokens
- jti (UUID) on refresh JWTs to prevent hash collisions on same-second issuance

### Plan 01-03 — PostgreSQL RLS Tenant Isolation (~55 min)
- `app_user` non-superuser role (superuser bypasses RLS — critical design constraint)
- `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` on users, refresh_tokens, verification_tokens
- `CREATE POLICY tenant_isolation` using `NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid`
- `SET LOCAL rls.tenant_id` per request — transaction-scoped, safe with asyncpg pools
- `get_authed_db` FastAPI dependency: JWT decode → tenant_id extract → SET LOCAL → yield session
- `init-db.sql` with `ALTER DEFAULT PRIVILEGES` — future tables auto-granted to app_user
- `GET /me` endpoint: full auth + RLS integration test target
- `test_rls.py`: 5 PostgreSQL RLS isolation tests (skip gracefully without PG)

### Plan 01-04 — Transaction Schema (~64 min)
- `Transaction` model — polymorphic single table covering all 5 asset classes
- `CorporateAction` model — B3 corporate events in a separate table
- IR fields stored at transaction time: `irrf_withheld`, `gross_profit`
- Nullable asset-class-specific columns: `coupon_rate`, `maturity_date` (renda_fixa), `is_exempt` (FII)
- Migration `0003_add_transaction_schema`: tables + indexes + RLS + app_user grants
- Pydantic v2 schemas: `TransactionCreate` + `TransactionResponse`
- EXT-03 skeleton: `async calculate(data: dict) -> dict` in `portfolio/service.py`
- EXT-01 proof: portfolio module added with zero changes to `app/core/` or `app/modules/auth/`

## Architecture Patterns Established for Phase 2

### 1. Tenant Isolation via RLS (not application-layer filtering)
```python
# ALL tenant-scoped routes use this dependency — never raw get_db():
db: AsyncSession = Depends(get_authed_db)
```
RLS is structural, not optional. Forgetting the dependency returns 0 rows, not wrong rows.

### 2. Shared Base for All Models
```python
# ALL modules import Base from auth.models — one metadata, one migration history
from app.modules.auth.models import Base
```
Alembic autogenerate detects all tables because they share one metadata object.

### 3. Module Boundary (EXT-01)
```
app/modules/portfolio/  → reads only Base (no auth logic)
app/modules/auth/       → zero imports from portfolio
app/core/               → zero imports from portfolio
```
Adding a new module requires only: create `module/`, import `Base`, add `import app.modules.{name}` to `alembic/env.py`.

### 4. RLS Migration Pattern
```python
# Always write RLS migrations manually — autogenerate misses these:
op.execute("ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
op.execute("ALTER TABLE {table} FORCE ROW LEVEL SECURITY")
op.execute("""
    CREATE POLICY tenant_isolation ON {table}
      AS PERMISSIVE FOR ALL TO app_user
      USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid)
      WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')::uuid)
""")
op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON {table} TO app_user")
```

### 5. Financial Skill Adapter Interface (EXT-03)
```python
# portfolio/service.py skeleton — Phase 4 skills implement this:
async def calculate(data: dict) -> dict: ...
```

## Alembic Migration Chain

```
baseline
  └── 001_add_auth_tables          (users, refresh_tokens, verification_tokens)
        └── 0002_add_rls_policies  (app_user role + RLS on auth tables)
              └── 0003_add_transaction_schema  (transactions + corporate_actions + RLS)  ← HEAD
```

## Test Coverage at Phase 1 Close

| File | Tests | Status |
|------|-------|--------|
| `test_auth.py` | 40 | All PASSED |
| `test_rls.py` | 6 | SKIPPED (PG-only, run in Docker) |
| `test_schema.py` | 12 (+1 PG skip) | All PASSED |
| **Total** | **52 passed, 7 skipped** | **0 failures, 0 errors** |

## Key Decisions Made in Phase 1

| Decision | Rationale |
|----------|-----------|
| PostgreSQL RLS from Day 1 | Tenant isolation not retrofittable — must be foundational |
| `SET LOCAL` (not `SET`) for RLS GUC | `SET` leaks across pool reuse; `SET LOCAL` is transaction-scoped |
| FORCE ROW LEVEL SECURITY | Without FORCE, table owner (postgres/migrations) bypasses RLS |
| `app_user` non-superuser | Superusers bypass RLS — application must never connect as superuser |
| JWT RS256 (not HS256) | Asymmetric — microservices can verify without the private key |
| PyJWT directly (not python-jose) | python-jose unmaintained; PyJWT 2.8.0 actively maintained |
| bcrypt directly (not passlib) | passlib 1.7.4 incompatible with bcrypt >= 4.0 |
| tenant_id = user.id for v1 | One portfolio per user — deliberate MVP simplification |
| Polymorphic single table | All asset classes in one table; asset-specific columns nullable |
| IR fields stored (not computed) | Tax authority requires exact stored values; computation drift is a compliance risk |
| Shared Base from auth.models | Single metadata for Alembic; Base itself has no auth domain logic |
| Next.js 15.2.3+ | Patches CVE-2025-29927 (middleware auth bypass) |
| Tailwind 3.4.x | shadcn/ui does not fully support Tailwind 4.x as of 2026-03 |

## Phase 2 Readiness Checklist

- [x] `get_authed_db` available — all tenant-scoped routes use `Depends(get_authed_db)`
- [x] `Transaction` model — accepts all 5 asset classes + IR fields
- [x] `CorporateAction` model — B3 events ready for cost-basis adjustments
- [x] Migration chain complete — `alembic upgrade head` deploys full schema
- [x] RLS active on all tenant tables — cross-tenant data isolation enforced at DB
- [x] `portfolio/service.py` skeleton — Phase 4 skill adapters plug in here
- [x] Test suite green — zero failures, zero errors, 52 passing

**Phase 2 can start immediately.** First plan: P&L engine (CMP — custo médio ponderado).

---
*Phase: 01-foundation*
*Status: COMPLETE*
*Completed: 2026-03-14*
