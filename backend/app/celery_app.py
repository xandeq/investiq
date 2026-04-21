"""Celery application factory for InvestIQ.

Architecture decisions:
- Redis is used as BOTH broker AND result backend (same Redis instance, different key namespaces)
- Beat runs as a separate Docker service -- do not embed beat in worker
- Tasks that need DB use db_sync.py (psycopg2 sync engine), NOT the asyncpg engine
- Market hours: B3 trades Mon-Fri 10h00-17h30 BRT (UTC-3 = 13h00-20h30 UTC)
  We use 10h-17h BRT = 13h-20h UTC for conservative scheduling
- brapi.dev Startup plan note: free tier has 15,000 req/month cap.
  At 15-min intervals, 6h market day = 24 requests/day × 20 tickers = 480 req/day.
  Monthly: ~10,560 requests -- within free tier for dev. Startup plan (R$59.99/mo) for prod.

Celery-asyncpg mismatch (critical):
- FastAPI uses asyncpg (async-only driver) -- cannot be used inside Celery sync tasks
- Celery workers use psycopg2 (sync) via db_sync.py
- NEVER import async_session_factory from app.core.db inside Celery tasks

Queue starvation prevention (see docs/audit/P0_INVESTIGATION.md):
- Every Beat entry carries `options.expires` = interval - 1min.
- Stale copies are discarded automatically if the worker is backlogged.
- scan_crypto reduced 15min → 30min to halve the 24/7 load on the queue.
"""
from __future__ import annotations

import os
from celery import Celery
from celery.schedules import crontab


