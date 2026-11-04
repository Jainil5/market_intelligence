from __future__ import annotations

import logging
import os
from datetime import date
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from data_manager.routes.admin import router as admin_router
from data_manager.routes.read import router as read_router
from data_manager.services.alerts import notify_job_result
from data_manager.services.stock_updater import update_all_stocks, update_one_stock
from data_manager.services.news_updater import update_news_for_all_stocks
from data_manager.services.announcement_updater import update_announcements_for_all_stocks
from data_manager.services.health import build_health_payload

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)
app = FastAPI(title="Market Intelligence Data API", version="1.2.0")
app.include_router(read_router)
app.include_router(admin_router)


class UpdateRequest(BaseModel):
    stock_id: Optional[str] = None
    include_fundamentals: bool = True
    include_news: bool = True
    include_announcements: bool = True


class PriceUpdateRequest(BaseModel):
    stock_id: Optional[str] = None
    include_fundamentals: bool = False
    backfill_from: Optional[date] = Field(
        default=None,
        description="Fetch OHLCV from this date (inclusive). Omit for incremental updates.",
    )


def check_api_key(x_api_key: Optional[str]) -> None:
    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY is not configured")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@app.get("/health")
def health():
    payload = build_health_payload()
    payload["environment"] = os.getenv("APP_ENV", "development")
    return payload


@app.post("/update/stocks")
def update_stocks(payload: UpdateRequest = UpdateRequest(), x_api_key: Optional[str] = Header(default=None)):
    check_api_key(x_api_key)
    if payload.stock_id:
        result = update_one_stock(payload.stock_id, include_fundamentals=payload.include_fundamentals)
        if payload.include_news:
            result["news"] = update_news_for_all_stocks(stock_id=payload.stock_id)
        if payload.include_announcements:
            result["announcements"] = update_announcements_for_all_stocks(stock_id=payload.stock_id)
        alert = notify_job_result("update_stocks", result)
        result["alert"] = alert
        return result

    result = update_all_stocks(include_fundamentals=payload.include_fundamentals)
    if payload.include_news:
        result["news"] = update_news_for_all_stocks()
    if payload.include_announcements:
        result["announcements"] = update_announcements_for_all_stocks()
    alert = notify_job_result("update_stocks", result)
    result["alert"] = alert
    return result


@app.post("/update/prices")
def update_prices(
    payload: PriceUpdateRequest = PriceUpdateRequest(),
    x_api_key: Optional[str] = Header(default=None),
):
    check_api_key(x_api_key)
    if payload.stock_id:
        result = update_one_stock(
            payload.stock_id,
            include_fundamentals=payload.include_fundamentals,
            backfill_from=payload.backfill_from,
        )
    else:
        result = update_all_stocks(
            include_fundamentals=payload.include_fundamentals,
            backfill_from=payload.backfill_from,
        )
    result["alert"] = notify_job_result("update_prices", result)
    return result


@app.post("/backfill/prices")
def backfill_prices(
    payload: PriceUpdateRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    check_api_key(x_api_key)
    if payload.backfill_from is None:
        raise HTTPException(status_code=422, detail="backfill_from is required for backfill")
    return update_prices(payload=payload, x_api_key=x_api_key)


@app.post("/update/news")
def update_news(stock_id: Optional[str] = None, x_api_key: Optional[str] = Header(default=None)):
    check_api_key(x_api_key)
    result = update_news_for_all_stocks(stock_id=stock_id)
    result["alert"] = notify_job_result("update_news", result)
    return result


@app.post("/update/announcements")
def update_announcements(stock_id: Optional[str] = None, x_api_key: Optional[str] = Header(default=None)):
    check_api_key(x_api_key)
    result = update_announcements_for_all_stocks(stock_id=stock_id)
    result["alert"] = notify_job_result("update_announcements", result)
    return result
