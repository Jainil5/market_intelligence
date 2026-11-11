from __future__ import annotations

import json
import logging
import os
import time
from datetime import date, timedelta
from pathlib import Path

from .market_summary import price_freshness, tradingview_symbol
from .price_fetcher import batch_recent_ohlcv, fetch_ohlcv
from .csv_store import has_local_csv, read_price_rows

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[1] / "data"
_DEMO_JSON = _DATA_DIR / "demo_stocks.json"
_NIFTY100_JSON = _DATA_DIR / "nifty100_stocks.json"
_PRICE_CACHE: dict[str, tuple[float, list[dict]]] = {}
_OVERVIEW_CACHE: tuple[float, list[dict]] | None = None
_CACHE_TTL_SEC = int(os.getenv("DEMO_PRICE_CACHE_SEC", "120"))
_OVERVIEW_PREDICTIONS = os.getenv("DEMO_OVERVIEW_PREDICTIONS", "false").lower() in {"1", "true", "yes"}


def demo_price_source() -> str:
    """Where demo mode reads OHLCV: auto | csv | yfinance."""
    raw = os.getenv("DEMO_PRICE_SOURCE", "auto").strip().lower()
    if raw in {"csv", "file", "local"}:
        return "csv"
    if raw in {"yfinance", "yahoo", "live"}:
        return "yfinance"
    return "auto"


def _use_csv_for_stock(stock_id: str) -> bool:
    mode = demo_price_source()
    if mode == "csv":
        return True
    if mode == "yfinance":
        return False
    return has_local_csv(stock_id)


def _data_source_label(stock_id: str) -> str:
    return "local_csv" if _use_csv_for_stock(stock_id) else "yfinance_demo"


def _catalog_file() -> Path:
    choice = os.getenv("DEMO_CATALOG", "nifty100").strip().lower()
    if choice in {"demo", "short", "sample"}:
        return _DEMO_JSON
    return _NIFTY100_JSON


def _load_catalog() -> list[dict]:
    path = _catalog_file()
    with path.open(encoding="utf-8") as fh:
        rows = json.load(fh)
    for row in rows:
        row.setdefault("active", True)
        row.setdefault("exchange", "NSE")
        row.setdefault("tv_symbol", tradingview_symbol(row))
    return rows


def catalog_label() -> str:
    path = _catalog_file()
    if path.name.startswith("nifty100"):
        return "nifty100"
    return "demo"


def list_demo_stocks(*, search: str | None = None, sector: str | None = None) -> list[dict]:
    rows = _load_catalog()
    if sector:
        rows = [r for r in rows if (r.get("sector") or "").lower() == sector.lower()]
    if search:
        needle = search.lower()
        rows = [
            r
            for r in rows
            if needle in (r.get("symbol") or "").lower()
            or needle in (r.get("company_name") or "").lower()
            or needle in (r.get("stock_id") or "").lower()
        ]
    return rows


def get_demo_stock(stock_id: str) -> dict | None:
    for row in _load_catalog():
        if row["stock_id"] == stock_id:
            return dict(row)
    return None


def _cached_prices(yfinance_symbol: str, lookback_days: int) -> list[dict]:
    now = time.time()
    cached = _PRICE_CACHE.get(yfinance_symbol)
    if cached and now - cached[0] < _CACHE_TTL_SEC:
        return cached[1]
    start = date.today() - timedelta(days=max(lookback_days, 10))
    rows = fetch_ohlcv(yfinance_symbol, start_date=start)
    _PRICE_CACHE[yfinance_symbol] = (now, rows)
    return rows


def get_demo_prices(stock_id: str, *, limit: int = 90) -> list[dict]:
    stock = get_demo_stock(stock_id)
    if not stock:
        return []
    if _use_csv_for_stock(stock_id):
        rows = read_price_rows(stock_id, limit=limit)
        if rows or demo_price_source() == "csv":
            return rows
    yf_sym = stock.get("yfinance_symbol") or stock.get("symbol")
    if not yf_sym:
        return []
    rows = _cached_prices(yf_sym, lookback_days=min(limit + 10, 400))
    if not rows:
        return []
    return list(reversed(rows[-limit:]))


