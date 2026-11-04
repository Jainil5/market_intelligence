"""
Exchange corporate announcements (NSE + BSE).

- NSE: uses stock_list.symbol (e.g. RELIANCE)
- BSE: uses stock_list.bse_scrip_code (e.g. 500325 for RELIANCE)
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache

import requests

from data_manager.services.retry_utils import retry_call

logger = logging.getLogger(__name__)

_NSE_HOME = "https://www.nseindia.com"
_NSE_ANN_API = "https://www.nseindia.com/api/corporate-announcements"
_BSE_API = "https://api.bseindia.com/BseIndiaAPI/api/AnnGetData/w"
_MAX_RESULTS = 25


@lru_cache(maxsize=1)
def _session(user_agent_key: str) -> requests.Session:
    _ = user_agent_key
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json,text/plain,*/*",
            "Accept-Language": "en-US,en;q=0.9",
        }
    )
    return session


def _parse_nse_datetime(value: str | None) -> str:
    if not value:
        return datetime.now(timezone.utc).isoformat()
    for fmt in ("%d-%b-%Y %H:%M:%S", "%d-%b-%Y"):
        try:
            dt = datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc)
            return dt.isoformat()
        except ValueError:
            continue
    return datetime.now(timezone.utc).isoformat()


def _lookup_stock(stock_id: str) -> dict | None:
    from data_manager.services.supabase_client import get_supabase

    rows = (
        get_supabase()
        .table("stock_list")
        .select("stock_id,symbol,exchange,bse_scrip_code,active")
        .eq("stock_id", stock_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def _fetch_nse_announcements(symbol: str) -> list[dict]:
    session = _session("nse")

    def _call():
        session.get(_NSE_HOME, timeout=20)
        session.headers["Referer"] = f"{_NSE_HOME}/companies-listing/corporate-filings-announcements"
        response = session.get(
            _NSE_ANN_API,
            params={"index": "equities", "symbol": symbol.upper()},
            timeout=20,
        )
        response.raise_for_status()
        return response.json()

    payload = retry_call(_call, label=f"nse.announcements({symbol})")
    if not isinstance(payload, list):
        return []

    items: list[dict] = []
    for row in payload[:_MAX_RESULTS]:
        title = (row.get("desc") or row.get("subject") or "").strip()
        url = row.get("attchmntFile") or row.get("attachment") or row.get("link")
        if not title or not url:
            continue
        if url.startswith("/"):
            url = f"{_NSE_HOME}{url}"
        items.append(
            {
                "title": title,
                "category": row.get("corpanns_type") or "corporate",
                "description": row.get("sm_name") or row.get("symbol"),
                "source_url": url,
                "published_at": _parse_nse_datetime(row.get("an_dt") or row.get("sort_date")),
            }
        )
    return items


def _fetch_bse_announcements(scrip_code: str) -> list[dict]:
    session = _session("bse")
    to_date = date.today()
    from_date = to_date - timedelta(days=120)
    params = {
        "strCat": "-1",
        "strPrevDate": from_date.strftime("%Y%m%d"),
        "strToDate": to_date.strftime("%Y%m%d"),
        "strScrip": scrip_code,
        "strSearch": "P",
    }

    def _call():
        session.headers["Referer"] = "https://www.bseindia.com/corporates/ann.html"
        response = session.get(_BSE_API, params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    payload = retry_call(_call, label=f"bse.announcements({scrip_code})")
    rows = payload if isinstance(payload, list) else payload.get("Table", []) if isinstance(payload, dict) else []
    items: list[dict] = []
    for row in rows[:_MAX_RESULTS]:
        title = (row.get("NEWSSUB") or row.get("NEWS_HEADLINE") or row.get("HEADLINE") or "").strip()
        news_id = row.get("NEWSID") or row.get("NEWS_ID")
        attachment = row.get("ATTACHMENTNAME") or row.get("ATTACHMENT")
        if attachment:
            url = attachment if str(attachment).startswith("http") else f"https://www.bseindia.com/xml-data/corpfiling/AttachHis/{attachment}"
        elif news_id:
            url = f"https://www.bseindia.com/stock-share-price/announcements/{news_id}"
        else:
            url = ""
        if not title or not url:
            continue
        items.append(
            {
                "title": title,
                "category": row.get("CATEGORYNAME") or "corporate",
                "description": row.get("SL_LONG_NAME") or row.get("SCRIP_CD"),
                "source_url": url,
                "published_at": _parse_nse_datetime(row.get("DT_TM") or row.get("NEWS_DT")),
            }
        )
    return items


def fetch_corp_ann(stock_id: str) -> list[dict]:
    stock = _lookup_stock(stock_id)
    if not stock or not stock.get("active", True):
        return []

    exchange = (stock.get("exchange") or "NSE").upper()
    symbol = (stock.get("symbol") or "").strip()
    bse_code = (stock.get("bse_scrip_code") or "").strip()
    items: list[dict] = []

    if exchange in {"NSE", "BOTH"} and symbol:
        try:
            items.extend(_fetch_nse_announcements(symbol))
        except Exception:
            logger.exception("NSE announcement fetch failed for %s (%s)", stock_id, symbol)

    if exchange in {"BSE", "BOTH"} and bse_code:
        try:
            items.extend(_fetch_bse_announcements(bse_code))
        except Exception:
            logger.exception("BSE announcement fetch failed for %s (%s)", stock_id, bse_code)

    if exchange == "BSE" and not bse_code:
        logger.info("Missing bse_scrip_code for BSE stock %s", stock_id)
    return items
