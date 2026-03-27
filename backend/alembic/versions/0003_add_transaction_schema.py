"""add_transaction_schema

Revision ID: 0003_add_transaction_schema
Revises: 0002_add_rls_policies
Create Date: 2026-03-14 09:00:00.000000

Deploys the complete transaction data model — Phase 1 schema baseline.

What this migration does:
Part A: Create tables
  - transactions: polymorphic single table for all asset classes
  - corporate_actions: corporate events (splits, bonuses, groupings)

Part B: Indexes
  - ix_transactions_tenant_ticker: composite index for P&L queries (tenant_id, ticker)
  - ix_transactions_tenant_date: composite index for date-range queries (tenant_id, transaction_date)

Part C: RLS policies (written manually — autogenerate does NOT detect RLS)
  - ENABLE ROW LEVEL SECURITY on transactions + corporate_actions
  - FORCE ROW LEVEL SECURITY (prevents table-owner bypass even for postgres)
  - CREATE POLICY tenant_isolation using NULLIF(current_setting('rls.tenant_id', TRUE), '')
    Same pattern as 0002_add_rls_policies — consistent across all tenant tables.

Part D: Grants
  - GRANT SELECT, INSERT, UPDATE, DELETE on new tables TO app_user
  - Required because init-db.sql DEFAULT PRIVILEGES only covers tables created
    by postgres in the future — existing sessions may need explicit grants.

Design notes:
- EXT-01: portfolio module added with zero changes to app/core/ or app/modules/auth/
- EXT-02: asset_class and transaction_type are Enum columns — extensible by adding enum values
  in a future migration (ALTER TYPE ... ADD VALUE 'new_value')
- IR fields (irrf_withheld, gross_profit) are stored at transaction time — never computed.
  Tax authority requires exact stored values. Adding them post-facto requires data migration.
- tenant_id on both tables has no FK to users — RLS handles isolation structurally.
  FK would create a dependency between portfolio and auth schemas.

References:
- 0002_add_rls_policies.py: RLS pattern reference
- backend/app/modules/portfolio/models.py: SQLAlchemy model definitions
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "0003_add_transaction_schema"
down_revision = "0002_add_rls_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # Part A: Create enum types using raw SQL (avoids asyncpg/SQLAlchemy issue)
    # ---------------------------------------------------------------------------
    op.execute("DO $$ BEGIN CREATE TYPE assetclass AS ENUM ('acao', 'FII', 'renda_fixa', 'BDR', 'ETF'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE transactiontype AS ENUM ('buy', 'sell', 'dividend', 'jscp', 'amortization'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE corporateactiontype AS ENUM ('desdobramento', 'grupamento', 'bonificacao'); EXCEPTION WHEN duplicate_object THEN NULL; END $$;")

    # ---------------------------------------------------------------------------
    # Part A: Create transactions table (raw SQL avoids sa.Enum re-creation bug)
    # ---------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            portfolio_id VARCHAR(36) NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            asset_class assetclass NOT NULL,
            transaction_type transactiontype NOT NULL,
            transaction_date DATE NOT NULL,
            quantity NUMERIC(18, 8) NOT NULL,
            unit_price NUMERIC(18, 8) NOT NULL,
            total_value NUMERIC(18, 2) NOT NULL,
            brokerage_fee NUMERIC(18, 2),
            irrf_withheld NUMERIC(18, 2),
            gross_profit NUMERIC(18, 2),
            coupon_rate NUMERIC(10, 6),
            maturity_date DATE,
            is_exempt BOOLEAN NOT NULL DEFAULT FALSE,
            notes VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ---------------------------------------------------------------------------
    # Part A: Create corporate_actions table
    # ---------------------------------------------------------------------------
    op.execute("""
        CREATE TABLE IF NOT EXISTS corporate_actions (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            tenant_id VARCHAR(36) NOT NULL,
            ticker VARCHAR(20) NOT NULL,
            action_type corporateactiontype NOT NULL,
            action_date DATE NOT NULL,
            factor NUMERIC(18, 8) NOT NULL,
            source VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    # ---------------------------------------------------------------------------
    # Part B: Indexes
    # ---------------------------------------------------------------------------
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_tenant_ticker ON transactions (tenant_id, ticker)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_transactions_tenant_date ON transactions (tenant_id, transaction_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_corporate_actions_tenant_ticker ON corporate_actions (tenant_id, ticker)")

    # ---------------------------------------------------------------------------
    # Part C: RLS on transactions
    # Same pattern as 0002_add_rls_policies — tenant_id column used directly.
    # ---------------------------------------------------------------------------
    op.execute("ALTER TABLE transactions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE transactions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON transactions
          AS PERMISSIVE
          FOR ALL
          TO app_user
          USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
          WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
    """)

    # ---------------------------------------------------------------------------
    # Part C: RLS on corporate_actions
    # ---------------------------------------------------------------------------
    op.execute("ALTER TABLE corporate_actions ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE corporate_actions FORCE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON corporate_actions
          AS PERMISSIVE
          FOR ALL
          TO app_user
          USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
          WITH CHECK (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
    """)

    # ---------------------------------------------------------------------------
    # Part D: Grants to app_user on new tables
    # ---------------------------------------------------------------------------
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON transactions, corporate_actions TO app_user"
    )


def downgrade() -> None:
    # Remove RLS policies
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON corporate_actions")
    op.execute("ALTER TABLE corporate_actions DISABLE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON transactions")
    op.execute("ALTER TABLE transactions DISABLE ROW LEVEL SECURITY")

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS ix_corporate_actions_tenant_ticker")
    op.execute("DROP INDEX IF EXISTS ix_transactions_tenant_date")
    op.execute("DROP INDEX IF EXISTS ix_transactions_tenant_ticker")

    # Drop tables
    op.execute("DROP TABLE IF EXISTS corporate_actions")
    op.execute("DROP TABLE IF EXISTS transactions")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS corporateactiontype")
    op.execute("DROP TYPE IF EXISTS transactiontype")
    op.execute("DROP TYPE IF EXISTS assetclass")
