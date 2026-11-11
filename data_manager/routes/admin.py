from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from data_manager.deps import ApiKeyDep
from data_manager.services.stock_catalog import create_stock, delete_stock, get_stock, list_stocks, update_stock
from data_manager.services.stock_updater import refresh_prediction
from data_manager.services.storage_sync import sync_all_price_csvs, upload_price_csv
from data_manager.services.config import DATA_DIR

router = APIRouter(prefix="/admin", tags=["admin"])


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


@router.get("/stocks")
def admin_list_stocks(_: ApiKeyDep, include_inactive: bool = True):
    return {"stocks": list_stocks(active_only=False, include_inactive=include_inactive)}


@router.post("/stocks")
def admin_create_stock(payload: StockCreateRequest, _: ApiKeyDep):
    if get_stock(payload.stock_id):
        raise HTTPException(status_code=409, detail="stock_id already exists")
    try:
        row = create_stock(payload.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"status": "created", "stock": row}


@router.patch("/stocks/{stock_id}")
def admin_update_stock(stock_id: str, payload: StockUpdateRequest, _: ApiKeyDep):
    if not get_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    row = update_stock(stock_id, payload.model_dump(exclude_unset=True))
    return {"status": "updated", "stock": row}


@router.delete("/stocks/{stock_id}")
def admin_delete_stock(stock_id: str, _: ApiKeyDep):
    if not get_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    delete_stock(stock_id)
    return {"status": "deleted", "stock_id": stock_id}


@router.post("/stocks/{stock_id}/sync-storage")
def admin_sync_storage(stock_id: str, _: ApiKeyDep):
    if not get_stock(stock_id):
        raise HTTPException(status_code=404, detail="Stock not found")
    return upload_price_csv(stock_id, DATA_DIR / f"{stock_id}.csv")


@router.post("/stocks/{stock_id}/refresh-prediction")
def admin_refresh_prediction(stock_id: str, _: ApiKeyDep):
    return refresh_prediction(stock_id)


@router.post("/storage/sync-all")
def admin_sync_all_storage(_: ApiKeyDep):
    return sync_all_price_csvs()
