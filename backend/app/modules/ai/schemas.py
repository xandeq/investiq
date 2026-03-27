"""Pydantic schemas for the AI analysis engine.

Schemas:
- AnalysisRequest: ticker for asset analysis (POST /ai/analyze/{ticker})
- MacroAnalysisRequest: no fields — uses authenticated user's portfolio allocation
- JobResponse: base response with job metadata (status, timestamps, etc.)
- JobResultResponse: extends JobResponse with the result dict when available
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class AnalysisRequest(BaseModel):
    """Request body for asset analysis (ticker is in the path, not body).

    Kept as an empty request body for extensibility — future versions may
    accept model preferences, analysis depth, etc.
    """
    pass


class MacroAnalysisRequest(BaseModel):
    """Request body for macro portfolio analysis.

    No fields required — the backend fetches the authenticated user's
    current portfolio allocation from PortfolioService.
    """
    pass


class JobResponse(BaseModel):
    """Base job metadata response — returned immediately on 202 Accepted."""

    id: str
    job_type: str
    ticker: str | None = None
    status: str
    created_at: datetime
    completed_at: datetime | None = None
    error_message: str | None = None

    model_config = {"from_attributes": True}


class JobResultResponse(JobResponse):
    """Job response with full result when status == 'completed'."""

    result: dict[str, Any] | None = None
