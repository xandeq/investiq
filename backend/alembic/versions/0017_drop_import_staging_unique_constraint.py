"""drop uq_import_staging_tenant_hash — staging não precisa de unicidade global

Revision ID: 0017_drop_import_staging_unique_constraint
Revises: 0016_add_wizard_jobs
Create Date: 2026-03-23

Motivo: a constraint UniqueConstraint("tenant_id","import_hash") em import_staging
causava IntegrityError ao fazer re-upload do mesmo arquivo XLSX. A deduplicação
real ocorre em confirm_import contra a tabela transactions (que tem import_hash
único por tenant via lógica de aplicação), não em import_staging, que é tabela
temporária e pode ter múltiplos jobs com o mesmo arquivo.
"""
from __future__ import annotations

from alembic import op


revision = "0017_drop_import_staging_unique_constraint"
down_revision = "0016_add_wizard_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_import_staging_tenant_hash",
        "import_staging",
        type_="unique",
    )


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_import_staging_tenant_hash",
        "import_staging",
        ["tenant_id", "import_hash"],
    )
