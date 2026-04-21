"""create signal_outcomes table

Revision ID: 0030
Revises: 0029_add_idempotent_checkout_requests
Create Date: 2026-04-21
"""
from alembic import op
import sqlalchemy as sa

revision = '0030'
down_revision = '0029_add_idempotent_checkout_requests'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'signal_outcomes',
        sa.Column('id', sa.String, primary_key=True),
        sa.Column('tenant_id', sa.String, nullable=False),
        sa.Column('ticker', sa.String, nullable=False),
        sa.Column('pattern', sa.String, nullable=True),
        sa.Column('direction', sa.String, nullable=False),
        sa.Column('entry_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('stop_price', sa.Numeric(18, 4), nullable=False),
        sa.Column('target_1', sa.Numeric(18, 4), nullable=True),
        sa.Column('target_2', sa.Numeric(18, 4), nullable=True),
        sa.Column('exit_price', sa.Numeric(18, 4), nullable=True),
        sa.Column('exit_date', sa.Date, nullable=True),
        sa.Column('status', sa.String, nullable=False, server_default='open'),
        sa.Column('r_multiple', sa.Numeric(8, 4), nullable=True),
        sa.Column('signal_grade', sa.String, nullable=True),
        sa.Column('signal_score', sa.Numeric(6, 2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.execute("ALTER TABLE signal_outcomes ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON signal_outcomes
        USING (tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), ''))
    """)


def downgrade() -> None:
    op.drop_table('signal_outcomes')
