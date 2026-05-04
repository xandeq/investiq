"""Reddit adapter — sentiment data from r/investimentos via public JSON API.

No authentication required. Uses the Reddit public JSON search endpoint
(60 req/min unauthenticated). Targets Brazilian investing subreddits.
"""

import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any

import requests

logger = logging.getLogger(__name__)

_TIMEOUT = 10
_HEADERS = {
    "User-Agent": "InvestIQ/2.0 sentiment-bot (contact: investiq.com.br)",
}
_SUBREDDITS = ["investimentos", "acoes", "fiis", "brasil"]

# Simple PT-BR sentiment keywords for scoring Reddit posts
_POSITIVE = {
    "alta", "subindo", "comprar", "buy", "bullish", "positivo", "crescimento",
    "lucro", "resultado", "superar", "oportunidade", "entrada", "valorização",
    "recomendo", "potencial", "forte", "ótimo", "excelente", "crescer",
    "dividendo", "rendimento", "ganho", "recuperação", "upside", "long",
}
_NEGATIVE = {
    "queda", "caindo", "vender", "sell", "bearish", "negativo", "prejuízo",
    "risco", "medo", "sair", "perda", "cair", "romper", "suporte", "stop",
    "fraco", "ruim", "péssimo", "cuidado", "atenção", "short", "downside",
    "crise", "calote", "falência", "dívida",
}


def _score_text(text: str) -> float:
    """Simple keyword-based sentiment score from -1.0 to 1.0."""
    words = set(text.lower().split())
    pos = len(words & _POSITIVE)
    neg = len(words & _NEGATIVE)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


def get_reddit_sentiment(ticker: str, hours_back: int = 24) -> dict[str, Any]:
    """Fetch Reddit posts mentioning ticker and compute aggregate sentiment.

    Searches public subreddits without authentication. Returns:
        {
            "ticker": str,
            "source": "reddit",
            "score": float,          # average sentiment [-1, 1]
            "mention_count": int,
            "sample_posts": list[str],
            "window_hours": int,
        }
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_back)
    all_posts: list[dict] = []
    seen_ids: set[str] = set()

    # Search top subreddits for the ticker
    for sub in _SUBREDDITS[:2]:  # limit to 2 to stay under rate limits
        url = (
            f"https://www.reddit.com/r/{sub}/search.json"
            f"?q={ticker}&restrict_sr=on&sort=new&t=day&limit=25"
        )
        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            posts = data.get("data", {}).get("children", [])
            for post in posts:
                p = post.get("data", {})
                post_id = p.get("id", "")
                if post_id in seen_ids:
                    continue
                seen_ids.add(post_id)

                created = p.get("created_utc", 0)
                created_dt = datetime.fromtimestamp(created, tz=timezone.utc) if created else None
                if created_dt and created_dt < cutoff:
                    continue

                title = p.get("title", "")
                body = p.get("selftext", "")[:300]
                if ticker.upper() not in (title + body).upper():
                    continue

                all_posts.append({
                    "id": post_id,
                    "text": f"{title} {body}".strip(),
                    "upvotes": p.get("score", 0),
                    "created": created,
                })
        except Exception as exc:
            logger.debug("reddit: %s/%s fetch failed: %s", sub, ticker, exc)
        time.sleep(0.3)  # be a good citizen

    if not all_posts:
        return {
            "ticker": ticker,
            "source": "reddit",
            "score": 0.0,
            "mention_count": 0,
            "sample_posts": [],
            "window_hours": hours_back,
        }

    scores = [_score_text(p["text"]) for p in all_posts]
    avg_score = round(sum(scores) / len(scores), 3)
    sample = [p["text"][:120] for p in sorted(all_posts, key=lambda x: x["upvotes"], reverse=True)[:3]]

    return {
        "ticker": ticker,
        "source": "reddit",
        "score": avg_score,
        "mention_count": len(all_posts),
        "sample_posts": sample,
        "window_hours": hours_back,
    }
