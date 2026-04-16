"""Billing Celery tasks — trial expiry warnings and lifecycle hooks.

check_expiring_trials:
  Runs daily at 09:00 BRT.
  Finds all users whose trial expires within the next 3 days
  AND trial_warning_sent = False.
  Sends a "trial expiring soon" email and sets trial_warning_sent = True.

Design:
- Uses sync psycopg2 (Celery rule — never asyncpg in tasks)
- Idempotent: trial_warning_sent flag prevents duplicate sends
- Non-fatal: errors per-user are caught and logged individually
- Uses billing.email_templates for consistent HTML email format
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import text

from app.core.db_sync import get_superuser_sync_db_session
from app.core.email import send_email
from app.modules.billing.email_templates import trial_expiring_soon_email

logger = logging.getLogger(__name__)

_WARN_DAYS_BEFORE = 3   # send warning N days before trial ends
_WARN_WINDOW_DAYS = 1   # look for trials expiring within N days of the warning threshold


@shared_task(name="app.modules.billing.tasks.check_expiring_trials")
def check_expiring_trials() -> None:
    """Send trial-expiry warning emails to users whose trial ends in ~3 days.

    Idempotent: trial_warning_sent=True marks users that already received the email.
    Runs daily at 09:00 BRT so warnings land at the start of the Brazilian workday.
    """
    now = datetime.now(tz=timezone.utc)
    warn_start = now + timedelta(days=_WARN_DAYS_BEFORE - _WARN_WINDOW_DAYS)
    warn_end = now + timedelta(days=_WARN_DAYS_BEFORE + _WARN_WINDOW_DAYS)

    with get_superuser_sync_db_session() as session:
        rows = session.execute(text("""
            SELECT id, email, trial_ends_at
            FROM users
            WHERE is_verified = TRUE
              AND plan = 'free'
              AND trial_warning_sent = FALSE
              AND trial_ends_at IS NOT NULL
              AND trial_ends_at >= :warn_start
              AND trial_ends_at <= :warn_end
            ORDER BY trial_ends_at ASC
        """), {"warn_start": warn_start, "warn_end": warn_end}).fetchall()

    if not rows:
        logger.info("check_expiring_trials: no expiring trials to warn")
        return

    logger.info("check_expiring_trials: found %d users with expiring trials", len(rows))

    sent = 0
    errors = 0

    for row in rows:
        user_id, email, trial_ends_at = row
        if trial_ends_at.tzinfo is None:
            trial_ends_at = trial_ends_at.replace(tzinfo=timezone.utc)

        days_remaining = max(0, (trial_ends_at - now).days)

        try:
            subject, html = trial_expiring_soon_email(
                user_email=email,
                days_remaining=days_remaining,
                trial_ends_at=trial_ends_at,
            )
            send_email(to=email, subject=subject, html=html)

            # Mark warning as sent — prevents duplicate in subsequent daily runs
            with get_superuser_sync_db_session() as session:
                session.execute(text("""
                    UPDATE users
                    SET trial_warning_sent = TRUE, updated_at = :now
                    WHERE id = :uid
                """), {"uid": user_id, "now": now})

            logger.info(
                "check_expiring_trials: sent warning to %s (days_remaining=%d, expires=%s)",
                email, days_remaining, trial_ends_at.date(),
            )
            sent += 1

        except Exception as exc:
            logger.error(
                "check_expiring_trials: failed for user %s: %s",
                email, exc, exc_info=True,
            )
            errors += 1

    logger.info("check_expiring_trials: done — sent=%d errors=%d", sent, errors)
