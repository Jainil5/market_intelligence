from __future__ import annotations

import importlib.util
import logging
import os
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from .supabase_client import get_supabase
from .google_news_fetcher import fetch_google_news

logger = logging.getLogger(__name__)
PROJECT_ROOT = Path(__file__).resolve().parents[2]

def _enabled_news_providers() -> set[str]:
    raw = os.getenv("NEWS_PROVIDERS", "google_rss,custom")
    return {p.strip().lower() for p in raw.split(",") if p.strip()}

def _load_external_fetcher():
    path = PROJECT_ROOT / "services" / "news_fetcher.py"
    if not path.exists(): return None
    spec = importlib.util.spec_from_file_location("project_news_fetcher", path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return getattr(module, "fetch_news", None)

def _normalise_date(value):
    if not value: return datetime.now(timezone.utc).isoformat()
    if isinstance(value, datetime): return value.astimezone(timezone.utc).isoformat()
    try: return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception: return datetime.now(timezone.utc).isoformat()

def _insert_news(stock: dict, articles: list[dict]) -> int:
    rows=[]
    for article in articles:
        url = article.get("source_url") or article.get("url")
        headline = article.get("headline") or article.get("title")
        if not url or not headline: continue
        rows.append({"stock_id": stock["stock_id"], "headline": headline, "content": article.get("content") or article.get("summary"), "source": article.get("source") or "Unknown", "source_url": url, "published_at": _normalise_date(article.get("published_at") or article.get("published"))})
    if not rows: return 0
    # source_url is unique per stock; duplicates from repeated RSS runs are ignored.
    get_supabase().table("news").upsert(rows, on_conflict="stock_id,source_url", ignore_duplicates=True).execute()
    return len(rows)

def update_news_for_all_stocks(stock_id: str | None = None) -> dict:
    q=get_supabase().table("stock_list").select("stock_id,symbol,company_name,active")
    if stock_id: q=q.eq("stock_id", stock_id)
    else: q=q.eq("active", True)
    stocks=q.execute().data or []
    external=_load_external_fetcher()
    providers = _enabled_news_providers()
    total=0; errors=[]
    for stock in stocks:
        try:
            articles: list[dict] = []
            if "google_rss" in providers:
                articles.extend(fetch_google_news(stock))
            if "custom" in providers and external:
                try:
                    custom=external(stock["stock_id"]) or []
                    articles.extend(custom)
                except Exception:
                    logger.exception("Custom news fetch failed for %s", stock["stock_id"])
            total += _insert_news(stock, articles)
        except Exception as exc:
            logger.exception("News update failed for %s", stock["stock_id"]); errors.append({"stock_id":stock["stock_id"],"error":str(exc)})
    return {"stocks_checked":len(stocks),"articles_submitted":total,"errors":errors}
