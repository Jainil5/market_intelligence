from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from data_manager.deps import ApiKeyDep
from data_manager.services.market_summary import build_market_overview, build_stock_snapshot
from data_manager.services.market_data import using_demo_market
from data_manager.services.demo_market import get_demo_stock, get_demo_prices, list_demo_stocks
from data_manager.services.stock_catalog import (
    get_recent_announcements,
    get_recent_news,
    get_recent_prices,
    get_stock,
    list_stocks,
)

router = APIRouter(prefix="/stocks", tags=["read"])


@router.get("/overview/market")
def market_overview(_: ApiKeyDep, price_limit: int = Query(default=5, ge=1, le=30)):
    stocks = build_market_overview(price_limit=price_limit)
    source = "yfinance_demo" if using_demo_market() else "supabase"
    return {"stocks": stocks, "data_source": source}


def _resolve_stock(stock_id: str) -> dict | None:
    if using_demo_market():
        return get_demo_stock(stock_id)
    return get_stock(stock_id)


@router.get("")
def stocks(
    _: ApiKeyDep,
    include_inactive: bool = Query(default=False),
    search: Optional[str] = Query(default=None),
    sector: Optional[str] = Query(default=None),
):
    return {
        "stocks": list_demo_stocks(search=search, sector=sector)
        if using_demo_market()
        else list_stocks(
            active_only=not include_inactive,
            include_inactive=include_inactive,
            search=search,
            sector=sector,
        )
    }


@router.get("/{stock_id}")
def stock_detail(stock_id: str, _: ApiKeyDep):
    row = _resolve_stock(stock_id)
    if not row:
        raise HTTPException(status_code=404, detail="Stock not found")
    return row


@router.get("/{stock_id}/snapshot")
def stock_snapshot(stock_id: str, _: ApiKeyDep, price_limit: int = Query(default=30, ge=1, le=120)):
    snap = build_stock_snapshot(stock_id, price_limit=price_limit)
    if not snap:
        raise HTTPException(status_code=404, detail="Stock not found")
    return snap


@router.get("/{stock_id}/prices")
def stock_prices(stock_id: str, _: ApiKeyDep, limit: int = Query(default=90, ge=1, le=500)):
    if not _resolve_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    rows = get_demo_prices(stock_id, limit=limit) if using_demo_market() else get_recent_prices(stock_id, limit=limit)
    return {"stock_id": stock_id, "count": len(rows), "prices": rows, "data_source": "yfinance_demo" if using_demo_market() else "supabase"}


@router.get("/{stock_id}/prices/export.csv")
def export_prices_csv(stock_id: str, _: ApiKeyDep, limit: int = Query(default=500, ge=1, le=2000)):
    if not _resolve_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    rows = get_demo_prices(stock_id, limit=limit) if using_demo_market() else get_recent_prices(stock_id, limit=limit)
    rows = list(reversed(rows))
    buffer = io.StringIO()
    writer = csv.DictWriter(
        buffer,
        fieldnames=["trade_date", "open", "high", "low", "close", "volume", "adj_close"],
    )
    writer.writeheader()
    writer.writerows(rows)
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{stock_id}_prices.csv"'},
    )


@router.get("/{stock_id}/news")
def stock_news(stock_id: str, _: ApiKeyDep, limit: int = Query(default=20, ge=1, le=100)):
    if not _resolve_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    if using_demo_market():
        return {"stock_id": stock_id, "count": 0, "news": [], "data_source": "yfinance_demo"}
    rows = get_recent_news(stock_id, limit=limit)
    return {"stock_id": stock_id, "count": len(rows), "news": rows}


@router.get("/{stock_id}/announcements")
def stock_announcements(stock_id: str, _: ApiKeyDep, limit: int = Query(default=20, ge=1, le=100)):
    if not _resolve_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    if using_demo_market():
        return {"stock_id": stock_id, "count": 0, "announcements": [], "data_source": "yfinance_demo"}
    rows = get_recent_announcements(stock_id, limit=limit)
    return {"stock_id": stock_id, "count": len(rows), "announcements": rows}