def create_celery_app() -> Celery:
    redis_url = os.environ.get("REDIS_URL") or "redis://redis:6379/0"

    app = Celery(
        "investiq",
        broker=redis_url,
        backend=redis_url,
        include=[
            "app.modules.market_data.tasks",
            "app.modules.ai.tasks",
            "app.modules.imports.tasks",
            "app.modules.insights.tasks",
            "app.modules.watchlist.tasks",
            "app.modules.screener.tasks",
            "app.modules.market_universe.tasks",
            "app.modules.wizard.tasks",
            "app.modules.advisor.tasks",
            "app.modules.analysis.tasks",
            "app.modules.opportunity_detector.scanner",
            "app.modules.dashboard.tasks",
            "app.modules.dashboard.digest_tasks",
            "app.modules.billing.tasks",
        ],
    )

    app.conf.update(
        # Serialization
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        # Timezone (BRT = UTC-3)
        timezone="America/Sao_Paulo",
        enable_utc=True,
        # Task behavior
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # Result TTL: keep task results for 1h
        result_expires=3600,
        # Beat schedule
        beat_schedule={
            "refresh-quotes-market-hours": {
                "task": "app.modules.market_data.tasks.refresh_quotes",
                # Every 15 min, Mon-Fri, 10h00-17h00 BRT (10-17 in America/Sao_Paulo)
                "schedule": crontab(minute="*/15", hour="10-17", day_of_week="1-5"),
                "args": [],
                "options": {"expires": 13 * 60},  # 13 min — discard before next fire
            },
            "refresh-macro-every-6h": {
                "task": "app.modules.market_data.tasks.refresh_macro",
                "schedule": crontab(minute=0, hour="*/6"),
                "args": [],
                "options": {"expires": 6 * 3600 - 60},  # just under 6h
            },
            "generate-daily-insights": {
                "task": "app.modules.insights.tasks.generate_daily_insights",
                # 8h BRT every day
                "schedule": crontab(minute=0, hour=8),
                "args": [],
                "options": {"expires": 23 * 3600},
            },
            "check-price-alerts": {
                "task": "app.modules.watchlist.tasks.check_price_alerts",
                # Every 15 min, Mon-Fri, 10h00-17h00 BRT -- aligned with quote refresh
                "schedule": crontab(minute="*/15", hour="10-17", day_of_week="1-5"),
                "args": [],
                "options": {"expires": 13 * 60},
            },
            "cleanup-stale-screener-runs": {
                "task": "screener.cleanup_stale_runs",
                # Every 15 min, all day
                "schedule": crontab(minute="*/15"),
                "args": [],
                "options": {"expires": 13 * 60},
            },
            "refresh-screener-universe-daily": {
                "task": "app.modules.market_universe.tasks.refresh_screener_universe",
                # 7h BRT Mon-Fri -- runs before market open at 10h BRT
                "schedule": crontab(minute=0, hour=7, day_of_week="1-5"),
                "args": [],
                "options": {"expires": 23 * 3600},
            },
            "refresh-fii-metadata-weekly": {
                "task": "app.modules.market_universe.tasks.refresh_fii_metadata",
                # Monday at 06:00 BRT -- runs before screener universe at 07h
                "schedule": crontab(minute=0, hour=6, day_of_week="1"),
                "args": [],
                "options": {"expires": 7 * 24 * 3600 - 3600},
            },
            "refresh-tesouro-rates-6h": {
                "task": "app.modules.market_universe.tasks.refresh_tesouro_rates",
                # Every 6 hours -- ANBIMA rates update intraday
                "schedule": crontab(minute=0, hour="*/6"),
                "args": [],
                "options": {"expires": 6 * 3600 - 60},
            },
            "check-earnings-releases-nightly": {
                "task": "analysis.check_earnings_releases",
                # 22h BRT, Mon-Fri -- after market close and filing updates
                "schedule": crontab(minute=0, hour=22, day_of_week="1-5"),
                "args": [],
                "options": {"expires": 23 * 3600},
            },
            # Phase 17: FII Scored Screener -- after screener universe refresh at 07h
            "calculate-fii-scores-daily": {
                "task": "app.modules.market_universe.tasks.calculate_fii_scores",
                "schedule": crontab(minute=0, hour=8),
                "args": [],
                "options": {"expires": 23 * 3600},
            },
            # Opportunity Detector
            "opportunity-detector-acoes": {
                "task": "opportunity_detector.scan_acoes",
                # Every 15min, Mon-Fri, 10h-17h BRT -- aligned with quote refresh
                "schedule": crontab(minute="*/15", hour="10-17", day_of_week="1-5"),
                "args": [],
                "options": {"expires": 13 * 60},
            },
            "opportunity-detector-crypto": {
                "task": "opportunity_detector.scan_crypto",
                # Every 30min, 24/7 -- halved from 15min to reduce queue pressure
                "schedule": crontab(minute="*/30"),
                "args": [],
                "options": {"expires": 28 * 60},  # 28 min — discard before next fire
            },
            "opportunity-detector-fixed-income": {
                "task": "opportunity_detector.scan_fixed_income",
                # Every 6h -- aligned with tesouro rate refresh
                "schedule": crontab(minute=30, hour="*/6"),
                "args": [],
                "options": {"expires": 6 * 3600 - 60},
            },
            # Trial expiry warnings — daily 09:00 BRT
            "check-expiring-trials": {
                "task": "app.modules.billing.tasks.check_expiring_trials",
                "schedule": crontab(minute=0, hour=9),
                "args": [],
                "options": {"expires": 23 * 3600},
            },
            # Weekly portfolio digest — every Monday 08:00 BRT
            "send-weekly-portfolio-digest": {
                "task": "app.modules.dashboard.digest_tasks.send_weekly_digest",
                "schedule": crontab(minute=0, hour=8, day_of_week="1"),
                "args": [],
                "options": {"expires": 7 * 24 * 3600 - 3600},
            },
            # Portfolio EOD snapshot — runs at 18h30 BRT after B3 closes at 17h30
            "snapshot-portfolio-daily-value": {
                "task": "app.modules.dashboard.tasks.snapshot_portfolio_daily_value",
                "schedule": crontab(minute=30, hour=18, day_of_week="1-5"),
                "args": [],
                "options": {"expires": 23 * 3600},
            },
            # Observability: alert if macro data is stale > 2h
            "check-macro-freshness": {
                "task": "app.modules.market_data.tasks.check_macro_freshness",
                "schedule": crontab(minute="*/30"),
                "args": [],
                "options": {"expires": 28 * 60},
            },
            # Phase 26: Universe entry signals — daily at 02h BRT (after screener refresh at 07h-1 day)
            "refresh-universe-entry-signals-daily": {
                "task": "advisor.refresh_universe_entry_signals",
                "schedule": crontab(minute=0, hour=2),
                "args": [],
            },
        },
    )

    return app


celery_app = create_celery_app()
