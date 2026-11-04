from __future__ import annotations

import os
import re
import logging
from urllib.parse import quote_plus
import feedparser

logger = logging.getLogger(__name__)

def _query_url(query: str) -> str:
    country = os.getenv("NEWS_COUNTRY", "IN")
    language = os.getenv("NEWS_LANGUAGE", "en")
    hl = "en-IN" if country == "IN" and language == "en" else f"{language}-{country}"
    return f"https://news.google.com/rss/search?q={quote_plus(query)}&hl={hl}&gl={country}&ceid={country}:{language}"

def fetch_google_news(stock: dict, max_results: int | None = None) -> list[dict]:
    """Free Google News RSS search. Results are headlines/metadata, not full article text."""
    query = stock.get("company_name") or stock.get("symbol")
    if not query: return []
    # Include ticker as a secondary search hint; avoid over-constraining query.
    symbol = stock.get("symbol")
    search = f'"{query}"' + (f' OR {symbol}' if symbol else "")
    feed = feedparser.parse(_query_url(search))
    limit = max_results or int(os.getenv("NEWS_MAX_RESULTS", "15"))
    results=[]
    for entry in feed.entries[:limit]:
        title = re.sub(r"\s+", " ", getattr(entry, "title", "")).strip()
        url = getattr(entry, "link", "")
        if not title or not url: continue
        source = getattr(getattr(entry, "source", {}), "title", None) or "Google News RSS"
        results.append({
            "headline": title,
            "content": getattr(entry, "summary", None),
            "source": source,
            "source_url": url,
            "published_at": getattr(entry, "published", None),
        })
    return results
