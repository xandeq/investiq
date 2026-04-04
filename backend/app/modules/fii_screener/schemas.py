"""Pydantic schemas for the FII Scored Screener endpoint.

GET /fii-screener/ranked returns FIIs pre-ranked by composite score:
  score = DY_rank*0.5 + PVP_rank_inverted*0.3 + liquidity_rank*0.2

Scores are pre-calculated nightly by the calculate_fii_scores Celery task.
FIIs without sufficient data (NULL metrics) receive score=None and appear at bottom.
"""
from __future__ import annotations

from pydantic import BaseModel

# CVM Res. 19/2021 mandatory disclaimer
CVM_DISCLAIMER = "Analise informativa — nao constitui recomendacao de investimento (CVM Res. 19/2021)"


class FIIScoredRow(BaseModel):
    """Single FII row with pre-calculated composite score."""

    ticker: str
    short_name: str | None = None
    segmento: str | None = None
    dy_12m: str | None = None          # DY 12m as percentage string (e.g. "8.5")
    pvp: str | None = None             # P/VP as string
    daily_liquidity: int | None = None # Average daily volume (R$)
    score: str | None = None           # Composite score 0-100 as string
    dy_rank: int | None = None         # DY percentile rank (0-100)
    pvp_rank: int | None = None        # P/VP percentile rank inverted (lower P/VP = higher rank)
    liquidity_rank: int | None = None  # Liquidity percentile rank (0-100)
    score_updated_at: str | None = None  # ISO 8601 timestamp of last score calculation


class FIIScoredResponse(BaseModel):
    """Response for GET /fii-screener/ranked."""

    disclaimer: str = CVM_DISCLAIMER
    score_available: bool = True        # False if calculate_fii_scores has not run yet
    total: int
    results: list[FIIScoredRow]
