"""Fetch Yahoo OHLCV into local CSV files using the demo catalog (no Supabase)."""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta

from .csv_store import latest_trade_date, save_price_rows
from .demo_market import get_demo_stock, list_demo_stocks
from .price_fetcher import fetch_ohlcv

logger = logging.getLogger(__name__)


def _initial_lookback_days() -> int:
    try:
        return max(1, int(os.getenv("PRICE_INITIAL_LOOKBACK_DAYS", "365")))
    except ValueError:
        return 365


def _resolve_start_date(stock_id: str, backfill_from: date | None) -> date:
    if backfill_from is not None:
        return backfill_from
    latest = latest_trade_date(stock_id)
    if latest:
        return latest
    return date.today() - timedelta(days=_initial_lookback_days())


def update_one_csv(stock_id: str, *, backfill_from: date | None = None) -> dict:
    stock = get_demo_stock(stock_id)
    if not stock:
        return {"stock_id": stock_id, "status": "not_found"}
    symbol = stock.get("yfinance_symbol") or stock.get("symbol")
    if not symbol:
        return {"stock_id": stock_id, "status": "error", "error": "Missing yfinance_symbol"}
    try:
        start_date = _resolve_start_date(stock_id, backfill_from)
        rows = fetch_ohlcv(symbol, start_date=start_date)
        if not rows:
            return {"stock_id": stock_id, "status": "no_price_data", "yfinance_symbol": symbol}
        merged = save_price_rows(stock_id, rows)
        return {
            "stock_id": stock_id,
            "status": "updated",
            "rows_fetched": len(rows),
            "csv_rows_total": merged,
            "fetch_from": start_date.isoformat(),
            "latest_trade_date": rows[-1]["trade_date"],
            "storage": "local_csv",
        }
    except Exception as exc:
        logger.exception("CSV price update failed: %s", stock_id)
        return {"stock_id": stock_id, "status": "error", "error": str(exc)}


def update_all_csv(*, backfill_from: date | None = None) -> dict:
    results = [
        update_one_csv(stock["stock_id"], backfill_from=backfill_from)
        for stock in list_demo_stocks()
    ]
    return {
        "total": len(results),
        "updated": sum(x["status"] == "updated" for x in results),
        "failed": sum(x["status"] == "error" for x in results),
        "storage": "local_csv",
        "results": results,
    }
