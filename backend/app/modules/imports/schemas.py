"""Pydantic schemas for the imports module API.

Response schemas mirror the SQLAlchemy models but expose only the fields
needed by the frontend. Decimal fields are serialized as strings (project
convention to preserve precision and match Pydantic v2 JSON serialization).
"""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class ImportJobResponse(BaseModel):
    """Response schema for import job status (without staged rows)."""
    id: str
    file_id: str
    file_type: str  # "pdf" | "csv"
    status: str  # "pending" | "running" | "completed" | "failed" | "confirmed" | "cancelled"
    staging_count: int | None = None
    confirmed_count: int | None = None
    duplicate_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class StagingRowResponse(BaseModel):
    """Response schema for a single staged transaction row."""
    id: str
    ticker: str
    asset_class: str
    transaction_type: str
    transaction_date: date
    quantity: str    # Decimal as string — project convention
    unit_price: str
    total_value: str
    brokerage_fee: str
    irrf_withheld: str
    notes: str
    parser_source: str
    is_duplicate: bool

    model_config = {"from_attributes": True}


class ImportJobDetailResponse(ImportJobResponse):
    """Extended response that includes staged rows (used by GET /jobs/{id})."""
    staged_rows: list[StagingRowResponse] = []


class ConfirmResponse(BaseModel):
    """Response schema for POST /jobs/{id}/confirm."""
    job_id: str
    confirmed_count: int
    duplicate_count: int
    status: str
