import logging
import sys
from app.core.config import settings


def configure_logging() -> None:
    """Configure logging for the application.

    Uses JSON format in production for structured log ingestion.
    Uses plain text with color-friendly format in development.
    """
    if settings.ENVIRONMENT == "production":
        # JSON format for production log aggregators (Loki, CloudWatch, etc.)
        log_format = (
            '{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # Human-readable format for development
        log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    logging.basicConfig(
        level=logging.DEBUG if settings.ENVIRONMENT == "development" else logging.INFO,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Attach DB handler — persists WARNING+ to app_logs table
    from app.core.log_handler import DBLogHandler
    db_handler = DBLogHandler()
    db_handler.setLevel(logging.WARNING)
    logging.getLogger().addHandler(db_handler)

    # Quiet noisy third-party loggers in production
    if settings.ENVIRONMENT != "development":
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
        logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
