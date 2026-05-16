"""add fundo to assetclass enum + fund_info + fund_quotes tables

Revision ID: 0037
Revises: 0036
Create Date: 2026-05-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0037"
down_revision = "0036"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add 'fundo' to the assetclass PostgreSQL enum.
    # ALTER TYPE ... ADD VALUE cannot run inside a transaction in PG < 12.
    # Using op.execute with connection.execution_options(autocommit=True)
    # is the standard Alembic workaround.
    op.execute("ALTER TYPE assetclass ADD VALUE IF NOT EXISTS 'fundo'")

    op.create_table(
        "fund_info",
        sa.Column("cnpj", sa.String(14), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("admin", sa.String(128), nullable=True),
        sa.Column("fund_class", sa.String(64), nullable=True),
        sa.Column("status", sa.String(64), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        "fund_quotes",
        sa.Column(
            "id", sa.String(36), primary_key=True,
            server_default=sa.text("gen_random_uuid()::text"),
        ),
        sa.Column("cnpj", sa.String(14), nullable=False),
        sa.Column("quote_date", sa.Date, nullable=False),
        sa.Column("nav_per_quota", sa.Numeric(18, 8), nullable=False),
        sa.Column("net_assets_brl", sa.Numeric(20, 2), nullable=True),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("cnpj", "quote_date", name="uq_fund_quotes_cnpj_date"),
    )
    op.create_index("ix_fund_quotes_cnpj", "fund_quotes", ["cnpj"])


def downgrade() -> None:
    op.drop_index("ix_fund_quotes_cnpj", "fund_quotes")
    op.drop_table("fund_quotes")
    op.drop_table("fund_info")
    # PostgreSQL does not support removing enum values — no rollback for 'fundo'