def _day_change(prices_newest_first: list[dict]) -> float | None:
    if len(prices_newest_first) < 2:
        return None
    latest = prices_newest_first[0]
    previous = prices_newest_first[1]
    if not latest.get("close") or not previous.get("close"):
        return None
    prev = float(previous["close"])
    if prev == 0:
        return None
    return round(((float(latest["close"]) - prev) / prev) * 100, 2)


def _maybe_prediction(stock: dict, prices_asc: list[dict]) -> dict | None:
    hook = os.getenv("PREDICTION_FUNCTION", "").strip()
    if not hook or len(prices_asc) < 5:
        return None
    try:
        module_path, func_name = hook.split(":", 1)
        import importlib

        mod = importlib.import_module(module_path)
        fn = getattr(mod, func_name)
        return fn(stock=stock, prices=prices_asc)
    except Exception:
        logger.exception("Demo prediction hook failed for %s", stock.get("stock_id"))
        return None


def _batch_quotes(lookback_days: int = 10) -> dict[str, list[dict]]:
    catalog = _load_catalog()
    mode = demo_price_source()
    quotes: dict[str, list[dict]] = {}
    yf_symbols: list[str] = []
    limit = max(lookback_days + 3, 10)
    for stock in catalog:
        yf = stock.get("yfinance_symbol")
        if not yf:
            continue
        sid = stock["stock_id"]
        if mode == "csv" or (mode == "auto" and has_local_csv(sid)):
            newest = read_price_rows(sid, limit=limit)
            quotes[yf] = list(reversed(newest)) if newest else []
        elif mode != "csv":
            yf_symbols.append(yf)
    if yf_symbols and mode != "csv":
        quotes.update(batch_recent_ohlcv(yf_symbols, lookback_days=lookback_days))
    return quotes


def build_demo_market_overview(*, price_limit: int = 5) -> list[dict]:
    global _OVERVIEW_CACHE
    now = time.time()
    if _OVERVIEW_CACHE and now - _OVERVIEW_CACHE[0] < _CACHE_TTL_SEC:
        return _OVERVIEW_CACHE[1]

    catalog = _load_catalog()
    quotes = _batch_quotes(lookback_days=max(price_limit + 3, 10))
    overview: list[dict] = []
    for stock in catalog:
        yf = stock.get("yfinance_symbol")
        if not yf:
            continue
        asc = quotes.get(yf) or []
        prices_newest = list(reversed(asc[-max(price_limit, 2) :])) if asc else []
        latest = prices_newest[0] if prices_newest else None
        prediction = None
        if _OVERVIEW_PREDICTIONS and prices_newest:
            prediction = _maybe_prediction(stock, asc)
        overview.append(
            {
                "stock_id": stock["stock_id"],
                "symbol": stock.get("symbol"),
                "company_name": stock.get("company_name"),
                "exchange": stock.get("exchange"),
                "sector": stock.get("sector"),
                "yfinance_symbol": yf,
                "tv_symbol": stock.get("tv_symbol") or tradingview_symbol(stock),
                "latest_trade_date": (latest or {}).get("trade_date"),
                "close": (latest or {}).get("close"),
                "day_change_pct": _day_change(prices_newest),
                "prediction": prediction,
                "freshness": price_freshness((latest or {}).get("trade_date")),
                "data_source": _data_source_label(stock["stock_id"]),
                "catalog": catalog_label(),
            }
        )
    _OVERVIEW_CACHE = (now, overview)
    return overview


def build_demo_stock_snapshot(stock_id: str, *, price_limit: int = 30) -> dict | None:
    stock = get_demo_stock(stock_id)
    if not stock:
        return None
    prices = get_demo_prices(stock_id, limit=price_limit)
    latest = prices[0] if prices else None
    change_pct = _day_change(prices)
    prediction = _maybe_prediction(stock, list(reversed(prices))) if prices else None
    stock_row = dict(stock)
    if prediction:
        stock_row["latest_prediction"] = prediction
    return {
        "stock": stock_row,
        "latest_price": latest,
        "day_change_pct": change_pct,
        "recent_prices": prices,
        "data_source": _data_source_label(stock_id),
        "catalog": catalog_label(),
    }
