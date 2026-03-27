# Phase 1: Foundation - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-tenant platform infrastructure: users can create accounts and authenticate, all data is isolated by tenant via PostgreSQL RLS, and the full transaction schema (asset classes, corporate actions, IR-required fields) is deployed and migration-baselined. Login UI, registration UI, and password reset UI are included. New modules must be addable without touching auth or tenant middleware.

</domain>

<decisions>
## Implementation Decisions

### Email Verification (AUTH-02)
- Blocked until verified — user hits a "check your email" screen, cannot enter the app until verified
- One-click token link (not OTP code) — user clicks link in email, immediately verified
- Link expiry: 24 hours
- Resend rate-limited: 3 requests per hour per user

### Session & Token Strategy (AUTH-03)
- Tokens stored in httpOnly cookies — XSS-proof, SSR-friendly for Next.js
- Access token: 15-minute lifetime; Refresh token: 7-day lifetime with rotation
- No "Remember me" checkbox — always persistent (7-day refresh for all users)
- All sessions valid simultaneously — user can be logged in on desktop and mobile at the same time

### Transaction Schema (EXT-01/EXT-03)
- Single polymorphic `transactions` table with `asset_class` enum (acao, FII, renda_fixa, BDR, ETF)
- Asset-specific columns are nullable (e.g., `coupon_rate` only applies to renda_fixa)
- Corporate actions stored in a **separate `corporate_actions` table** — clean separation from user transactions, easier to apply retroactively
- IR-required fields (`irrf_withheld`, `gross_profit`) stored **on the transaction row** — not computed on-the-fly
- One portfolio per tenant for v1 — no sub-portfolio concept yet

### Module/Folder Architecture (EXT-01)
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

</decisions>

<specifics>
## Specific Ideas

- No specific references — user selected all recommended/standard options throughout
- Brevo is the email provider (already configured in AWS Secrets Manager at `tools/brevo`)
- python-jose for JWT RS256 (from STATE.md decision log) — monitor maintenance status, fallback is PyJWT 2.8.x

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- None — greenfield project, no existing codebase to reference

### Established Patterns
- Stack locked: FastAPI + SQLAlchemy 2.x async + asyncpg (backend), Next.js 15 App Router + Tailwind 3.4.x + shadcn/ui (frontend)
- Infra: Docker Compose on VPS 185.173.110.180, Traefik for routing, EasyPanel for management
- Ports: frontend :3100 (investiq.com.br), API :8100 (api.investiq.com.br)

### Integration Points
- Auth module is the foundation — all other modules depend on `tenant_id` injected by auth middleware
- RLS must be active from the first endpoint — not retrofittable

</code_context>

<deferred>
## Deferred Ideas

- Multiple named portfolios (Clear vs XP separation) — noted for Phase 2+ consideration
- OAuth social login (Google/GitHub) — explicitly out of scope in PROJECT.md for v1
- Session management UI (view/revoke active sessions) — future phase

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-03-13*
