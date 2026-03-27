"""add_auth_tables

Revision ID: 001_add_auth_tables
Revises:
Create Date: 2026-03-13 22:30:00.000000

Creates: users, refresh_tokens, verification_tokens

Note on RLS: Row-Level Security policies are added in Plan 01-03 (schema migration).
This migration creates the tables and grants SELECT/INSERT/UPDATE/DELETE to the
app_user role so RLS can be applied without superuser rights.

tenant_id = user.id for v1 (one-tenant-per-user simplification documented in models.py).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "001_add_auth_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Use raw SQL to avoid asyncpg/SQLAlchemy enum creation issues.
    # Named enum types must be created before the tables that reference them.
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE token_status AS ENUM ('active', 'used', 'revoked');
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)

    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            email VARCHAR(255) NOT NULL,
            hashed_password VARCHAR(255) NOT NULL,
            is_verified BOOLEAN NOT NULL DEFAULT FALSE,
            plan VARCHAR(50) NOT NULL DEFAULT 'free',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_users_email UNIQUE (email)
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_users_tenant_id ON users (tenant_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            status token_status NOT NULL DEFAULT 'active',
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_refresh_tokens_user_id ON refresh_tokens (user_id)")

    op.execute("""
        CREATE TABLE IF NOT EXISTS verification_tokens (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            email VARCHAR(255) NOT NULL,
            token_hash VARCHAR(64) NOT NULL UNIQUE,
            purpose VARCHAR(20) NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_tokens_user_id ON verification_tokens (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_verification_tokens_email ON verification_tokens (email)")

    # Grant permissions to app_user role for RLS enforcement (Plan 01-03)
    # app_user is not a superuser — superusers bypass RLS
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                GRANT SELECT, INSERT, UPDATE, DELETE ON users TO app_user;
                GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO app_user;
                GRANT SELECT, INSERT, UPDATE, DELETE ON verification_tokens TO app_user;
            END IF;
        END
        $$;
        """
    )

    # Register with alembic_version (handled automatically by alembic)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS verification_tokens")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP TYPE IF EXISTS token_status")
