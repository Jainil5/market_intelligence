"""
Custom news: Moneycontrol RSS filtered by company name / NSE symbol.
Runs when NEWS_PROVIDERS includes custom (alongside Google RSS if enabled).
"""
from __future__ import annotations

import logging
import os
import re

import feedparser

logger = logging.getLogger(__name__)

_MC_RSS = "https://www.moneycontrol.com/rss/latestnews.xml"


def _lookup_stock(stock_id: str) -> dict | None:
    from data_manager.services.supabase_client import get_supabase

    rows = (
        get_supabase()
        .table("stock_list")
        .select("stock_id,symbol,company_name,active")
        .eq("stock_id", stock_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _matches(entry_title: str, *, symbol: str | None, company: str | None) -> bool:
    title = entry_title.lower()
    if symbol and re.search(rf"\b{re.escape(symbol.lower())}\b", title):
        return True
    if company:
        tokens = [t for t in re.split(r"\W+", company.lower()) if len(t) > 3]
        if tokens and sum(1 for t in tokens[:3] if t in title) >= min(2, len(tokens)):
            return True
    return False


def fetch_news(stock_id: str) -> list[dict]:
    stock = _lookup_stock(stock_id)
    if not stock or not stock.get("active", True):
        return []
    if os.getenv("MONEYCONTROL_NEWS_ENABLED", "true").lower() not in {"1", "true", "yes", "on"}:
        return []

    try:
        feed = feedparser.parse(_MC_RSS)
    except Exception:
        logger.exception("Moneycontrol RSS parse failed")
        return []

    symbol = stock.get("symbol")
    company = stock.get("company_name")
    limit = int(os.getenv("MONEYCONTROL_NEWS_MAX", "10"))
    articles: list[dict] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()
        if not title or not url:
            continue
        if not _matches(title, symbol=symbol, company=company):
            continue
        articles.append(
            {
                "headline": title,
                "content": getattr(entry, "summary", None),
                "source": "Moneycontrol",
                "source_url": url,
                "published_at": getattr(entry, "published", None),
            }
        )
        if len(articles) >= limit:
            break
    return articles
