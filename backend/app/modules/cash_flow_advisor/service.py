"""Ranking logic for Cash Parking Advisor."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

from app.modules.cash_flow_advisor.schemas import (
    CashFlowProjection,
    CashParkingResponse,
    CashParkingRow,
)
from app.modules.market_universe.iof_engine import IOFEngine
from app.modules.market_universe.tax_engine import TaxEngine

_MIN_AMOUNT = Decimal("1000.00")
_MAX_HOLDING_DAYS = 90
_POUPANCA_SELIC_THRESHOLD = Decimal("8.50")


class CashParkingService:
    """Compute net short-term cash parking options."""

    def __init__(
        self,
        *,
        cdi_annual_pct: Decimal,
        selic_annual_pct: Decimal,
        tax_config_rows: list[Any],
    ) -> None:
        self.cdi = Decimal(str(cdi_annual_pct))
        self.selic = Decimal(str(selic_annual_pct))
        self.tax = TaxEngine(tax_config_rows)
        self.iof = IOFEngine()

    async def rank_options(
        self,
        projection: CashFlowProjection,
        *,
        today: date | None = None,
    ) -> CashParkingResponse:
        today = today or date.today()
        amount = projection.available_to_invest
        warnings: list[str] = []
        holding_days = self._holding_days(projection, today, warnings)

        if amount < _MIN_AMOUNT:
            return CashParkingResponse(
                amount=amount,
                holding_days=holding_days,
                rows=[],
                next_big_outflow=projection.next_big_outflow,
                generated_at=datetime.now(timezone.utc),
                warnings=["Valor disponivel abaixo do minimo de R$ 1.000 para recomendacao."],
            )

        if holding_days <= 1:
            return CashParkingResponse(
                amount=amount,
                holding_days=holding_days,
                rows=[],
                next_big_outflow=projection.next_big_outflow,
                generated_at=datetime.now(timezone.utc),
                warnings=["Janela curta demais; IOF tende a consumir quase todo o rendimento."],
            )

        instruments = [
            ("Tesouro Selic", self.selic, True, True, None),
            ("CDB DI 100% CDI", self.cdi, True, True, None),
            ("CDB DI 102% CDI", self.cdi * Decimal("1.02"), True, True, None),
            ("CDB DI 110% CDI", self.cdi * Decimal("1.10"), True, True, None),
            ("Fundo DI 95% CDI", self.cdi * Decimal("0.95"), True, True, "fund_di"),
            ("Poupanca", self._poupanca_rate(), False, False, "poupanca"),
        ]

        rows = [
            self._compute_row(
                amount=amount,
                label=label,
                gross_annual_pct=gross,
                holding_days=holding_days,
                ir_applies=ir_applies,
                iof_applies=iof_applies,
                special=special,
                today=today,
            )
            for label, gross, ir_applies, iof_applies, special in instruments
        ]
        rows.sort(key=lambda row: row.net_pct, reverse=True)
        for rank, row in enumerate(rows, start=1):
            row.rank = rank

        return CashParkingResponse(
            amount=amount,
            holding_days=holding_days,
            rows=rows,
            next_big_outflow=projection.next_big_outflow,
            generated_at=datetime.now(timezone.utc),
            warnings=warnings,
        )

    def _holding_days(
        self,
        projection: CashFlowProjection,
        today: date,
        warnings: list[str],
    ) -> int:
        if projection.next_big_outflow is None:
            return _MAX_HOLDING_DAYS

        days = max(0, (projection.next_big_outflow.date - today).days)
        if days > _MAX_HOLDING_DAYS:
            warnings.append("Janela limitada a 90 dias; use o comparador para prazos maiores.")
            return _MAX_HOLDING_DAYS
        return days

    def _poupanca_rate(self) -> Decimal:
        if self.selic > _POUPANCA_SELIC_THRESHOLD:
            return Decimal("6.17")
        return self.selic * Decimal("0.70")

    def _compute_row(
        self,
        *,
        amount: Decimal,
        label: str,
        gross_annual_pct: Decimal,
        holding_days: int,
        ir_applies: bool,
        iof_applies: bool,
        special: str | None,
        today: date,
    ) -> CashParkingRow:
        compound_pct = self._compound(gross_annual_pct, holding_days)
        gross_brl = (amount * compound_pct / Decimal("100")).quantize(Decimal("0.01"))
        note: str | None = None

        if special == "poupanca" and holding_days < self._days_to_next_monthly_anniversary(today):
            gross_brl = Decimal("0.00")
            note = "Poupanca nao rende se o resgate ocorrer antes do aniversario mensal."

        iof_pct = self.iof.rate_for_days(holding_days) if iof_applies else Decimal("0.00")
        iof_brl = (gross_brl * iof_pct).quantize(Decimal("0.01"))
        after_iof = gross_brl - iof_brl

        if ir_applies and after_iof > 0:
            ir_pct = self.tax.get_rate("renda_fixa", holding_days) / Decimal("100")
        else:
            ir_pct = Decimal("0.00")
        ir_brl = (after_iof * ir_pct).quantize(Decimal("0.01"))
        net_brl = (after_iof - ir_brl).quantize(Decimal("0.01"))
        net_pct = (net_brl / amount * Decimal("100")).quantize(Decimal("0.0001"))

        return CashParkingRow(
            label=label,
            gross_annual_pct=gross_annual_pct.quantize(Decimal("0.0001")),
            holding_days=holding_days,
            iof_pct=iof_pct,
            ir_pct=ir_pct,
            gross_value_brl=gross_brl,
            iof_value_brl=iof_brl,
            ir_value_brl=ir_brl,
            net_value_brl=net_brl,
            net_pct=net_pct,
            rank=0,
            note=note,
        )

    @staticmethod
    def _compound(annual_pct: Decimal, holding_days: int) -> Decimal:
        rate = float(annual_pct) / 100
        compound = (1 + rate) ** (holding_days / 365) - 1
        return Decimal(str(round(compound * 100, 4)))

    @staticmethod
    def _days_to_next_monthly_anniversary(today: date) -> int:
        # Conservative v1 approximation: savings only credits after a 30-day cycle.
        return 30
