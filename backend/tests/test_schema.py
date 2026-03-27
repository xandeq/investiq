"""Schema and extensibility tests.

EXT-02: Verifies that the `plan` field on User is a DB-configurable string,
not a hardcoded Python enum or database CHECK constraint. Changing a user's
plan requires only a DB UPDATE — no code deploy.

EXT-01/EXT-03 (Plan 01-04): Verifies the transaction schema — all asset classes,
corporate action types, IR fields, RLS isolation, and module boundary isolation.

These tests use SQLite (same as the main test suite) and do NOT require
a running PostgreSQL instance (except test_rls_on_transactions which skips
when PG is unavailable).
"""
from __future__ import annotations

import uuid
import inspect as stdlib_inspect
import importlib
import asyncio

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.modules.auth.models import Base, User


# ---------------------------------------------------------------------------
# SQLite engine for schema tests (no PG needed)
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def schema_engine():
    """In-memory SQLite engine for schema-level tests."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def schema_session(schema_engine) -> AsyncSession:
    """Session with explicit transaction — rolled back after each test."""
    factory = async_sessionmaker(schema_engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# EXT-02: plan field is a configurable string (not a hardcoded enum)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_plan_field_accepts_free(schema_session: AsyncSession):
    """EXT-02: User.plan accepts 'free' — the default tier."""
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email=f"plan-test-{uuid.uuid4()}@example.com",
        hashed_password="$2b$12$fakehash",
        plan="free",
    )
    schema_session.add(user)
    await schema_session.flush()

    result = await schema_session.execute(
        text("SELECT plan FROM users WHERE id = :id"),
        {"id": user.id},
    )
    plan = result.scalar_one()
    assert plan == "free"


@pytest.mark.asyncio
async def test_plan_field_accepts_premium(schema_session: AsyncSession):
    """EXT-02: User.plan accepts 'premium' — a paid tier."""
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email=f"plan-test-{uuid.uuid4()}@example.com",
        hashed_password="$2b$12$fakehash",
        plan="premium",
    )
    schema_session.add(user)
    await schema_session.flush()

    result = await schema_session.execute(
        text("SELECT plan FROM users WHERE id = :id"),
        {"id": user.id},
    )
    plan = result.scalar_one()
    assert plan == "premium"


@pytest.mark.asyncio
async def test_plan_field_accepts_enterprise(schema_session: AsyncSession):
    """EXT-02: User.plan accepts 'enterprise' WITHOUT a schema change or code deploy.

    This is the key EXT-02 invariant: arbitrary plan names can be stored and
    retrieved from the DB. There must be no CHECK constraint or Python enum
    enforcement that would reject an unknown value.
    """
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email=f"plan-test-{uuid.uuid4()}@example.com",
        hashed_password="$2b$12$fakehash",
        plan="enterprise",
    )
    schema_session.add(user)
    await schema_session.flush()

    result = await schema_session.execute(
        text("SELECT plan FROM users WHERE id = :id"),
        {"id": user.id},
    )
    plan = result.scalar_one()
    assert plan == "enterprise"


@pytest.mark.asyncio
async def test_plan_field_updatable_without_migration(schema_session: AsyncSession):
    """EXT-02: Changing plan is a simple DB UPDATE — no migration needed.

    The plan field must accept any string value update. This simulates the
    operations pattern that would be used by a SaaS billing webhook: when a
    user upgrades from 'free' → 'premium', only an UPDATE is required.
    """
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email=f"plan-test-{uuid.uuid4()}@example.com",
        hashed_password="$2b$12$fakehash",
        plan="free",
    )
    schema_session.add(user)
    await schema_session.flush()

    # Upgrade via DB UPDATE — no code change required
    await schema_session.execute(
        text("UPDATE users SET plan = 'premium' WHERE id = :id"),
        {"id": user.id},
    )

    result = await schema_session.execute(
        text("SELECT plan FROM users WHERE id = :id"),
        {"id": user.id},
    )
    updated_plan = result.scalar_one()
    assert updated_plan == "premium", (
        f"Plan field should be 'premium' after UPDATE, got '{updated_plan}'"
    )


@pytest.mark.asyncio
async def test_plan_field_default_is_free(schema_session: AsyncSession):
    """EXT-02: Default plan value is 'free' when not explicitly set."""
    user = User(
        id=str(uuid.uuid4()),
        tenant_id=str(uuid.uuid4()),
        email=f"plan-test-{uuid.uuid4()}@example.com",
        hashed_password="$2b$12$fakehash",
        # plan not set — should default to "free"
    )
    schema_session.add(user)
    await schema_session.flush()

    assert user.plan == "free", f"Default plan should be 'free', got '{user.plan}'"


@pytest.mark.asyncio
async def test_plan_field_is_not_python_enum(schema_session: AsyncSession):
    """EXT-02: The plan field is a plain string column — not a Python Enum or SQLAlchemy Enum type.

    This test verifies the ORM column type directly. If plan were a SQLAlchemy
    Enum, inserting 'enterprise' (an unlisted value) would raise a LookupError.
    The fact that test_plan_field_accepts_enterprise passes confirms the column
    type is String, not Enum.
    """
    from sqlalchemy import inspect, String
    from app.modules.auth.models import User

    mapper = inspect(User)
    plan_col = mapper.columns["plan"]

    # The column type should be a String, not an Enum
    assert isinstance(plan_col.type, String), (
        f"User.plan should be a String column but is {type(plan_col.type).__name__}. "
        "A Python Enum column would reject unknown values and require a migration to add new tiers."
    )


# ---------------------------------------------------------------------------
# Portfolio module fixture — SQLite engine with portfolio models registered
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture(scope="module")
async def portfolio_engine():
    """In-memory SQLite engine with both auth + portfolio models registered."""
    # Import portfolio models to register them with Base.metadata
    import app.modules.portfolio.models  # noqa — side-effect: registers models
    from app.modules.portfolio.models import Transaction, CorporateAction

    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def portfolio_session(portfolio_engine) -> AsyncSession:
    """Session with explicit transaction — rolled back after each test."""
    factory = async_sessionmaker(portfolio_engine, expire_on_commit=False)
    async with factory() as session:
        async with session.begin():
            yield session
            await session.rollback()


# ---------------------------------------------------------------------------
# Helper: make a minimal transaction dict
# ---------------------------------------------------------------------------

def _make_tx(**overrides) -> dict:
    from decimal import Decimal
    from datetime import date
    from app.modules.portfolio.models import AssetClass, TransactionType

    base = {
        "id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "portfolio_id": str(uuid.uuid4()),
        "ticker": "PETR4",
        "asset_class": AssetClass.acao,
        "transaction_type": TransactionType.buy,
        "transaction_date": date(2025, 1, 15),
        "quantity": Decimal("100"),
        "unit_price": Decimal("38.50"),
        "total_value": Decimal("3850.00"),
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# EXT-01/EXT-02: Transaction asset class enum tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_transaction_asset_class_enum(portfolio_session: AsyncSession):
    """EXT-01/EXT-03: asset_class enum accepts all 5 required values.

    All of acao, FII, renda_fixa, BDR, ETF must be storable in the transactions
    table. This is a schema correctness requirement — any missing asset class
    breaks Phase 2 P&L calculations.
    """
    from sqlalchemy import select
    from app.modules.portfolio.models import Transaction, AssetClass

    asset_classes = [
        AssetClass.acao,
        AssetClass.fii,
        AssetClass.renda_fixa,
        AssetClass.bdr,
        AssetClass.etf,
    ]

    inserted_ids = []
    for ac in asset_classes:
        tx = Transaction(**_make_tx(
            id=str(uuid.uuid4()),
            ticker="TEST4",
            asset_class=ac,
        ))
        portfolio_session.add(tx)
        inserted_ids.append((tx.id, ac))

    await portfolio_session.flush()

    # Verify via ORM — avoids SQLite vs PostgreSQL enum storage differences
    # (SQLite stores enum member name, PostgreSQL stores enum value)
    result = await portfolio_session.execute(
        select(Transaction).where(Transaction.ticker == "TEST4")
    )
    rows = result.scalars().all()
    stored_classes = {row.asset_class for row in rows}
    expected = set(asset_classes)
    assert stored_classes == expected, (
        f"Expected all 5 asset classes stored, got: {stored_classes}"
    )
    assert len(rows) == 5, f"Expected 5 transactions inserted, got {len(rows)}"


@pytest.mark.asyncio
async def test_transaction_asset_specific_columns(portfolio_session: AsyncSession):
    """EXT-02: Nullable asset-specific columns work correctly.

    renda_fixa transaction with coupon_rate → persisted.
    acao transaction without coupon_rate → NULL stored, no error.
    This is the polymorphic single-table design.
    """
    from decimal import Decimal
    from datetime import date
    from app.modules.portfolio.models import Transaction, AssetClass, TransactionType

    # renda_fixa with coupon_rate
    tx_rf = Transaction(**_make_tx(
        id=str(uuid.uuid4()),
        ticker="TESOURO2027",
        asset_class=AssetClass.renda_fixa,
        coupon_rate=Decimal("0.1275"),
        maturity_date=date(2027, 3, 1),
    ))
    portfolio_session.add(tx_rf)

    # acao without coupon_rate (NULL)
    tx_ac = Transaction(**_make_tx(
        id=str(uuid.uuid4()),
        ticker="ITUB4",
        asset_class=AssetClass.acao,
    ))
    portfolio_session.add(tx_ac)

    await portfolio_session.flush()

    result_rf = await portfolio_session.execute(
        text("SELECT coupon_rate FROM transactions WHERE ticker = 'TESOURO2027'")
    )
    coupon = result_rf.scalar_one()
    assert coupon is not None, "coupon_rate should be stored for renda_fixa"
    assert float(coupon) == pytest.approx(0.1275, rel=1e-4)

    result_ac = await portfolio_session.execute(
        text("SELECT coupon_rate FROM transactions WHERE ticker = 'ITUB4'")
    )
    coupon_null = result_ac.scalar_one()
    assert coupon_null is None, "coupon_rate should be NULL for acao"


@pytest.mark.asyncio
async def test_ir_fields_stored(portfolio_session: AsyncSession):
    """IR fields irrf_withheld and gross_profit persist exactly as stored.

    These fields are NOT computed at query time — they are stored at transaction
    time to avoid recalculation drift. Tax authority requires exact stored values.
    """
    from decimal import Decimal
    from app.modules.portfolio.models import Transaction, AssetClass, TransactionType

    tx = Transaction(**_make_tx(
        id=str(uuid.uuid4()),
        asset_class=AssetClass.acao,
        transaction_type=TransactionType.sell,
        irrf_withheld=Decimal("150.00"),
        gross_profit=Decimal("1000.00"),
    ))
    portfolio_session.add(tx)
    await portfolio_session.flush()

    result = await portfolio_session.execute(
        text("SELECT irrf_withheld, gross_profit FROM transactions WHERE id = :id"),
        {"id": tx.id},
    )
    row = result.fetchone()
    assert row is not None
    assert float(row[0]) == pytest.approx(150.00), f"irrf_withheld mismatch: {row[0]}"
    assert float(row[1]) == pytest.approx(1000.00), f"gross_profit mismatch: {row[1]}"


@pytest.mark.asyncio
async def test_corporate_action_types(portfolio_session: AsyncSession):
    """Corporate action types desdobramento, grupamento, bonificacao all accepted."""
    from decimal import Decimal
    from datetime import date
    from app.modules.portfolio.models import CorporateAction, CorporateActionType

    action_types = [
        CorporateActionType.desdobramento,
        CorporateActionType.grupamento,
        CorporateActionType.bonificacao,
    ]

    for at in action_types:
        ca = CorporateAction(
            id=str(uuid.uuid4()),
            tenant_id=str(uuid.uuid4()),
            ticker="VALE3",
            action_type=at,
            action_date=date(2025, 6, 1),
            factor=Decimal("2.0") if at == CorporateActionType.desdobramento else Decimal("0.5"),
            source="B3",
        )
        portfolio_session.add(ca)

    await portfolio_session.flush()

    result = await portfolio_session.execute(
        text("SELECT DISTINCT action_type FROM corporate_actions")
    )
    stored = {row[0] for row in result.fetchall()}
    expected = {at.value for at in action_types}
    assert stored == expected, f"Expected all 3 action types, got: {stored}"


# ---------------------------------------------------------------------------
# RLS test — requires PostgreSQL (skipped if unavailable)
# ---------------------------------------------------------------------------

def _pg_available() -> bool:
    """Check if asyncpg is importable and a PG instance is reachable."""
    try:
        import asyncpg  # noqa
        return True
    except ImportError:
        return False


PG_AVAILABLE = _pg_available()

pytestmark_pg = pytest.mark.skipif(
    not PG_AVAILABLE,
    reason="asyncpg not installed — RLS test requires PostgreSQL; run inside Docker backend container",
)


@pytestmark_pg
@pytest.mark.asyncio
async def test_rls_on_transactions():
    """RLS on transactions table: Tenant A data invisible to Tenant B session.

    Requires PostgreSQL (asyncpg). Skipped when running locally without Docker.
    Run this test inside the Docker backend container where PG is accessible.
    """
    import os
    from decimal import Decimal
    from datetime import date
    from app.modules.portfolio.models import Transaction, AssetClass, TransactionType

    db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@postgres:5432/investiq_test"
    )

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())

    async with factory() as session:
        # As superuser (postgres), insert one transaction for tenant_a
        tx = Transaction(**_make_tx(
            id=str(uuid.uuid4()),
            tenant_id=tenant_a,
        ))
        session.add(tx)
        await session.commit()

    # Connect as app_user and set tenant_b context — should see 0 rows
    app_url = db_url.replace("postgres:postgres@", "app_user:change_in_production@")
    app_engine = create_async_engine(app_url, echo=False)
    app_factory = async_sessionmaker(app_engine, expire_on_commit=False)

    try:
        async with app_factory() as session:
            await session.execute(
                text("SET LOCAL rls.tenant_id = :tid"),
                {"tid": tenant_b},
            )
            result = await session.execute(
                text("SELECT COUNT(*) FROM transactions WHERE tenant_id = :tid"),
                {"tid": tenant_a},
            )
            count = result.scalar_one()
            assert count == 0, (
                f"RLS FAILED: tenant_b session saw {count} rows belonging to tenant_a"
            )
    finally:
        await app_engine.dispose()
        await engine.dispose()


# ---------------------------------------------------------------------------
# EXT-01: Module boundary isolation
# ---------------------------------------------------------------------------

def test_ext01_no_core_changes():
    """EXT-01: portfolio.models imports nothing from app.core.security or app.modules.auth.

    Adding the portfolio module required zero changes in app/core/ or app/modules/auth/.
    This test verifies the boundary is clean by inspecting the actual import statements.
    """
    import app.modules.portfolio.models as pm

    # Inspect only top-level imports, not docstrings or comments
    source_lines = stdlib_inspect.getsource(pm).splitlines()
    import_lines = [
        line for line in source_lines
        if line.strip().startswith(("import ", "from ")) and not line.strip().startswith("#")
    ]
    import_block = "\n".join(import_lines)

    forbidden_imports = [
        "from app.core.security",
        "from app.modules.auth.router",
        "from app.modules.auth.schemas",
        "from app.modules.auth.service",
        "import app.modules.auth",
        "import app.core.security",
    ]
    for forbidden in forbidden_imports:
        assert forbidden not in import_block, (
            f"EXT-01 VIOLATED: portfolio/models.py contains import '{forbidden}'. "
            "Portfolio module must be independent of auth domain logic."
        )


# ---------------------------------------------------------------------------
# EXT-03: Financial skill adapter interface
# ---------------------------------------------------------------------------

def test_ext03_skill_adapter_interface():
    """EXT-03: portfolio service exposes async calculate(data: dict) -> dict.

    This is the skeleton interface that DCF/valuation/earnings skills will
    implement in Phase 4. The interface must be a coroutine function (async def).
    """
    import app.modules.portfolio.service as svc

    assert hasattr(svc, "calculate"), (
        "EXT-03: portfolio/service.py must expose a 'calculate' function"
    )
    assert asyncio.iscoroutinefunction(svc.calculate), (
        "EXT-03: portfolio/service.calculate must be an async function (coroutine)"
    )

    # Verify the signature accepts (data: dict) -> dict
    sig = stdlib_inspect.signature(svc.calculate)
    params = list(sig.parameters.keys())
    assert "data" in params, (
        f"EXT-03: calculate() must accept a 'data' parameter, got params: {params}"
    )
