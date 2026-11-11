from __future__ import annotations

from .supabase_client import get_supabase


def platform_metrics() -> dict:
    from .market_data import using_demo_market

    if using_demo_market():
        from .csv_store import count_local_price_rows
        from .demo_market import demo_price_source, list_demo_stocks

        n = len(list_demo_stocks())
        return {
            "active_stocks": n,
            "price_rows": count_local_price_rows(),
            "news_rows": 0,
            "announcement_rows": 0,
            "mode": "local_csv",
            "price_source": demo_price_source(),
        }
    client = get_supabase()
    stocks = client.table("stock_list").select("stock_id", count="exact").eq("active", True).execute()
    prices = client.table("stock_prices").select("trade_date", count="exact").execute()
    news = client.table("news").select("news_id", count="exact").execute()
    announcements = client.table("announcements").select("announcement_id", count="exact").execute()
    return {
        "active_stocks": stocks.count or 0,
        "price_rows": prices.count or 0,
        "news_rows": news.count or 0,
        "announcement_rows": announcements.count or 0,
    }
