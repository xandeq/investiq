"""add ai_mode column to users

Revision ID: 0032
Revises: 0031
Create Date: 2026-04-23
"""
from alembic import op
import sqlalchemy as sa

revision = "0032"
down_revision = "0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "ai_mode",
            sa.String(10),
            nullable=False,
            server_default="standard",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "ai_mode")
