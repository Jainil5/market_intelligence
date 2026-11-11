#!/usr/bin/env python3
"""Refresh Nifty 100 catalog JSON from NSE CSV (optional network)."""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data_manager" / "data" / "ind_nifty100list.csv"
OUT_PATH = ROOT / "data_manager" / "data" / "nifty100_stocks.json"
CSV_URL = "https://nsearchives.nseindia.com/content/indices/ind_nifty100list.csv"


def download_csv() -> None:
    import urllib.request

    req = urllib.request.Request(CSV_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        CSV_PATH.write_bytes(resp.read())


def build_catalog() -> list[dict]:
    if not CSV_PATH.exists():
        download_csv()
    rows: list[dict] = []
    with CSV_PATH.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for line in reader:
            symbol = (line.get("Symbol") or "").strip()
            if not symbol:
                continue
            company = (line.get("Company Name") or symbol).strip()
            sector = (line.get("Industry") or "").strip()
            rows.append(
                {
                    "stock_id": f"N100_{symbol}",
                    "symbol": symbol,
                    "yfinance_symbol": f"{symbol}.NS",
                    "company_name": company,
                    "exchange": "NSE",
                    "sector": sector,
                }
            )
    return rows


def main() -> int:
    catalog = build_catalog()
    if len(catalog) < 90:
        print(f"Expected ~100 rows, got {len(catalog)}", file=sys.stderr)
        return 1
    OUT_PATH.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {len(catalog)} stocks to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
