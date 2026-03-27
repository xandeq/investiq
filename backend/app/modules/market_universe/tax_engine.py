"""TaxEngine — IR regressivo calculator with DB-driven rates.

Reads tax_config rows once at init. Phases 8/9/10 instantiate per-request
with a global DB session — fast because tax_config has ~10 rows.

Usage (FastAPI endpoint):
    async def my_endpoint(db: AsyncSession = Depends(get_global_db)):
        rows = (await db.execute(select(TaxConfig))).scalars().all()
        engine = TaxEngine(rows)
        rate = engine.get_rate("renda_fixa", 200)

Usage (Celery task — sync):
    with get_sync_db_session(tenant_id=None) as session:
        engine = TaxEngine.from_db(session)
        net = engine.net_return(gross_pct=Decimal("10.0"), asset_class="LCI", holding_days=365)

Pitfall to avoid (D-13): Do NOT instantiate TaxEngine as a module-level singleton.
Instantiate per-request so process restarts pick up DB seed changes.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence


class TaxEngine:
    """IR regressivo calculator with DB-driven rates.

    Reads tax_config rows once at init. Each row must have:
        asset_class       (str)
        holding_days_min  (int)
        holding_days_max  (int | None)  — None means no upper bound
        rate_percent      (Decimal | str | float)
        is_exempt         (bool)

    Scope (D-10):
        - IR regressivo for renda_fixa (4 tiers)
        - LCI PF exemption (is_exempt=True)
        - LCA PF exemption (is_exempt=True)
        - FII dividend exemption (is_exempt=True)

    NOT in scope: acoes monthly R$20k exemption, day-trade 20%.
    """

    def __init__(self, config_rows: Sequence[Any]) -> None:
        """Accept pre-loaded config rows (from DB query or test stubs).

        Each row must expose attributes: asset_class, holding_days_min,
        holding_days_max, rate_percent, is_exempt.
        """
        self._tiers: list[dict] = []
        self._exemptions: set[str] = set()

        for row in config_rows:
            entry = {
                "asset_class": row.asset_class,
                "min": row.holding_days_min,
                "max": row.holding_days_max,       # None = no upper bound
                "rate": Decimal(str(row.rate_percent)),
                "exempt": bool(row.is_exempt),
            }
            self._tiers.append(entry)
            if entry["exempt"]:
                self._exemptions.add(entry["asset_class"])

    @classmethod
    def from_db(cls, db_session: Any) -> "TaxEngine":
        """Factory that loads config from tax_config table (sync session).

        For use in Celery tasks with get_sync_db_session(tenant_id=None).
        For async FastAPI endpoints, load rows explicitly and call cls(rows).
        """
        from app.modules.market_universe.models import TaxConfig
        from sqlalchemy import select

        rows = db_session.execute(select(TaxConfig)).scalars().all()
        return cls(rows)

    def get_rate(self, asset_class: str, holding_days: int) -> Decimal:
        """Return IR rate percent for the given asset class and holding period.

        Returns Decimal("0.00") for exempt asset classes (LCI, LCA, FII).
        Raises ValueError if no matching tier is found.

        Args:
            asset_class:  One of 'renda_fixa', 'LCI', 'LCA', 'FII'.
            holding_days: Number of days the investment was held.

        Returns:
            IR rate as a percentage, e.g. Decimal("22.50") for 22.5%.
        """
        if asset_class in self._exemptions:
            return Decimal("0.00")

        for tier in self._tiers:
            if tier["asset_class"] != asset_class:
                continue
            min_days = tier["min"]
            max_days = tier["max"]
            if min_days <= holding_days and (max_days is None or holding_days <= max_days):
                return tier["rate"]

        raise ValueError(
            f"No tax config found for asset_class='{asset_class}' at holding_days={holding_days}. "
            f"Check that tax_config table is seeded correctly."
        )

    def is_exempt(self, asset_class: str) -> bool:
        """Return True if the asset class is IR-exempt (LCI, LCA, FII).

        Args:
            asset_class: Asset class string, e.g. 'LCI', 'LCA', 'FII', 'renda_fixa'.

        Returns:
            True if exempt, False otherwise.
        """
        return asset_class in self._exemptions

    def net_return(
        self,
        gross_pct: Decimal,
        asset_class: str,
        holding_days: int,
    ) -> Decimal:
        """Calculate net return after IR deduction.

        Args:
            gross_pct:    Gross return as percentage, e.g. Decimal('10.0') for 10%.
            asset_class:  Asset class string.
            holding_days: Number of days held.

        Returns:
            Net return percentage after IR, e.g. Decimal('8.25') for 10% with 17.5% IR.

        Example:
            >>> engine.net_return(Decimal('10.0'), 'renda_fixa', 365)
            Decimal('8.25')  # 10.0 * (1 - 17.5/100) = 8.25
        """
        rate = self.get_rate(asset_class, holding_days)
        return gross_pct * (Decimal("1") - rate / Decimal("100"))
