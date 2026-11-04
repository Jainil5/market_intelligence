"""Backfill OHLCV from a start date into Supabase and local CSV."""
from __future__ import annotations

import argparse
from datetime import date

from dotenv import load_dotenv

from data_manager.services.stock_updater import update_all_stocks, update_one_stock

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill historical prices from yfinance")
    parser.add_argument("--from", dest="backfill_from", required=True, help="Start date YYYY-MM-DD")
    parser.add_argument("--stock-id", dest="stock_id", default=None, help="Single stock_id; omit for all active")
    parser.add_argument("--fundamentals", action="store_true", help="Refresh fundamentals snapshot too")
    args = parser.parse_args()
    start = date.fromisoformat(args.backfill_from)
    if args.stock_id:
        result = update_one_stock(
            args.stock_id,
            include_fundamentals=args.fundamentals,
            backfill_from=start,
        )
    else:
        result = update_all_stocks(
            include_fundamentals=args.fundamentals,
            backfill_from=start,
        )
    print(result)


if __name__ == "__main__":
    main()
