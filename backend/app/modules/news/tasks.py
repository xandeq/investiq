"""Celery tasks for sentiment data ingestion.

Runs every 30min during B3 market hours (10h-17h BRT Mon-Fri).
Fetches Reddit + StockTwits sentiment for COPILOT_UNIVERSE tickers
and persists to sentiment_snapshots table.
"""

import logging
import time
from decimal import Decimal

from app.celery_app import celery_app

logger = logging.getLogger(__name__)

# Subset of COPILOT_UNIVERSE — most liquid, most discussed on social media
# Full universe scan runs every 30min; this list keeps each run under 3 min
_SENTIMENT_UNIVERSE = [
    "PETR4", "VALE3", "ITUB4", "BBDC4", "BBAS3",
    "ELET3", "WEGE3", "EMBR3", "SUZB3", "JBSS3",
    "ABEV3", "RENT3", "RDOR3", "EGIE3", "VIVT3",
    "PRIO3", "CSAN3", "B3SA3", "SBSP3", "TOTS3",
]


def _write_snapshot(ticker: str, source: str, result: dict) -> None:
    """Persist one sentiment snapshot to the database using psycopg2 (sync)."""
    import json
    import os
    import psycopg2

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.warning("news.tasks: DATABASE_URL not set — cannot persist snapshot")
        return

    # Convert asyncpg URL to psycopg2 format
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("asyncpg://", "postgresql://")

    score = result.get("score", 0.0)
    mention_count = result.get("mention_count", 0)
    sample_posts = result.get("sample_posts", [])
    window_hours = result.get("window_hours", 24)

    try:
        conn = psycopg2.connect(db_url)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sentiment_snapshots
                        (ticker, source, score, mention_count, sample_posts, window_hours)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (ticker, source, Decimal(str(score)), mention_count, json.dumps(sample_posts), window_hours),
                )
        conn.close()
    except Exception as exc:
        logger.error("news.tasks: DB write failed for %s/%s: %s", ticker, source, exc)


@celery_app.task(name="news.ingest_sentiment_snapshots")
def ingest_sentiment_snapshots() -> dict:
    """Fetch Reddit + StockTwits sentiment for top B3 tickers.

    Processes _SENTIMENT_UNIVERSE sequentially with rate-limit delays.
    Writes one row per (ticker, source) per run to sentiment_snapshots.
    """
    from app.modules.news.adapters.reddit_adapter import get_reddit_sentiment
    from app.modules.news.adapters.stocktwits_adapter import get_stocktwits_sentiment

    processed = 0
    errors = 0

    for ticker in _SENTIMENT_UNIVERSE:
        # Reddit
        try:
            reddit_result = get_reddit_sentiment(ticker, hours_back=24)
            if reddit_result["mention_count"] > 0:
                _write_snapshot(ticker, "reddit", reddit_result)
                processed += 1
        except Exception as exc:
            logger.warning("news.tasks: Reddit failed for %s: %s", ticker, exc)
            errors += 1

        time.sleep(0.5)  # respect Reddit rate limits

        # StockTwits
        try:
            st_result = get_stocktwits_sentiment(ticker, hours_back=24)
            if st_result["mention_count"] > 0:
                _write_snapshot(ticker, "stocktwits", st_result)
                processed += 1
        except Exception as exc:
            logger.debug("news.tasks: StockTwits failed for %s: %s", ticker, exc)
            # StockTwits has limited B3 coverage — debug only

        time.sleep(0.3)

    logger.info("news.ingest_sentiment_snapshots: processed=%d errors=%d", processed, errors)
    return {"status": "ok", "processed": processed, "errors": errors}
