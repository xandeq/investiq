"""Kelly fractional position sizing for swing trade setups (Sprint 3).

Rules:
- Max 8% of book per position (hard cap)
- Max 5 open positions simultaneously
- Daily drawdown of -2% blocks new entries
- Max 30% sector exposure (not enforced here — caller's responsibility)
- Quarter Kelly: full_kelly / 4 (never bet full Kelly)
"""
from __future__ import annotations

from decimal import Decimal, ROUND_DOWN

MAX_POSITION_PCT = Decimal("0.08")    # 8% of book per position
MAX_OPEN_POSITIONS = 5
DAILY_DRAWDOWN_LIMIT = Decimal("-0.02")  # -2% blocks new entries
MAX_SECTOR_EXPOSURE = Decimal("0.30")   # 30% max per sector (enforcement is caller's job)


def kelly_fraction(
    win_rate: float,
    avg_win_r: float,
    avg_loss_r: float = 1.0,
) -> float:
    """Compute quarter-Kelly fraction.

    Formula: full_kelly = (win_rate * avg_win_r - (1 - win_rate) * avg_loss_r) / avg_win_r
    Returns: max(0, full_kelly / 4)

    Args:
        win_rate: Historical win rate [0, 1]
        avg_win_r: Average win in R-multiples (must be > 0)
        avg_loss_r: Average loss in R-multiples (default 1.0 = 1R)

    Returns:
        Quarter-Kelly fraction [0, 1)
    """
    if avg_win_r <= 0:
        return 0.0
    full_kelly = (win_rate * avg_win_r - (1.0 - win_rate) * avg_loss_r) / avg_win_r
    return max(0.0, full_kelly / 4.0)


def calculate_position_size(
    book_value: Decimal,
    entry: Decimal,
    stop: Decimal,
    win_rate: float = 0.5,
    avg_win_r: float = 2.5,
    open_positions: int = 0,
    daily_pnl_pct: float = 0.0,
) -> dict:
    """Calculate Kelly-based position size with risk management guardrails.

    Args:
        book_value: Total portfolio value in BRL
        entry: Entry price per share
        stop: Stop-loss price per share
        win_rate: Historical win rate (default 50%)
        avg_win_r: Average win in R-multiples (default 2.5R)
        open_positions: Number of currently open positions
        daily_pnl_pct: Today's P&L as fraction (e.g., -0.025 = -2.5%)

    Returns:
        dict with keys:
            fraction (float): Kelly fraction applied [0, 1]
            amount_brl (Decimal): BRL amount to allocate
            shares (int): Number of shares to buy
            blocked (bool): True if position blocked by risk rules
            block_reason (str | None): Reason for block if blocked
            warnings (list[str]): Non-blocking advisory warnings
    """
    warnings: list[str] = []
    blocked = False
    block_reason: str | None = None

    # ── Guard: daily drawdown limit ───────────────────────────────────────────
    if Decimal(str(daily_pnl_pct)) <= DAILY_DRAWDOWN_LIMIT:
        blocked = True
        block_reason = (
            f"Daily drawdown limit reached ({daily_pnl_pct:.1%}). "
            f"No new entries until next session."
        )
        return {
            "fraction": 0.0,
            "amount_brl": Decimal("0"),
            "shares": 0,
            "blocked": True,
            "block_reason": block_reason,
            "warnings": warnings,
        }

    # ── Guard: max open positions ─────────────────────────────────────────────
    if open_positions >= MAX_OPEN_POSITIONS:
        blocked = True
        block_reason = (
            f"Maximum open positions reached ({open_positions}/{MAX_OPEN_POSITIONS}). "
            f"Close an existing position before entering a new one."
        )
        return {
            "fraction": 0.0,
            "amount_brl": Decimal("0"),
            "shares": 0,
            "blocked": True,
            "block_reason": block_reason,
            "warnings": warnings,
        }

    # ── Risk per share (R) ────────────────────────────────────────────────────
    risk_per_share = abs(entry - stop)
    if risk_per_share == 0:
        return {
            "fraction": 0.0,
            "amount_brl": Decimal("0"),
            "shares": 0,
            "blocked": True,
            "block_reason": "Entry and stop prices are identical — cannot calculate risk.",
            "warnings": warnings,
        }

    # ── Kelly fraction ────────────────────────────────────────────────────────
    fraction = kelly_fraction(win_rate, avg_win_r)

    # ── Apply maximum position cap ────────────────────────────────────────────
    fraction_dec = Decimal(str(fraction))
    if fraction_dec > MAX_POSITION_PCT:
        warnings.append(
            f"Kelly fraction {fraction:.1%} capped at max position {float(MAX_POSITION_PCT):.0%}."
        )
        fraction_dec = MAX_POSITION_PCT
        fraction = float(fraction_dec)

    # ── BRL amount ────────────────────────────────────────────────────────────
    amount_brl = (book_value * fraction_dec).quantize(Decimal("0.01"), rounding=ROUND_DOWN)

    # ── Number of shares ──────────────────────────────────────────────────────
    if entry > 0:
        shares = int((amount_brl / entry).to_integral_value(rounding=ROUND_DOWN))
    else:
        shares = 0

    # ── Advisory warnings ─────────────────────────────────────────────────────
    if open_positions >= MAX_OPEN_POSITIONS - 1:
        warnings.append(
            f"One slot remaining ({open_positions}/{MAX_OPEN_POSITIONS} open positions)."
        )

    if daily_pnl_pct < -0.01:
        warnings.append(
            f"Daily P&L is {daily_pnl_pct:.1%} — approaching drawdown limit."
        )

    return {
        "fraction": fraction,
        "amount_brl": amount_brl,
        "shares": shares,
        "blocked": False,
        "block_reason": None,
        "warnings": warnings,
    }
