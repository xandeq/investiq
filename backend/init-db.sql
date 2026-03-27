-- InvestIQ PostgreSQL initialization script.
-- Mounted as /docker-entrypoint-initdb.d/init-db.sql in the postgres container.
-- Runs ONCE at container first creation (not on subsequent starts).
--
-- Creates app_user role for RLS enforcement.
-- app_user is non-superuser — superusers bypass RLS, making isolation meaningless.
--
-- IMPORTANT: This script runs on the investiq database (POSTGRES_DB).
-- For the investiq_test database (used by pytest inside the backend container),
-- the Alembic migration 0002_add_rls_policies.py handles role creation.
--
-- Production secret rotation: replace 'change_in_production' with the value
-- from AWS Secrets Manager at tools/investiq-db. Never commit real passwords.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN PASSWORD 'change_in_production';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE investiq TO app_user;
GRANT USAGE ON SCHEMA public TO app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;

-- Default privileges: future tables created by the postgres user are automatically
-- accessible to app_user. Without this, each new migration's tables need explicit GRANTs.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
