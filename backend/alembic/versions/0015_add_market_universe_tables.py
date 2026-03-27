"""add market universe tables (screener_snapshots, fii_metadata, fixed_income_catalog, tax_config)

Revision ID: 0015_add_market_universe_tables
Revises: 0014_add_trial_fields
Create Date: 2026-03-22

These are GLOBAL tables — no tenant_id column, no RLS policies.
app_user needs GRANT permissions since RLS is not used for access control.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0015_add_market_universe_tables"
down_revision = "0014_add_trial_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # screener_snapshots — one row per (ticker, snapshot_date)
    # Upserted daily by refresh_screener_universe Celery beat task (Mon-Fri 07h BRT)
    op.create_table(
        "screener_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("snapshot_date", sa.Date, nullable=False),
        sa.Column("short_name", sa.String(100), nullable=True),
        sa.Column("sector", sa.String(100), nullable=True),
        sa.Column("regular_market_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("regular_market_change_percent", sa.Numeric(10, 6), nullable=True),
        sa.Column("regular_market_volume", sa.BigInteger, nullable=True),
        sa.Column("market_cap", sa.BigInteger, nullable=True),
        sa.Column("pl", sa.Numeric(10, 4), nullable=True),
        sa.Column("pvp", sa.Numeric(10, 4), nullable=True),
        sa.Column("dy", sa.Numeric(10, 6), nullable=True),
        sa.Column("ev_ebitda", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    # Composite unique constraint — required for INSERT ON CONFLICT (ticker, snapshot_date)
    op.create_unique_constraint(
        "uq_screener_snapshots_ticker_date",
        "screener_snapshots",
        ["ticker", "snapshot_date"],
    )
    op.create_index(
        "ix_screener_snapshots_ticker_date",
        "screener_snapshots",
        ["ticker", "snapshot_date"],
    )
    op.create_index(
        "ix_screener_snapshots_date",
        "screener_snapshots",
        ["snapshot_date"],
    )

    # fii_metadata — one row per FII ticker (upserted weekly from CVM informe mensal)
    op.create_table(
        "fii_metadata",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("ticker", sa.String(20), nullable=False, unique=True),
        sa.Column("segmento", sa.String(50), nullable=True),
        sa.Column("vacancia_financeira", sa.Numeric(8, 4), nullable=True),
        sa.Column("num_cotistas", sa.Integer, nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_fii_metadata_ticker",
        "fii_metadata",
        ["ticker"],
        unique=True,
    )

    # fixed_income_catalog — seeded, read-only after migration
    # UI must always label as "taxas de referencia de mercado" — never "oferta ao vivo"
    op.create_table(
        "fixed_income_catalog",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_type", sa.String(20), nullable=False),  # CDB, LCI, LCA, TD_SELIC
        sa.Column("indexer", sa.String(20), nullable=False),           # CDI, IPCA, PREFIXADO, SELIC
        sa.Column("min_months", sa.Integer, nullable=False),
        sa.Column("max_months", sa.Integer, nullable=True),
        sa.Column("min_rate_pct", sa.Numeric(8, 4), nullable=False),
        sa.Column("max_rate_pct", sa.Numeric(8, 4), nullable=True),
        sa.Column("label", sa.String(100), nullable=False),
        sa.Column("is_reference", sa.Boolean, server_default="true", nullable=False),
    )

    # tax_config — TaxEngine reads this table at init time
    # Scope: IR regressivo (4 tiers) + LCI/LCA PF exemption + FII dividend exemption
    op.create_table(
        "tax_config",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("asset_class", sa.String(30), nullable=False),  # renda_fixa, FII, LCI, LCA
        sa.Column("holding_days_min", sa.Integer, nullable=False),
        sa.Column("holding_days_max", sa.Integer, nullable=True),  # NULL = no upper bound
        sa.Column("rate_percent", sa.Numeric(6, 4), nullable=False),
        sa.Column("is_exempt", sa.Boolean, server_default="false", nullable=False),
        sa.Column("label", sa.String(100), nullable=False),
    )

    # GRANT to app_user — required since these tables have no RLS policy
    # Without GRANT, app_user would get "permission denied for table" at runtime
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON screener_snapshots TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON fii_metadata TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON fixed_income_catalog TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON tax_config TO app_user")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")

    # Seed tax_config — IR regressivo 4 tiers + 3 exemptions (LCI, LCA, FII)
    # Total: 7 rows. Source: D-09, D-10, D-11 in CONTEXT.md
    op.execute("""
        INSERT INTO tax_config (id, asset_class, holding_days_min, holding_days_max, rate_percent, is_exempt, label) VALUES
        ('tc-rf-1', 'renda_fixa', 0,   180,  22.50, false, 'IR Regressivo <=180 dias'),
        ('tc-rf-2', 'renda_fixa', 181, 360,  20.00, false, 'IR Regressivo 181-360 dias'),
        ('tc-rf-3', 'renda_fixa', 361, 720,  17.50, false, 'IR Regressivo 361-720 dias'),
        ('tc-rf-4', 'renda_fixa', 721, NULL, 15.00, false, 'IR Regressivo >720 dias'),
        ('tc-lci-1', 'LCI',       0,   NULL,  0.00, true,  'LCI PF - Isento de IR'),
        ('tc-lca-1', 'LCA',       0,   NULL,  0.00, true,  'LCA PF - Isento de IR'),
        ('tc-fii-1', 'FII',       0,   NULL,  0.00, true,  'FII Dividendo - Isento de IR')
    """)

    # Seed fixed_income_catalog — 14 reference rate range rows
    # Source: D-07 + Code Examples section in RESEARCH.md
    # CDI-based: CDB (4 tenors), LCI (3 tenors), LCA (3 tenors) = 10 rows
    # IPCA-based: CDB (2 tenors), LCA (2 tenors) = 4 rows
    # Total: 14 rows
    op.execute("""
        INSERT INTO fixed_income_catalog (id, instrument_type, indexer, min_months, max_months, min_rate_pct, max_rate_pct, label, is_reference) VALUES
        ('cdb-cdi-6m',  'CDB', 'CDI',  6,    12,   95.00, 100.00, 'CDB 6 meses - 95% a 100% CDI',   true),
        ('cdb-cdi-1a',  'CDB', 'CDI',  12,   24,  100.00, 107.00, 'CDB 1 ano - 100% a 107% CDI',    true),
        ('cdb-cdi-2a',  'CDB', 'CDI',  24,   60,  105.00, 110.00, 'CDB 2 anos - 105% a 110% CDI',   true),
        ('cdb-cdi-5a',  'CDB', 'CDI',  60,  NULL, 108.00, 115.00, 'CDB 5 anos - 108% a 115% CDI',   true),
        ('lci-cdi-6m',  'LCI', 'CDI',  6,    12,   80.00,  88.00, 'LCI 6 meses - 80% a 88% CDI',    true),
        ('lci-cdi-1a',  'LCI', 'CDI',  12,   24,   85.00,  92.00, 'LCI 1 ano - 85% a 92% CDI',      true),
        ('lci-cdi-2a',  'LCI', 'CDI',  24,  NULL,  88.00,  95.00, 'LCI 2 anos - 88% a 95% CDI',     true),
        ('lca-cdi-6m',  'LCA', 'CDI',  6,    12,   80.00,  88.00, 'LCA 6 meses - 80% a 88% CDI',    true),
        ('lca-cdi-1a',  'LCA', 'CDI',  12,   24,   85.00,  92.00, 'LCA 1 ano - 85% a 92% CDI',      true),
        ('lca-cdi-2a',  'LCA', 'CDI',  24,  NULL,  88.00,  95.00, 'LCA 2 anos - 88% a 95% CDI',     true),
        ('cdb-ipca-3a', 'CDB', 'IPCA', 36,   60,    5.00,   5.00, 'CDB IPCA+ 3 anos - IPCA+5%',     true),
        ('cdb-ipca-5a', 'CDB', 'IPCA', 60,  NULL,   5.50,   5.50, 'CDB IPCA+ 5 anos - IPCA+5.5%',  true),
        ('lca-ipca-2a', 'LCA', 'IPCA', 24,   60,    4.00,   4.00, 'LCA IPCA+ 2 anos - IPCA+4%',     true),
        ('lca-ipca-5a', 'LCA', 'IPCA', 60,  NULL,   4.50,   4.50, 'LCA IPCA+ 5 anos - IPCA+4.5%',  true)
    """)


def downgrade() -> None:
    op.drop_table("tax_config")
    op.drop_table("fixed_income_catalog")
    op.drop_table("fii_metadata")
    op.drop_table("screener_snapshots")
