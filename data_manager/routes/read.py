from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Header, HTTPException, Query

from data_manager.services.stock_catalog import (
    get_recent_news,
    get_recent_prices,
    get_stock,
    list_stocks,
)

router = APIRouter(prefix="/stocks", tags=["read"])


def _check_api_key(x_api_key: Optional[str]) -> None:
    import os

    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@router.get("")
def stocks(
    include_inactive: bool = Query(default=False),
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)
    return {"stocks": list_stocks(active_only=not include_inactive, include_inactive=include_inactive)}


@router.get("/{stock_id}")
def stock_detail(stock_id: str, x_api_key: Optional[str] = Header(default=None)):
    _check_api_key(x_api_key)
    row = get_stock(stock_id)
    if not row:
        raise HTTPException(status_code=404, detail="Stock not found")
    return row


@router.get("/{stock_id}/prices")
def stock_prices(
    stock_id: str,
    limit: int = Query(default=90, ge=1, le=500),
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)
    if not get_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    rows = get_recent_prices(stock_id, limit=limit)
    return {"stock_id": stock_id, "count": len(rows), "prices": rows}


@router.get("/{stock_id}/news")
def stock_news(
    stock_id: str,
    limit: int = Query(default=20, ge=1, le=100),
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)
    if not get_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    rows = get_recent_news(stock_id, limit=limit)
    return {"stock_id": stock_id, "count": len(rows), "news": rows}
