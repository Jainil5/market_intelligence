from __future__ import annotations

import os

from .health import check_supabase


def market_data_mode() -> str:
    """
    Return 'demo' (Yahoo Finance + bundled watchlist) or 'supabase'.
    DEMO_MARKET_DATA: true | false | auto (default auto = demo when Supabase is down).
    """
    raw = os.getenv("DEMO_MARKET_DATA", "auto").strip().lower()
    if raw in {"1", "true", "yes", "on", "demo", "yfinance"}:
        return "demo"
    if raw in {"0", "false", "no", "off", "supabase", "db"}:
        return "supabase"
    return "demo" if not check_supabase().get("ok") else "supabase"


def using_demo_market() -> bool:
    return market_data_mode() == "demo"
