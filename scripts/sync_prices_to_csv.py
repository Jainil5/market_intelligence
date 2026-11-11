#!/usr/bin/env python3
"""Download Yahoo OHLCV into local CSV files (demo catalog, no Supabase)."""
from __future__ import annotations

import argparse
from datetime import date

from dotenv import load_dotenv

from data_manager.services.local_price_updater import update_all_csv, update_one_csv

load_dotenv()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync demo catalog prices to local CSV files")
    parser.add_argument("--stock-id", dest="stock_id", default=None, help="Single stock_id; omit for full catalog")
    parser.add_argument("--from", dest="backfill_from", default=None, help="Start date YYYY-MM-DD")
    args = parser.parse_args()
    start = date.fromisoformat(args.backfill_from) if args.backfill_from else None
    if args.stock_id:
        result = update_one_csv(args.stock_id, backfill_from=start)
    else:
        result = update_all_csv(backfill_from=start)
    print(result)


if __name__ == "__main__":
    main()
