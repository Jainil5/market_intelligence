from __future__ import annotations

import os
from datetime import date

from .stock_catalog import get_recent_prices, get_stock, list_stocks

_DEFAULT_STALE_DAYS = 3


def price_freshness(trade_date: str | None, *, stale_after_days: int | None = None) -> dict:
    """Classify how current stored prices are (calendar days since last bar)."""
    limit = stale_after_days if stale_after_days is not None else int(os.getenv("PRICE_STALE_DAYS", _DEFAULT_STALE_DAYS))
    if not trade_date:
        return {"status": "missing", "days_old": None, "label": "No prices"}
    try:
        last = date.fromisoformat(str(trade_date)[:10])
    except ValueError:
        return {"status": "unknown", "days_old": None, "label": str(trade_date)}
    days_old = (date.today() - last).days
    if days_old <= 1:
        return {"status": "fresh", "days_old": days_old, "label": f"As of {last.isoformat()}"}
    if days_old <= limit:
        return {"status": "aging", "days_old": days_old, "label": f"{days_old}d old"}
    return {"status": "stale", "days_old": days_old, "label": f"Stale · {days_old}d"}


def tradingview_symbol(stock: dict) -> str:
    """Map catalog row to a TradingView symbol (e.g. NSE:RELIANCE)."""
    symbol = (stock.get("symbol") or "").strip()
    yf = (stock.get("yfinance_symbol") or "").strip()
    exchange = (stock.get("exchange") or "NSE").upper()
    if yf.upper().endswith(".NS") and symbol:
        return f"NSE:{symbol}"
    if yf.upper().endswith(".BO"):
        bse = stock.get("bse_scrip_code")
        if bse:
            return f"BSE:{bse}"
        if symbol:
            return f"BSE:{symbol}"
    if exchange == "BSE" and stock.get("bse_scrip_code"):
        return f"BSE:{stock['bse_scrip_code']}"
    if exchange == "NSE" and symbol:
        return f"NSE:{symbol}"
    return symbol or yf or "NSE:NIFTY"


def build_stock_snapshot(stock_id: str, price_limit: int = 30) -> dict | None:
    from .market_data import using_demo_market

    if using_demo_market():
        from .demo_market import build_demo_stock_snapshot

        return build_demo_stock_snapshot(stock_id, price_limit=price_limit)
    stock = get_stock(stock_id)
    if not stock:
        return None
    prices = get_recent_prices(stock_id, limit=price_limit)
    latest = prices[0] if prices else None
    previous = prices[1] if len(prices) > 1 else None
    change_pct = None
    if latest and previous and previous.get("close"):
        change_pct = round(
            ((float(latest["close"]) - float(previous["close"])) / float(previous["close"])) * 100,
            2,
        )
    return {
        "stock": stock,
        "latest_price": latest,
        "day_change_pct": change_pct,
        "recent_prices": prices,
    }


def build_market_overview(*, price_limit: int = 5) -> list[dict]:
    from .market_data import using_demo_market

    if using_demo_market():
        from .demo_market import build_demo_market_overview

        return build_demo_market_overview(price_limit=price_limit)
    overview = []
    for stock in list_stocks(active_only=True):
        snap = build_stock_snapshot(stock["stock_id"], price_limit=price_limit)
        if snap:
            overview.append(
                {
                    "stock_id": stock["stock_id"],
                    "symbol": stock.get("symbol"),
                    "company_name": stock.get("company_name"),
                    "exchange": stock.get("exchange"),
                    "yfinance_symbol": stock.get("yfinance_symbol"),
                    "tv_symbol": tradingview_symbol(stock),
                    "sector": stock.get("sector"),
                    "latest_trade_date": (snap.get("latest_price") or {}).get("trade_date"),
                    "close": (snap.get("latest_price") or {}).get("close"),
                    "day_change_pct": snap.get("day_change_pct"),
                    "prediction": stock.get("latest_prediction"),
                    "freshness": price_freshness((snap.get("latest_price") or {}).get("trade_date")),
                }
            )
    return overview
