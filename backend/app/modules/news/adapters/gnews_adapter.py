"""GNews adapter — free financial news via Google News RSS feed.

Uses Google News RSS (no key required) filtered for Brazilian and
global financial news. Reliable from any server.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any
import xml.etree.ElementTree as ET

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 10
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; InvestIQ/1.0)"}

# Google News RSS topics relevant to investing
_FEEDS = [
    # BR financial news
    ("https://news.google.com/rss/search?q=bovespa+ibovespa+B3+ações&hl=pt-BR&gl=BR&ceid=BR:pt-419", "BR"),
    ("https://news.google.com/rss/search?q=banco+central+selic+dolar+real&hl=pt-BR&gl=BR&ceid=BR:pt-419", "BR"),
    # Global
    ("https://news.google.com/rss/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGx6TVdZU0FtVnVHZ0pDUWlnQVAB?hl=en-US&gl=US&ceid=US:en", "US"),
]


def _parse_rss(xml_text: str, source_tag: str) -> list[dict[str, Any]]:
    """Parse RSS XML and extract news items."""
    results = []
    try:
        root = ET.fromstring(xml_text)
        channel = root.find("channel")
        if channel is None:
            return []
        for item in channel.findall("item")[:15]:
            title = item.findtext("title", "").strip()
            link = item.findtext("link", "").strip()
            pub_date = item.findtext("pubDate", "").strip()
            description = item.findtext("description", "").strip()

            if not title:
                continue

            # Parse pub date
            pub_dt = None
            for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S GMT"):
                try:
                    pub_dt = datetime.strptime(pub_date, fmt)
                    break
                except ValueError:
                    continue

            results.append({
                "headline": title,
                "summary": description[:200] if description else "",
                "url": link,
                "source": f"Google News ({source_tag})",
                "published_at": pub_dt.isoformat() if pub_dt else pub_date,
                "tickers": [],
                "category": "general",
            })
    except ET.ParseError as exc:
        logger.warning("gnews: XML parse error: %s", exc)
    return results


def get_financial_news(hours_back: int = 24) -> list[dict[str, Any]]:
    """Fetch recent financial news from Google News RSS.

    Returns merged list from all feeds, deduplicated, within hours_back window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    all_items: list[dict[str, Any]] = []
    seen_titles: set[str] = set()

    for feed_url, tag in _FEEDS:
        try:
            resp = requests.get(feed_url, timeout=_TIMEOUT, headers=_HEADERS)
            resp.raise_for_status()
            items = _parse_rss(resp.text, tag)
            for item in items:
                title_key = item["headline"][:50].lower()
                if title_key in seen_titles:
                    continue
                seen_titles.add(title_key)

                # Filter by time if we have a date
                pub = item.get("published_at", "")
                if pub:
                    try:
                        dt = datetime.fromisoformat(pub)
                        if dt.tzinfo is None:
                            dt = dt.replace(tzinfo=timezone.utc)
                        if dt < cutoff:
                            continue
                    except ValueError:
                        pass  # Keep if date is unparseable

                all_items.append(item)
        except Exception as exc:
            logger.warning("gnews: feed %s failed: %s", feed_url[:50], exc)
            continue

    return all_items[:20]
