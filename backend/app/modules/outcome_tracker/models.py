"""SQLAlchemy model for signal_outcomes table (Sprint 3)."""
from __future__ import annotations

from sqlalchemy import Column, Date, DateTime, Numeric, String
from sqlalchemy.sql import func

from app.modules.auth.models import Base


class SignalOutcome(Base):
    __tablename__ = "signal_outcomes"

    id = Column(String, primary_key=True)
    tenant_id = Column(String, nullable=False)
    ticker = Column(String, nullable=False)
    pattern = Column(String)
    direction = Column(String, nullable=False)
    entry_price = Column(Numeric(18, 4), nullable=False)
    stop_price = Column(Numeric(18, 4), nullable=False)
    target_1 = Column(Numeric(18, 4))
    target_2 = Column(Numeric(18, 4))
    exit_price = Column(Numeric(18, 4))
    exit_date = Column(Date)
    status = Column(String, nullable=False, default="open")
    r_multiple = Column(Numeric(8, 4))
    signal_grade = Column(String)
    signal_score = Column(Numeric(6, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
