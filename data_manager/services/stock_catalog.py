from __future__ import annotations

from typing import Any

from .supabase_client import get_supabase


def list_stocks(*, active_only: bool = True, include_inactive: bool = False) -> list[dict]:
    query = get_supabase().table("stock_list").select(
        "stock_id,symbol,yfinance_symbol,company_name,exchange,bse_scrip_code,sector,industry,active,fundamentals,latest_prediction,updated_at"
    )
    if active_only and not include_inactive:
        query = query.eq("active", True)
    rows = query.order("stock_id").execute().data or []
    return rows


def get_stock(stock_id: str) -> dict | None:
    rows = (
        get_supabase()
        .table("stock_list")
        .select(
            "stock_id,symbol,yfinance_symbol,company_name,exchange,bse_scrip_code,sector,industry,active,fundamentals,latest_prediction,updated_at"
        )
        .eq("stock_id", stock_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    return rows[0] if rows else None


def get_recent_prices(stock_id: str, limit: int = 90) -> list[dict]:
    limit = max(1, min(limit, 500))
    return (
        get_supabase()
        .table("stock_prices")
        .select("trade_date,open,high,low,close,volume,adj_close")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def get_recent_news(stock_id: str, limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 100))
    return (
        get_supabase()
        .table("news")
        .select("news_id,headline,content,source,source_url,published_at,sentiment,created_at")
        .eq("stock_id", stock_id)
        .order("published_at", desc=True)
        .limit(limit)
        .execute()
        .data
        or []
    )


def create_stock(payload: dict[str, Any]) -> dict:
    row = {
        "stock_id": payload["stock_id"],
        "symbol": payload["symbol"],
        "yfinance_symbol": payload["yfinance_symbol"],
        "company_name": payload.get("company_name"),
        "exchange": payload.get("exchange") or "NSE",
        "bse_scrip_code": payload.get("bse_scrip_code"),
        "sector": payload.get("sector"),
        "industry": payload.get("industry"),
        "active": payload.get("active", True),
    }
    get_supabase().table("stock_list").insert(row).execute()
    return row


def update_stock(stock_id: str, payload: dict[str, Any]) -> dict | None:
    allowed = {
        "symbol",
        "yfinance_symbol",
        "company_name",
        "exchange",
        "bse_scrip_code",
        "sector",
        "industry",
        "active",
    }
    updates = {k: v for k, v in payload.items() if k in allowed and v is not None}
    if not updates:
        return get_stock(stock_id)
    (
        get_supabase()
        .table("stock_list")
        .update(updates)
        .eq("stock_id", stock_id)
        .execute()
    )
    return get_stock(stock_id)
