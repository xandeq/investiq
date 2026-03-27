"""DBLogHandler — Python logging handler that persists WARNING+ records to app_logs.

Uses the sync DB session (psycopg2) to avoid async complexity in the logging
call stack. Never raises — a broken DB connection must not crash the app.
"""
from __future__ import annotations

import logging
import traceback as tb_mod
import uuid
from datetime import datetime, timezone

from sqlalchemy import text


# Modules whose log records should never be persisted (avoids infinite recursion
# when SQLAlchemy / asyncpg itself emits a log during the INSERT).
_SKIP_LOGGERS = {
    "sqlalchemy",
    "sqlalchemy.engine",
    "sqlalchemy.pool",
    "asyncpg",
    "uvicorn.access",
}


class DBLogHandler(logging.Handler):
    """Saves WARNING+ log records to the app_logs table via psycopg2 (sync)."""

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.WARNING:
            return
        # Skip noisy infra loggers to avoid recursion
        if any(record.name.startswith(skip) for skip in _SKIP_LOGGERS):
            return

        try:
            tb_text: str | None = None
            if record.exc_info:
                tb_text = "".join(tb_mod.format_exception(*record.exc_info))

            # Lazy import to avoid circular deps at module load time
            from app.core.db_sync import get_sync_db_session

            with get_sync_db_session() as session:
                session.execute(
                    text(
                        """
                        INSERT INTO app_logs
                            (id, level, title, message, traceback, module, created_at)
                        VALUES
                            (:id, :level, :title, :message, :traceback, :module, :created_at)
                        """
                    ),
                    {
                        "id": str(uuid.uuid4()),
                        "level": record.levelname,
                        "title": record.getMessage()[:255],
                        "message": record.getMessage(),
                        "traceback": tb_text,
                        "module": record.name,
                        "created_at": datetime.now(tz=timezone.utc),
                    },
                )
        except Exception:
            self.handleError(record)
