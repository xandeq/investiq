"""add_swing_trade_operations

Revision ID: 0023_add_swing_trade_operations
Revises: 0022_add_detected_opportunities
Create Date: 2026-04-11

Creates the swing_trade_operations table used by Phase 20 (Swing Trade Page).
Enables PostgreSQL Row-Level Security so each tenant only sees its own rows.
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_add_swing_trade_operations"
down_revision = "0022_add_detected_opportunities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "swing_trade_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(36), nullable=False),
        sa.Column("ticker", sa.String(20), nullable=False),
        sa.Column("asset_class", sa.String(20), nullable=False, server_default="acao"),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("entry_price", sa.Numeric(18, 6), nullable=False),
        sa.Column("entry_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("target_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("stop_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("exit_price", sa.Numeric(18, 6), nullable=True),
        sa.Column("exit_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_swing_trade_operations_tenant_id",
        "swing_trade_operations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_swing_trade_operations_tenant_status",
        "swing_trade_operations",
        ["tenant_id", "status"],
    )

    # PostgreSQL-only: enable Row-Level Security so each tenant only reads/writes its rows.
    # SQLite (used in unit tests) ignores these statements because it doesn't have RLS.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TABLE swing_trade_operations ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            CREATE POLICY swing_trade_rls ON swing_trade_operations
            USING (tenant_id = current_setting('app.current_tenant_id', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))
            """
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("DROP POLICY IF EXISTS swing_trade_rls ON swing_trade_operations")
        op.execute("ALTER TABLE swing_trade_operations DISABLE ROW LEVEL SECURITY")
    op.drop_index(
        "ix_swing_trade_operations_tenant_status", table_name="swing_trade_operations"
    )
    op.drop_index(
        "ix_swing_trade_operations_tenant_id", table_name="swing_trade_operations"
    )
    op.drop_table("swing_trade_operations")
