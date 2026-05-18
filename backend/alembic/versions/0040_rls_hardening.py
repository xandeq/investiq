"""RLS hardening: fix GUC mismatch, add FORCE, add NULLIF, add missing policies.

Revision ID: 0040
Revises: 0039
Create Date: 2026-05-18

Fixes found in post-Phase-42 security audit:
  1. swing_trade_operations: used 'app.current_tenant_id' instead of 'rls.tenant_id'
     — drop old policy + recreate with standard GUC + NULLIF + FORCE
  2. portfolio_goals: missing NULLIF wrapper + missing FORCE ROW LEVEL SECURITY
  3. signal_outcomes: missing FORCE ROW LEVEL SECURITY
  4. user_insights, analysis_jobs, analysis_quota_logs, analysis_cost_logs:
     have tenant_id but zero RLS — add ENABLE + policy for each

All policies use: NULLIF(current_setting('rls.tenant_id', TRUE), '')
which is null-safe (unset GUC = NULL = policy matches nothing = safe default-deny).
FORCE ROW LEVEL SECURITY ensures even the table owner (superuser Celery sessions)
is subject to the policy when rls.tenant_id is set.
"""
from alembic import op

revision = "0040"
down_revision = "0039"
branch_labels = None
depends_on = None

_TENANT_EXPR = "tenant_id = NULLIF(current_setting('rls.tenant_id', TRUE), '')"
_STANDARD_POLICY = f"USING ({_TENANT_EXPR})"
_STANDARD_POLICY_WITH_CHECK = f"USING ({_TENANT_EXPR}) WITH CHECK ({_TENANT_EXPR})"


def _pg(sql: str) -> None:
    """Execute SQL only on PostgreSQL (ignored in SQLite test DB)."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sql)


def upgrade() -> None:
    # ── 1. swing_trade_operations: wrong GUC → standard GUC + FORCE ──────────
    _pg("DROP POLICY IF EXISTS swing_trade_rls ON swing_trade_operations")
    _pg("ALTER TABLE swing_trade_operations FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON swing_trade_operations "
        + _STANDARD_POLICY_WITH_CHECK
    )

    # ── 2. portfolio_goals: add NULLIF + FORCE (recreate clean policy) ────────
    _pg("DROP POLICY IF EXISTS tenant_isolation ON portfolio_goals")
    _pg("ALTER TABLE portfolio_goals FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON portfolio_goals "
        + _STANDARD_POLICY
    )

    # ── 3. signal_outcomes: add FORCE (policy already exists with NULLIF) ─────
    _pg("ALTER TABLE signal_outcomes FORCE ROW LEVEL SECURITY")

    # ── 4. user_insights: enable RLS + policy ────────────────────────────────
    _pg("ALTER TABLE user_insights ENABLE ROW LEVEL SECURITY")
    _pg("ALTER TABLE user_insights FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON user_insights "
        + _STANDARD_POLICY
    )

    # ── 5. analysis_jobs: enable RLS + policy ────────────────────────────────
    _pg("ALTER TABLE analysis_jobs ENABLE ROW LEVEL SECURITY")
    _pg("ALTER TABLE analysis_jobs FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON analysis_jobs "
        + _STANDARD_POLICY
    )

    # ── 6. analysis_quota_logs: enable RLS + policy ───────────────────────────
    _pg("ALTER TABLE analysis_quota_logs ENABLE ROW LEVEL SECURITY")
    _pg("ALTER TABLE analysis_quota_logs FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON analysis_quota_logs "
        + _STANDARD_POLICY
    )

    # ── 7. analysis_cost_logs: enable RLS + policy ────────────────────────────
    _pg("ALTER TABLE analysis_cost_logs ENABLE ROW LEVEL SECURITY")
    _pg("ALTER TABLE analysis_cost_logs FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON analysis_cost_logs "
        + _STANDARD_POLICY
    )


def downgrade() -> None:
    _pg("DROP POLICY IF EXISTS tenant_isolation ON analysis_cost_logs")
    _pg("ALTER TABLE analysis_cost_logs DISABLE ROW LEVEL SECURITY")

    _pg("DROP POLICY IF EXISTS tenant_isolation ON analysis_quota_logs")
    _pg("ALTER TABLE analysis_quota_logs DISABLE ROW LEVEL SECURITY")

    _pg("DROP POLICY IF EXISTS tenant_isolation ON analysis_jobs")
    _pg("ALTER TABLE analysis_jobs DISABLE ROW LEVEL SECURITY")

    _pg("DROP POLICY IF EXISTS tenant_isolation ON user_insights")
    _pg("ALTER TABLE user_insights DISABLE ROW LEVEL SECURITY")

    # signal_outcomes: just remove FORCE (policy + enable were in 0030)
    _pg("ALTER TABLE signal_outcomes NO FORCE ROW LEVEL SECURITY")

    # portfolio_goals: restore to pre-0040 state (no FORCE, direct cast)
    _pg("DROP POLICY IF EXISTS tenant_isolation ON portfolio_goals")
    _pg("ALTER TABLE portfolio_goals NO FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY tenant_isolation ON portfolio_goals "
        "USING (tenant_id = current_setting('rls.tenant_id', true)::text)"
    )

    # swing_trade: restore old (wrong) GUC policy
    _pg("DROP POLICY IF EXISTS tenant_isolation ON swing_trade_operations")
    _pg("ALTER TABLE swing_trade_operations NO FORCE ROW LEVEL SECURITY")
    _pg(
        "CREATE POLICY swing_trade_rls ON swing_trade_operations "
        "USING (tenant_id = current_setting('app.current_tenant_id', true)) "
        "WITH CHECK (tenant_id = current_setting('app.current_tenant_id', true))"
    )
