"""Synchronous SQLAlchemy engine for Celery worker tasks.

CRITICAL: Celery tasks are synchronous by default. The main FastAPI application
uses asyncpg (async-only driver). Celery workers MUST use a separate sync engine
with psycopg2 — never use the async engine from db.py inside a Celery task.

Pattern:
    from app.core.db_sync import get_sync_db_session

    @celery_app.task
    def my_task():
        with get_sync_db_session() as session:
            result = session.execute(select(MyModel)).scalars().all()

For system-level writes that must bypass RLS (e.g., updating job status from
Celery where the FastAPI transaction may not yet be committed), use
get_superuser_sync_db_session() which connects as the postgres superuser.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session


def _build_sync_url() -> str:
    """Convert asyncpg URL to psycopg2 URL for sync engine."""
    url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://app_user:change_in_production@postgres:5432/investiq",
    )
    # Replace asyncpg driver with psycopg2
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


def _build_superuser_sync_url() -> str:
    """Build psycopg2 URL using superuser (postgres) — bypasses RLS.

    Uses AUTH_DATABASE_URL which connects as the postgres superuser.
    Falls back to replacing app_user with postgres in DATABASE_URL.
    """
    url = os.environ.get(
        "AUTH_DATABASE_URL",
        os.environ.get(
            "DATABASE_URL",
            "postgresql+asyncpg://postgres:postgres@postgres:5432/investiq",
        ),
    )
    return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


# Lazy initialization — engine created on first use, not at import time.
# This prevents import-time DB connection attempts in tests.
_sync_engine = None
_sync_session_factory = None

_superuser_sync_engine = None
_superuser_sync_session_factory = None


def _get_engine():
    global _sync_engine, _sync_session_factory
    if _sync_engine is None:
        _sync_engine = create_engine(
            _build_sync_url(),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
        )
        _sync_session_factory = sessionmaker(_sync_engine, expire_on_commit=False)
    return _sync_engine, _sync_session_factory


def _get_superuser_engine():
    global _superuser_sync_engine, _superuser_sync_session_factory
    if _superuser_sync_engine is None:
        _superuser_sync_engine = create_engine(
            _build_superuser_sync_url(),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=0,
        )
        _superuser_sync_session_factory = sessionmaker(
            _superuser_sync_engine, expire_on_commit=False
        )
    return _superuser_sync_engine, _superuser_sync_session_factory


@contextmanager
def get_sync_db_session(tenant_id: str | None = None) -> Generator[Session, None, None]:
    """Sync DB session for Celery tasks. Optionally sets RLS tenant context.

    Args:
        tenant_id: If provided, executes SET LOCAL rls.tenant_id before yielding.
                   Celery tasks reading market data (not tenant-scoped) pass None.
    """
    _, factory = _get_engine()
    session = factory()
    try:
        if tenant_id:
            from uuid import UUID as _UUID; _UUID(tenant_id)  # validate UUID format
            session.execute(text(f"SET LOCAL rls.tenant_id = '{tenant_id}'"))
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def get_superuser_sync_db_session() -> Generator[Session, None, None]:
    """Sync DB session using postgres superuser — bypasses RLS entirely.

    Use this for system-level writes (e.g., updating AI job status from Celery)
    where:
    1. The row may have been inserted in an uncommitted FastAPI transaction, or
    2. The task must update rows regardless of tenant context.

    NEVER use this for tenant-scoped data reads — use get_sync_db_session(tenant_id).
    """
    _, factory = _get_superuser_engine()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
