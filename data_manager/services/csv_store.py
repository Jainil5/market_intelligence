from __future__ import annotations

from pathlib import Path
import pandas as pd
from .config import DATA_DIR

COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "adj_close"]

def save_price_rows(stock_id: str, rows: list[dict]) -> int:
    """Merge rows by date and persist sorted OHLCV history in one CSV per stock."""
    if not rows: return 0
    path: Path = DATA_DIR / f"{stock_id}.csv"
    incoming = pd.DataFrame(rows, columns=COLUMNS)
    if path.exists():
        old = pd.read_csv(path)
        merged = pd.concat([old, incoming], ignore_index=True)
    else:
        merged = incoming
    merged["trade_date"] = pd.to_datetime(merged["trade_date"]).dt.strftime("%Y-%m-%d")
    merged = merged.drop_duplicates(subset=["trade_date"], keep="last").sort_values("trade_date")
    merged = merged[COLUMNS]
    merged.to_csv(path, index=False)
    try:
        from .storage_sync import upload_price_csv

        upload_price_csv(stock_id, path)
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Storage upload failed for %s", stock_id)
    return len(incoming)
