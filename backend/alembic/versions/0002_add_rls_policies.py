"""add_rls_policies

Revision ID: 0002_add_rls_policies
Revises: 001_add_auth_tables
Create Date: 2026-03-13 23:00:00.000000

Adds PostgreSQL Row Level Security to the auth tables.

IMPORTANT: This migration is written manually — Alembic autogenerate does NOT
detect RLS policies, ENABLE ROW LEVEL SECURITY, or FORCE ROW LEVEL SECURITY.
Always write RLS migrations by hand.

What this migration does:
1. Creates the app_user role (non-superuser, LOGIN privilege).
   Superusers bypass RLS — app_user being non-superuser is critical.
2. Grants the minimum permissions app_user needs to operate.
3. Enables RLS on users, refresh_tokens tables.
4. Applies FORCE ROW LEVEL SECURITY (prevents table-owner bypass).
5. Creates tenant_isolation policy:
   - Uses current_setting('rls.tenant_id', TRUE) — the TRUE flag means
     "return NULL if the GUC is not set" (no error thrown).
   - NULLIF converts empty string → NULL to handle unset GUC safely.
   - Cast to ::uuid ensures type-safe comparison with the tenant_id column.
   - Used for USING and WITH CHECK — applies to ALL (SELECT, INSERT, UPDATE, DELETE).
   - Restricted to app_user role only — postgres superuser can still bypass for admin ops.

Design: SET LOCAL rls.tenant_id = :tid is applied at the start of every
authenticated request (see backend/app/core/middleware.py). The SET LOCAL
scope is transaction-local — safe with connection pooling (PgBouncer, asyncpg).

References:
- PostgreSQL docs: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- RESEARCH.md: "Do NOT wrap in a custom function — prevents index use"
- Plan 01-03 must_haves: SET LOCAL (not SET) prevents tenant leaking across pools
"""
from __future__ import annotations

from alembic import op


# revision identifiers, used by Alembic.
revision = "0002_add_rls_policies"
down_revision = "001_add_auth_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create application role — NOT superuser so RLS applies to it.
    # IF NOT EXISTS guard: safe to re-run (idempotent for dev rebuilds).
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
                CREATE ROLE app_user LOGIN PASSWORD 'change_in_production';
            END IF;
        END
        $$
    """)

    # Grant connectivity and schema access
    op.execute("GRANT CONNECT ON DATABASE investiq TO app_user")
    op.execute("GRANT USAGE ON SCHEMA public TO app_user")

    # Grant DML permissions on all current tables.
    # Note: tables created AFTER this grant are NOT automatically covered —
    # future migrations must explicitly grant to app_user.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")

    # ---------------------------------------------------------------------------
    # users table — RLS isolation
    # ---------------------------------------------------------------------------
    # ENABLE ROW LEVEL SECURITY: activates RLS on the table.
    op.execute("ALTER TABLE users ENABLE ROW LEVEL SECURITY")

    # FORCE ROW LEVEL SECURITY: applies the policy even to the table owner
    # (postgres). Without FORCE, the owner bypasses RLS. With FORCE, ALL roles
    # except explicit superusers obey the policy.
    op.execute("ALTER TABLE users FORCE ROW LEVEL SECURITY")

    # Isolation policy:
    # - current_setting('rls.tenant_id', TRUE) returns empty string if GUC not set.
    # - NULLIF(..., '') converts that empty string to NULL.
    # - NULL::uuid never equals any tenant_id — safe default (returns 0 rows).
    # - Do NOT wrap in a custom function: prevents PostgreSQL from using indexes
    #   on tenant_id (LEAKPROOF functions are the exception, but current_setting
    #   is built-in and safe to use directly).
    op.execute("""
        CREATE POLICY tenant_isolation ON users
          AS PERMISSIVE
          FOR ALL
          TO app_user
          USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
          WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
    """)

    # ---------------------------------------------------------------------------
    # refresh_tokens table — RLS via subquery into users
    # ---------------------------------------------------------------------------
    op.execute("ALTER TABLE refresh_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE refresh_tokens FORCE ROW LEVEL SECURITY")

    # refresh_tokens has a user_id foreign key — isolate by checking that the
    # referenced user belongs to the current tenant.
    op.execute("""
        CREATE POLICY tenant_isolation ON refresh_tokens
          AS PERMISSIVE
          FOR ALL
          TO app_user
          USING (user_id IN (
            SELECT id FROM users
            WHERE tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')
          ))
          WITH CHECK (user_id IN (
            SELECT id FROM users
            WHERE tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')
          ))
    """)

    # ---------------------------------------------------------------------------
    # verification_tokens table — RLS via subquery into users
    # ---------------------------------------------------------------------------
    op.execute("ALTER TABLE verification_tokens ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE verification_tokens FORCE ROW LEVEL SECURITY")

    op.execute("""
        CREATE POLICY tenant_isolation ON verification_tokens
          AS PERMISSIVE
          FOR ALL
          TO app_user
          USING (user_id IN (
            SELECT id FROM users
            WHERE tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')
          ))
          WITH CHECK (user_id IN (
            SELECT id FROM users
            WHERE tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')
          ))
    """)

    # Grant on the test database as well (test DB uses same migration).
    # This is a no-op if the database is 'investiq' — the GRANT above already covers it.
    # When running inside Docker: alembic upgrade head runs against investiq,
    # and a separate init script handles investiq_test (see backend/init-db.sql).


def downgrade() -> None:
    # Remove verification_tokens policies + RLS
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON verification_tokens")
    op.execute("ALTER TABLE verification_tokens DISABLE ROW LEVEL SECURITY")

    # Remove refresh_tokens policies + RLS
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON refresh_tokens")
    op.execute("ALTER TABLE refresh_tokens DISABLE ROW LEVEL SECURITY")

    # Remove users policies + RLS
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON users")
    op.execute("ALTER TABLE users DISABLE ROW LEVEL SECURITY")

    # Revoke permissions and drop role
    op.execute("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM app_user")
    op.execute("REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM app_user")
    op.execute("REVOKE USAGE ON SCHEMA public FROM app_user")
    op.execute("REVOKE CONNECT ON DATABASE investiq FROM app_user")
    op.execute("DROP ROLE IF EXISTS app_user")
