"""Pydantic v2 schemas for the AI Analysis module (Phase 12).

Defines the API response contract with data versioning metadata,
analysis request models, and job status tracking.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class DataMetadata(BaseModel):
    """Data provenance metadata attached to every analysis response.

    Ensures users know exactly what data was used, when it was fetched,
    and whether it came from cache.
    """

    data_timestamp: datetime
    data_version_id: str
    data_sources: list[dict] = Field(
        default_factory=list,
        description='Each item: {"source": str, "type": str, "freshness": str}',
    )
    cache_hit: bool
    cache_ttl_seconds: int


class AnalysisResponse(BaseModel):
    """Standard response envelope for all analysis endpoints.

    Always includes a CVM-compliant disclaimer.
    """

    analysis_id: str
    analysis_type: str
    ticker: str
    status: str
    result: dict | None = None
    data_metadata: DataMetadata | None = None
    disclaimer: str
    error_message: str | None = None


class DCFRequest(BaseModel):
    """Request body for Discounted Cash Flow analysis."""

    ticker: str = Field(min_length=4, max_length=10)
    growth_rate: float | None = Field(default=None, ge=0, le=0.20)
    discount_rate: float | None = Field(default=None, ge=0, le=0.30)
    terminal_growth: float | None = Field(default=None, ge=0, le=0.05)


class EarningsRequest(BaseModel):
    """Request body for Earnings analysis (Phase 13 Plan 02)."""

    ticker: str = Field(min_length=4, max_length=10)


class DividendRequest(BaseModel):
    """Request body for Dividend analysis (Phase 13 Plan 02)."""

    ticker: str = Field(min_length=4, max_length=10)


class SectorRequest(BaseModel):
    """Request body for Sector peer comparison (Phase 13 Plan 02)."""

    ticker: str = Field(min_length=4, max_length=10)
    max_peers: int = Field(default=10, ge=3, le=15)


class AnalysisJobStatus(BaseModel):
    """Lightweight status check response for async job polling."""

    job_id: str
    status: str
    message: str | None = None
