from __future__ import annotations

import importlib
import logging
import os
from datetime import date, timedelta
from .supabase_client import get_supabase
from .price_fetcher import fetch_ohlcv
from .csv_store import save_price_rows
from .fundamentals_updater import update_fundamentals

logger = logging.getLogger(__name__)

def _initial_lookback_days() -> int:
    try:
        return max(1, int(os.getenv("PRICE_INITIAL_LOOKBACK_DAYS", "365")))
    except ValueError:
        return 365

def _resolve_start_date(stock_id: str, backfill_from: date | None) -> date:
    if backfill_from is not None:
        return backfill_from
    latest = (
        get_supabase().table("stock_prices")
        .select("trade_date")
        .eq("stock_id", stock_id)
        .order("trade_date", desc=True)
        .limit(1)
        .execute()
        .data
        or []
    )
    if latest:
        return date.fromisoformat(latest[0]["trade_date"])
    return date.today() - timedelta(days=_initial_lookback_days())

def _load_prediction_function():
    path = __import__("os").getenv("PREDICTION_FUNCTION", "").strip()
    if not path: return None
    module_name, function_name = path.split(":", 1)
    return getattr(importlib.import_module(module_name), function_name)

def _get_stocks(stock_id: str | None = None) -> list[dict]:
    query = get_supabase().table("stock_list").select("stock_id,symbol,company_name,exchange,yfinance_symbol,active")
    if stock_id: query = query.eq("stock_id", stock_id)
    else: query = query.eq("active", True)
    return query.execute().data or []

def _run_prediction(stock: dict, price_rows: list[dict]):
    fn = _load_prediction_function()
    if fn is None or not price_rows: return None
    # Contract: your function receives stock metadata and fetched price rows. Adapt here if its signature differs.
    prediction = fn(stock=stock, prices=price_rows)
    if prediction is not None:
        get_supabase().table("stock_list").update({"latest_prediction": prediction}).eq("stock_id", stock["stock_id"]).execute()
    return prediction

def update_one_stock(
    stock_id: str,
    include_fundamentals: bool = True,
    backfill_from: date | None = None,
) -> dict:
    stocks = _get_stocks(stock_id)
    if not stocks: return {"stock_id": stock_id, "status": "not_found"}
    stock = stocks[0]
    symbol = stock.get("yfinance_symbol") or stock.get("symbol")
    if not symbol: return {"stock_id": stock_id, "status": "error", "error": "Missing yfinance_symbol"}
    try:
        # Incremental from latest stored trade_date (inclusive), or backfill_from / initial window.
        start_date = _resolve_start_date(stock_id, backfill_from)
        rows = fetch_ohlcv(symbol, start_date=start_date)
        if not rows:
            return {"stock_id": stock_id, "status": "no_price_data", "yfinance_symbol": symbol}
        db_rows = [{"stock_id": stock_id, **r} for r in rows]
        get_supabase().table("stock_prices").upsert(db_rows, on_conflict="stock_id,trade_date").execute()
        save_price_rows(stock_id, rows)
        prediction = _run_prediction(stock, rows)
        fundamentals_updated = False
        if include_fundamentals:
            try: fundamentals_updated = update_fundamentals(stock)
            except Exception: logger.exception("Fundamentals update failed for %s", stock_id)
        return {
            "stock_id": stock_id,
            "status": "updated",
            "rows_upserted": len(rows),
            "fetch_from": start_date.isoformat(),
            "latest_trade_date": rows[-1]["trade_date"],
            "fundamentals_updated": fundamentals_updated,
            "prediction_updated": prediction is not None,
        }
    except Exception as exc:
        logger.exception("Stock update failed: %s", stock_id)
        return {"stock_id": stock_id, "status": "error", "error": str(exc)}

def update_all_stocks(
    include_fundamentals: bool = True,
    backfill_from: date | None = None,
) -> dict:
    stocks = _get_stocks()
    results=[]
    for stock in stocks:
        results.append(
            update_one_stock(
                stock["stock_id"],
                include_fundamentals=include_fundamentals,
                backfill_from=backfill_from,
            )
        )
    return {"total": len(results), "updated": sum(x["status"] == "updated" for x in results), "failed": sum(x["status"] == "error" for x in results), "results": results}
