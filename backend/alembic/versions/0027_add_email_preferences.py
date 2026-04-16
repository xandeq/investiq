"""add_email_preferences

Revision ID: 0027_add_email_preferences
Revises: 0026_add_portfolio_daily_value
Create Date: 2026-04-16

Adds email notification preference columns to the users table.
Users can opt out of the weekly portfolio digest independently
of price alert emails (which are transactional and remain on by default).

LGPD (Brazilian GDPR) requires users be able to opt out of marketing emails.
"""
from alembic import op
import sqlalchemy as sa

revision = "0027_add_email_preferences"
down_revision = "0026_add_portfolio_daily_value"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # weekly digest opt-out (default: True = subscribed)
    op.add_column(
        "users",
        sa.Column(
            "email_digest_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("TRUE"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "email_digest_enabled")
