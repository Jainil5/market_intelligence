from __future__ import annotations

import importlib.util
import logging
from pathlib import Path
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from .supabase_client import get_supabase

logger=logging.getLogger(__name__)
PROJECT_ROOT=Path(__file__).resolve().parents[2]

def _load_fetcher():
    path=PROJECT_ROOT/"services"/"ann_fetcher.py"
    if not path.exists(): return None
    spec=importlib.util.spec_from_file_location("project_ann_fetcher",path)
    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return getattr(module,"fetch_corp_ann",None)

def _date(value):
    if not value: return datetime.now(timezone.utc).isoformat()
    if isinstance(value,datetime): return value.astimezone(timezone.utc).isoformat()
    try: return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except Exception: return datetime.now(timezone.utc).isoformat()

def update_announcements_for_all_stocks(stock_id: str | None = None) -> dict:
    fetcher=_load_fetcher()
    if not fetcher: return {"status":"skipped","reason":"Add services/ann_fetcher.py with fetch_corp_ann(stock_id)"}
    q=get_supabase().table("stock_list").select("stock_id").eq("active",True)
    if stock_id: q=q.eq("stock_id",stock_id)
    stocks=q.execute().data or []; total=0; errors=[]
    for stock in stocks:
        try:
            items=fetcher(stock["stock_id"]) or []; rows=[]
            for item in items:
                url=item.get("source_url") or item.get("url")
                title=item.get("title") or item.get("headline")
                if not url or not title: continue
                rows.append({"stock_id":stock["stock_id"],"title":title,"category":item.get("category"),"description":item.get("description"),"source_url":url,"published_at":_date(item.get("published_at"))})
            if rows:
                get_supabase().table("announcements").upsert(rows,on_conflict="stock_id,source_url",ignore_duplicates=True).execute(); total+=len(rows)
        except Exception as exc:
            logger.exception("Announcement update failed for %s",stock["stock_id"]); errors.append({"stock_id":stock["stock_id"],"error":str(exc)})
    return {"stocks_checked":len(stocks),"announcements_submitted":total,"errors":errors}
