from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from data_manager.services.stock_catalog import create_stock, get_stock, list_stocks, update_stock

router = APIRouter(prefix="/admin/stocks", tags=["admin"])


def _check_api_key(x_api_key: Optional[str]) -> None:
    import os

    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


class StockCreateRequest(BaseModel):
    stock_id: str = Field(min_length=1, max_length=32)
    symbol: str
    yfinance_symbol: str
    company_name: Optional[str] = None
    exchange: Literal["NSE", "BSE", "BOTH"] = "NSE"
    bse_scrip_code: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    active: bool = True


class StockUpdateRequest(BaseModel):
    symbol: Optional[str] = None
    yfinance_symbol: Optional[str] = None
    company_name: Optional[str] = None
    exchange: Optional[Literal["NSE", "BSE", "BOTH"]] = None
    bse_scrip_code: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    active: Optional[bool] = None


@router.get("")
def admin_list_stocks(
    include_inactive: bool = True,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)
    return {"stocks": list_stocks(active_only=False, include_inactive=include_inactive)}


@router.post("")
def admin_create_stock(payload: StockCreateRequest, x_api_key: Optional[str] = Header(default=None)):
    _check_api_key(x_api_key)
    if get_stock(payload.stock_id):
        raise HTTPException(status_code=409, detail="stock_id already exists")
    try:
        row = create_stock(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "created", "stock": row}


@router.patch("/{stock_id}")
def admin_update_stock(
    stock_id: str,
    payload: StockUpdateRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    _check_api_key(x_api_key)
    if not get_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    row = update_stock(stock_id, payload.model_dump(exclude_unset=True))
    return {"status": "updated", "stock": row}
