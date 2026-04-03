"""normalize_assetclass_enum_lowercase

Revision ID: 0018_normalize_assetclass_enum_lowercase
Revises: 0017_drop_import_staging_unique_constraint
Create Date: 2026-03-24

Root cause fixed:
  SQLAlchemy 2.x str(enum.Enum) builds _object_lookup using member NAMES as keys
  (acao, fii, renda_fixa, bdr, etf — lowercase). The PostgreSQL assetclass TYPE
  had uppercase values (FII, BDR, ETF) from migration 0003. When reading rows,
  SQLAlchemy looks up 'FII' in the dict but only finds 'fii' → LookupError.

  Error: LookupError: 'FII' is not among the defined enum values.
  Route: GET /dashboard/summary → portfolio/service.py → get_positions()

Fix:
  Rename the three uppercase PostgreSQL enum values to lowercase so they match
  the Python AssetClass member names. PostgreSQL stores enum values internally by
  OID — RENAME VALUE changes the label without requiring a data migration.

  After this migration: assetclass = ('acao', 'fii', 'renda_fixa', 'bdr', 'etf')

Python changes (same commit):
  - models.py: AssetClass.fii = "fii", .bdr = "bdr", .etf = "etf"
  - csv_parser.py: VALID_ASSET_CLASSES updated to lowercase
  - xlsx_parser.py: hardcoded "FII" → "fii"
  - insights/tasks.py, simulador/service.py, wizard/tasks.py: mapping keys lowercase
"""
from __future__ import annotations

from alembic import op


revision = "0018_normalize_assetclass_enum_lowercase"
down_revision = "0017_drop_import_staging_unique_constraint"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ALTER TYPE ... RENAME VALUE requires PostgreSQL 10+.
    # Existing rows are unaffected in storage (OID-based); the label change is
    # reflected immediately on next SELECT without a data migration.
    op.execute("ALTER TYPE assetclass RENAME VALUE 'FII' TO 'fii'")
    op.execute("ALTER TYPE assetclass RENAME VALUE 'BDR' TO 'bdr'")
    op.execute("ALTER TYPE assetclass RENAME VALUE 'ETF' TO 'etf'")


def downgrade() -> None:
    op.execute("ALTER TYPE assetclass RENAME VALUE 'fii' TO 'FII'")
    op.execute("ALTER TYPE assetclass RENAME VALUE 'bdr' TO 'BDR'")
    op.execute("ALTER TYPE assetclass RENAME VALUE 'etf' TO 'ETF'")
