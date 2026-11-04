import logging
from .price_fetcher import fetch_fundamentals
from .supabase_client import get_supabase

logger = logging.getLogger(__name__)

def update_fundamentals(stock: dict) -> bool:
    symbol = stock.get("yfinance_symbol") or stock.get("symbol")
    if not symbol: return False
    data = fetch_fundamentals(symbol)
    get_supabase().table("stock_list").update({"fundamentals": data}).eq("stock_id", stock["stock_id"]).execute()
    return True
