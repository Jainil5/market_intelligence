from __future__ import annotations

import logging
import os
from pathlib import Path

from .config import DATA_DIR
from .supabase_client import get_supabase

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return bool(os.getenv("SUPABASE_STORAGE_BUCKET", "").strip())


def upload_price_csv(stock_id: str, csv_path: Path | None = None) -> dict:
    """Upload merged OHLCV CSV to Supabase Storage (upsert)."""
    if not _enabled():
        return {"uploaded": False, "reason": "SUPABASE_STORAGE_BUCKET not set"}
    path = csv_path or (DATA_DIR / f"{stock_id}.csv")
    if not path.exists():
        return {"uploaded": False, "reason": "csv_missing", "path": str(path)}

    bucket = os.getenv("SUPABASE_STORAGE_BUCKET", "").strip()
    prefix = os.getenv("SUPABASE_STORAGE_PREFIX", "historical_prices").strip().strip("/")
    object_path = f"{prefix}/{stock_id}.csv"
    data = path.read_bytes()
    client = get_supabase()
    client.storage.from_(bucket).upload(
        object_path,
        data,
        file_options={"content-type": "text/csv", "upsert": "true"},
    )
    return {"uploaded": True, "bucket": bucket, "path": object_path, "bytes": len(data)}
