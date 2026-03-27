"""CMP (Custo Médio Ponderado) — Preço Médio Ponderado calculation engine.

B3/CVM-mandated cost basis methodology for Brazilian investment accounts.
All arithmetic uses Python Decimal (8 decimal places) — never float.

References:
- B3: Instrução CVM 8/1979 (custo médio ponderado)
- CVM Resolution 19/2021 (IR calculation on equity gains)

B3 formula for buy:
    new_cmp = (qty_held × cmp_prev + qty_bought × effective_price) / (qty_held + qty_bought)

Key rules:
- CMP recalculates on EVERY buy
- CMP does NOT change on sell — only P&L is computed
- Corporate events: desdobramento (split), grupamento (reverse split), bonificacao (bonus shares)
- Corporate events preserve total_cost (invariant) for desdobramento and grupamento
- Bonificação adds cost of bonus shares: total_cost increases by bonus_qty × issue_price
- On the same date, corporate actions are applied BEFORE transactions (B3 ex-date rule)

Pure functions: no DB, no Redis, no FastAPI coupling.
The service layer (portfolio/service.py) loads data from DB and calls these functions.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# 8 decimal places — sufficient for CMP precision without float drift
_DP = Decimal("0.00000001")
_ZERO = Decimal("0")


# ---------------------------------------------------------------------------
# Position dataclass
# ---------------------------------------------------------------------------

@dataclass
class Position:
    """Current position state for a single ticker.

    Immutable by convention — all functions return new Position instances.
    Mutation causes hard-to-debug CMP drift in multi-transaction sequences.

    Fields:
        ticker:      Stock/asset symbol (e.g., "PETR4")
        quantity:    Current shares held (Decimal)
        cmp:         Custo Médio Ponderado — weighted average cost per share (Decimal)
        total_cost:  quantity × cmp; invariant across desdobramento/grupamento events
        asset_class: AssetClass enum value as string (e.g., "acao", "fii")
    """
    ticker: str
    quantity: Decimal
    cmp: Decimal
    total_cost: Decimal
    asset_class: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _quantize(value: Decimal) -> Decimal:
    """Round to 8 decimal places with ROUND_HALF_UP (B3 precision standard)."""
    return value.quantize(_DP, rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_buy(
    position: Position,
    qty: Decimal,
    unit_price: Decimal,
    brokerage_fee: Decimal | None = None,
) -> Position:
    """Apply a buy transaction — recalculates CMP using B3 weighted average formula.

    B3 formula:
        new_cmp = (qty_held × cmp_prev + qty_bought × effective_price) / (qty_held + qty_bought)

    Brokerage fee is included in the effective price (B3 cost basis rule):
        effective_price = (qty × unit_price + fee) / qty

    Args:
        position:      Current position state.
        qty:           Number of shares being bought (must be > 0).
        unit_price:    Price per share (before fee).
        brokerage_fee: Total brokerage fee for this transaction (optional).

    Returns:
        New Position with updated quantity, CMP, and total_cost.

    Raises:
        ValueError: If qty is not positive.
    """
    if qty <= _ZERO:
        raise ValueError(f"Buy quantity must be positive, got {qty}")

    # Effective price includes brokerage fee proportionally distributed per share
    fee = brokerage_fee if brokerage_fee is not None else _ZERO
    effective_price = _quantize((qty * unit_price + fee) / qty)

    # B3 CMP formula: weighted average of existing position and new purchase
    if position.quantity == _ZERO:
        # First buy: CMP = purchase price (no previous position to blend)
        new_cmp = effective_price
    else:
        new_cmp = _quantize(
            (position.quantity * position.cmp + qty * effective_price)
            / (position.quantity + qty)
        )

    new_qty = position.quantity + qty
    return Position(
        ticker=position.ticker,
        quantity=new_qty,
        cmp=new_cmp,
        total_cost=_quantize(new_qty * new_cmp),
        asset_class=position.asset_class,
    )


def apply_sell(
    position: Position,
    qty: Decimal,
    sale_price: Decimal,
) -> tuple[Position, Decimal]:
    """Apply a sell transaction — CMP is UNCHANGED. Returns (new_position, realized_pnl).

    B3 rule: selling shares does NOT change the weighted average cost.
    Only P&L is computed from the difference between sale price and CMP.

    P&L formula: realized_pnl = (sale_price - cmp) × qty

    Args:
        position:   Current position state.
        qty:        Number of shares being sold (must be > 0 and ≤ position.quantity).
        sale_price: Price per share received on sale.

    Returns:
        Tuple of (new Position with reduced quantity, realized P&L in R$).
        P&L is positive for a gain, negative for a loss.

    Raises:
        ValueError: If qty is not positive or exceeds current holdings.
    """
    if qty <= _ZERO:
        raise ValueError(f"Sell quantity must be positive, got {qty}")
    if qty > position.quantity:
        raise ValueError(
            f"Cannot sell {qty} shares — only {position.quantity} held for {position.ticker}"
        )

    # CMP NEVER changes on sell — only quantity and total_cost are reduced
    realized_pnl = _quantize((sale_price - position.cmp) * qty)
    new_qty = position.quantity - qty

    return (
        Position(
            ticker=position.ticker,
            quantity=new_qty,
            cmp=position.cmp,        # CMP unchanged — B3 rule
            total_cost=_quantize(new_qty * position.cmp),
            asset_class=position.asset_class,
        ),
        realized_pnl,
    )


def apply_corporate_event(
    position: Position,
    action_type: str,              # CorporateActionType value (e.g., "desdobramento")
    factor: Decimal,
    issue_price: Decimal | None = None,  # Required for bonificacao only
) -> Position:
    """Apply a B3 corporate event — adjusts quantity and CMP.

    desdobramento (split):
        qty × factor, cmp / factor — total_cost invariant
    grupamento (reverse split):
        qty / factor, cmp × factor — total_cost invariant
    bonificacao (bonus shares):
        bonus_qty = qty × factor (e.g., factor=0.10 for 10% bonus)
        new_cmp = (qty × cmp + bonus_qty × issue_price) / (qty + bonus_qty)
        total_cost increases by bonus_qty × issue_price

    Args:
        position:    Current position state.
        action_type: CorporateActionType enum value as string.
        factor:      Split ratio, reverse split ratio, or bonus percentage.
        issue_price: Bonus shares issue price (required for bonificacao).

    Returns:
        New Position with adjusted quantity, CMP, and total_cost.

    Raises:
        ValueError: If action_type is unknown or issue_price is missing for bonificacao.
    """
    if action_type == "desdobramento":
        # Split: shares multiply, price divides — total_cost unchanged
        new_qty = _quantize(position.quantity * factor)
        new_cmp = _quantize(position.cmp / factor)
        return Position(
            ticker=position.ticker,
            quantity=new_qty,
            cmp=new_cmp,
            total_cost=position.total_cost,  # invariant — B3 rule
            asset_class=position.asset_class,
        )

    elif action_type == "grupamento":
        # Reverse split: shares divide, price multiplies — total_cost unchanged
        new_qty = _quantize(position.quantity / factor)
        new_cmp = _quantize(position.cmp * factor)
        return Position(
            ticker=position.ticker,
            quantity=new_qty,
            cmp=new_cmp,
            total_cost=position.total_cost,  # invariant — B3 rule
            asset_class=position.asset_class,
        )

    elif action_type == "bonificacao":
        # Bonus shares: issued at stated issue_price, CMP recalculated
        if issue_price is None:
            raise ValueError("bonificacao requires issue_price parameter")
        # B3 formula: bonus_qty = current_qty × bonus_rate (factor = rate, e.g. 0.10 = 10%)
        bonus_qty = _quantize(position.quantity * factor)
        new_qty = position.quantity + bonus_qty
        # New CMP: weighted average of existing cost basis + bonus shares at issue price
        new_cmp = _quantize(
            (position.quantity * position.cmp + bonus_qty * issue_price) / new_qty
        )
        return Position(
            ticker=position.ticker,
            quantity=new_qty,
            cmp=new_cmp,
            total_cost=_quantize(new_qty * new_cmp),
            asset_class=position.asset_class,
        )

    else:
        raise ValueError(f"Unknown corporate action type: {action_type!r}")


def build_position_from_history(
    ticker: str,
    asset_class: str,
    transactions: list[Any],        # list of Transaction-like duck-typed objects
    corporate_actions: list[Any],   # list of CorporateAction-like duck-typed objects
) -> Position:
    """Build current Position by replaying all events in chronological order.

    B3 ex-date rule: on the same date, corporate actions are applied BEFORE transactions.
    This ensures splits/bonuses correctly adjust cost basis before same-day trades.

    Duck-typed inputs (no SQLAlchemy dependency):
    - transactions: objects with .transaction_date, .transaction_type, .quantity,
                    .unit_price, and optional .brokerage_fee
    - corporate_actions: objects with .action_date, .action_type, .factor,
                         and optional .issue_price

    Args:
        ticker:            Asset symbol.
        asset_class:       AssetClass enum value as string.
        transactions:      List of transaction records (buy/sell/etc.).
        corporate_actions: List of corporate event records.

    Returns:
        Final Position after all events have been applied.
    """
    position = Position(
        ticker=ticker,
        quantity=_ZERO,
        cmp=_ZERO,
        total_cost=_ZERO,
        asset_class=asset_class,
    )

    # Build unified timeline: (event_date, priority, event)
    # priority 0 = corporate action (applied first on same date — B3 ex-date rule)
    # priority 1 = transaction
    timeline: list[tuple[date, int, Any]] = []

    for ca in corporate_actions:
        timeline.append((ca.action_date, 0, ca))
    for tx in transactions:
        timeline.append((tx.transaction_date, 1, tx))

    # Sort by (date, priority) — ensures corporate events precede same-date transactions
    timeline.sort(key=lambda e: (e[0], e[1]))

    for _, _, event in timeline:
        if hasattr(event, "action_type"):
            # CorporateAction — dispatch to apply_corporate_event
            issue_price = getattr(event, "issue_price", None)
            position = apply_corporate_event(
                position,
                event.action_type,
                event.factor,
                issue_price,
            )
        elif event.transaction_type in ("buy",):
            # Buy transaction — recalculate CMP
            position = apply_buy(
                position,
                event.quantity,
                event.unit_price,
                getattr(event, "brokerage_fee", None),
            )
        elif event.transaction_type in ("sell",):
            # Sell transaction — CMP unchanged, quantity reduced
            position, _ = apply_sell(position, event.quantity, event.unit_price)
        # dividend, jscp, amortization: do not affect CMP or quantity — skip

    return position
