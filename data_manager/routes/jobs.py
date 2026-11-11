from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from data_manager.deps import ApiKeyDep
from data_manager.services.alerts import notify_job_result
from data_manager.services.announcement_updater import update_announcements_for_all_stocks
from data_manager.services.job_runs import finish_job, start_job
from data_manager.services.news_updater import update_news_for_all_stocks
from data_manager.services.market_data import using_demo_market
from data_manager.services.local_price_updater import update_all_csv, update_one_csv
from data_manager.services.stock_updater import update_all_stocks, update_one_stock

router = APIRouter(tags=["jobs"])


class UpdateRequest(BaseModel):
    stock_id: Optional[str] = None
    include_fundamentals: bool = True
    include_news: bool = True
    include_announcements: bool = True


class PriceUpdateRequest(BaseModel):
    stock_id: Optional[str] = None
    include_fundamentals: bool = False
    backfill_from: Optional[date] = Field(default=None)


def _attach_job(job_name: str, result: dict) -> dict:
    handle = start_job(job_name)
    result["job"] = finish_job(handle, result)
    result["alert"] = notify_job_result(job_name, result)
    return result


@router.post("/update/stocks")
def update_stocks(_: ApiKeyDep, payload: UpdateRequest = UpdateRequest()):
    if using_demo_market():
        if payload.stock_id:
            result = update_one_csv(payload.stock_id)
        else:
            result = update_all_csv()
        result["news"] = {"status": "skipped", "reason": "demo_mode_no_database"}
        result["announcements"] = {"status": "skipped", "reason": "demo_mode_no_database"}
        return _attach_job("update_stocks", result)

    if payload.stock_id:
        result = update_one_stock(payload.stock_id, include_fundamentals=payload.include_fundamentals)
        if payload.include_news:
            result["news"] = update_news_for_all_stocks(stock_id=payload.stock_id)
        if payload.include_announcements:
            result["announcements"] = update_announcements_for_all_stocks(stock_id=payload.stock_id)
        return _attach_job("update_stocks", result)

    result = update_all_stocks(include_fundamentals=payload.include_fundamentals)
    if payload.include_news:
        result["news"] = update_news_for_all_stocks()
    if payload.include_announcements:
        result["announcements"] = update_announcements_for_all_stocks()
    return _attach_job("update_stocks", result)


@router.post("/update/prices")
def update_prices(_: ApiKeyDep, payload: PriceUpdateRequest = PriceUpdateRequest()):
    if using_demo_market():
        if payload.stock_id:
            result = update_one_csv(payload.stock_id, backfill_from=payload.backfill_from)
        else:
            result = update_all_csv(backfill_from=payload.backfill_from)
        return _attach_job("update_prices", result)

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
    return _attach_job("update_prices", result)


@router.post("/backfill/prices")
def backfill_prices(_: ApiKeyDep, payload: PriceUpdateRequest):
    if payload.backfill_from is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="backfill_from is required for backfill")
    return update_prices(payload=payload)


@router.post("/update/news")
def update_news(_: ApiKeyDep, stock_id: Optional[str] = None):
    result = update_news_for_all_stocks(stock_id=stock_id)
    return _attach_job("update_news", result)


@router.post("/update/announcements")
def update_announcements(_: ApiKeyDep, stock_id: Optional[str] = None):
    result = update_announcements_for_all_stocks(stock_id=stock_id)
    return _attach_job("update_announcements", result)
