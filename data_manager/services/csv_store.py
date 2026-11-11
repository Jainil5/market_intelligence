from __future__ import annotations

from datetime import date
from pathlib import Path
import pandas as pd
from .config import DATA_DIR

COLUMNS = ["trade_date", "open", "high", "low", "close", "volume", "adj_close"]


def csv_path(stock_id: str) -> Path:
    return DATA_DIR / f"{stock_id}.csv"


def has_local_csv(stock_id: str) -> bool:
    return csv_path(stock_id).is_file()


def latest_trade_date(stock_id: str) -> date | None:
    path = csv_path(stock_id)
    if not path.is_file():
        return None
    df = pd.read_csv(path, usecols=["trade_date"])
    if df.empty:
        return None
    return date.fromisoformat(str(df["trade_date"].iloc[-1]))


def read_price_rows(stock_id: str, *, limit: int = 500) -> list[dict]:
    """Read OHLCV from local CSV; newest trade_date first."""
    path = csv_path(stock_id)
    if not path.is_file():
        return []
    limit = max(1, min(limit, 5000))
    df = pd.read_csv(path)
    if df.empty:
        return []
    for col in COLUMNS:
        if col not in df.columns:
            return []
    df = df.sort_values("trade_date", ascending=False).head(limit)
    rows: list[dict] = []
    for _, row in df.iterrows():
        rows.append(
            {
                "trade_date": str(row["trade_date"])[:10],
                "open": float(row["open"]) if pd.notna(row["open"]) else None,
                "high": float(row["high"]) if pd.notna(row["high"]) else None,
                "low": float(row["low"]) if pd.notna(row["low"]) else None,
                "close": float(row["close"]) if pd.notna(row["close"]) else None,
                "volume": float(row["volume"]) if pd.notna(row["volume"]) else None,
                "adj_close": float(row["adj_close"]) if pd.notna(row.get("adj_close")) else None,
            }
        )
    return rows


def count_local_price_rows() -> int:
    total = 0
    for path in DATA_DIR.glob("*.csv"):
        try:
            total += len(pd.read_csv(path))
        except (OSError, ValueError, pd.errors.EmptyDataError):
            continue
    return total


def save_price_rows(stock_id: str, rows: list[dict]) -> int:
    """Merge rows by date and persist sorted OHLCV history in one CSV per stock."""
    if not rows:
        return 0
    path = csv_path(stock_id)
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
    bucket = __import__("os").getenv("SUPABASE_STORAGE_BUCKET", "").strip()
    if bucket:
        try:
            from .storage_sync import upload_price_csv

            upload_price_csv(stock_id, path)
        except Exception:
            import logging

            logging.getLogger(__name__).exception("Storage upload failed for %s", stock_id)
    return len(incoming)
