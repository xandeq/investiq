"""News ingestion service — fetch CVM + GNews, tag B3 tickers, persist to news_events.

Ticker extraction uses keyword matching (same _TICKER_KEYWORDS dict used in copilot.py).
No LLM required — deterministic, fast, $0 cost.
"""

import logging
import os
import psycopg2
from datetime import datetime, timezone, timedelta
from typing import Any

logger = logging.getLogger(__name__)

# Canonical keyword map — kept in sync with copilot._TICKER_KEYWORDS
_TICKER_KEYWORDS: dict[str, list[str]] = {
    "PETR4": ["petrobras"],
    "PRIO3": ["petrorio", "prio3"],
    "RECV3": ["recôncavo", "reconcavo"],
    "VBBR3": ["vibra"],
    "VALE3": ["vale"],
    "GGBR4": ["gerdau"],
    "CSNA3": ["csn", "siderúrgica nacional"],
    "ITUB4": ["itaú", "itau", "itaubanco"],
    "BBDC4": ["bradesco"],
    "BBAS3": ["banco do brasil", "banco brasil"],
    "SANB11": ["santander"],
    "B3SA3": [" b3 "],
    "BBSE3": ["bb seguridade"],
    "IRBR3": ["irb"],
    "EGIE3": ["engie"],
    "TAEE11": ["taesa"],
    "CMIG4": ["cemig"],
    "ELET3": ["eletrobras"],
    "ENEV3": ["eneva"],
    "CPFE3": ["cpfl"],
    "AURE3": ["auren"],
    "SBSP3": ["sabesp"],
    "CSAN3": ["cosan"],
    "ABEV3": ["ambev"],
    "JBSS3": ["jbs"],
    "SMTO3": ["são martinho", "sao martinho"],
    "BEEF3": ["minerva foods"],
    "LREN3": ["renner"],
    "RENT3": ["localiza"],
    "MOVI3": ["movida"],
    "SUZB3": ["suzano"],
    "KLBN11": ["klabin"],
    "WEGE3": ["weg"],
    "EMBR3": ["embraer"],
    "TOTS3": ["totvs"],
    "LWSA3": ["locaweb"],
    "RDOR3": ["rede d'or", "rdor"],
    "HAPV3": ["hapvida"],
    "RADL3": ["raia drogasil", "drogasil"],
    "FLRY3": ["fleury"],
    "CYRE3": ["cyrela"],
    "MRVE3": ["mrv"],
    "EZTC3": ["eztec"],
    "VIVT3": ["vivo", "telefônica", "telefonica"],
    "TIMS3": ["tim brasil", "tim s.a"],
    # Additional FII/macro keywords
    "BBAS3": ["banco do brasil"],
    "BCFF11": ["bcff11", "btg pactual fundo"],
}


def extract_tickers(text: str) -> list[str]:
    """Extract B3 tickers from a headline/body using keyword matching."""
    text_lower = text.lower()
    matched: list[str] = []
    for ticker, keywords in _TICKER_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            matched.append(ticker)
    # Also check for raw ticker patterns (e.g., "PETR4 subiu")
    import re
    raw_matches = re.findall(r'\b([A-Z]{4}[0-9]{1,2})\b', text.upper())
    for m in raw_matches:
        if m in _TICKER_KEYWORDS and m not in matched:
            matched.append(m)
    return matched


def _get_db_conn():
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL not set")
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://").replace("asyncpg://", "postgresql://")
    return psycopg2.connect(db_url)


def ingest_news_batch(items: list[dict[str, Any]]) -> int:
    """Persist a batch of news items to news_events. Returns count inserted."""
    if not items:
        return 0

    inserted = 0
    try:
        conn = _get_db_conn()
        with conn:
            with conn.cursor() as cur:
                for item in items:
                    headline = item.get("headline", "").strip()
                    if not headline:
                        continue

                    url = item.get("url") or ""
                    source = item.get("source", "unknown")[:32]
                    published_raw = item.get("published_at", "")
                    sentiment = item.get("sentiment")

                    # Parse published_at
                    published_dt: datetime | None = None
                    if published_raw:
                        try:
                            published_dt = datetime.fromisoformat(str(published_raw))
                            if published_dt.tzinfo is None:
                                published_dt = published_dt.replace(tzinfo=timezone.utc)
                        except (ValueError, TypeError):
                            published_dt = datetime.now(timezone.utc)
                    else:
                        published_dt = datetime.now(timezone.utc)

                    tickers = extract_tickers(headline + " " + item.get("summary", ""))

                    # Also use pre-tagged tickers from the adapter if available
                    adapter_tickers = item.get("tickers", [])
                    for t in adapter_tickers:
                        if t not in tickers:
                            tickers.append(t)

                    try:
                        cur.execute(
                            """
                            INSERT INTO news_events
                                (source, headline, url, tickers, sentiment, published_at)
                            VALUES (%s, %s, %s, %s, %s, %s)
                            ON CONFLICT (source, url) DO NOTHING
                            """,
                            (
                                source,
                                headline[:500],
                                url[:1000] if url else None,
                                tickers,
                                sentiment,
                                published_dt,
                            ),
                        )
                        if cur.rowcount:
                            inserted += 1
                    except Exception as exc:
                        logger.debug("news_events insert failed: %s", exc)
        conn.close()
    except Exception as exc:
        logger.error("ingest_news_batch: DB error: %s", exc)

    return inserted


def get_news_for_ticker(ticker: str, hours_back: int = 6) -> list[dict[str, Any]]:
    """Fetch recent news events for a specific ticker (sync, for Celery tasks)."""
    try:
        conn = _get_db_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT headline, url, source, sentiment, published_at
                FROM news_events
                WHERE %s = ANY(tickers)
                  AND published_at >= NOW() - make_interval(hours => %s)
                ORDER BY published_at DESC
                LIMIT 5
                """,
                (ticker, hours_back),
            )
            rows = cur.fetchall()
        conn.close()
        return [
            {
                "headline": r[0],
                "url": r[1],
                "source": r[2],
                "sentiment": float(r[3]) if r[3] is not None else None,
                "published_at": r[4].isoformat() if r[4] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.debug("get_news_for_ticker %s: %s", ticker, exc)
        return []
