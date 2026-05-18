"""add telegram_chat_id to users

Revision ID: 0038
Revises: 0037
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0038"
down_revision = "0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("telegram_chat_id", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "telegram_chat_id")
