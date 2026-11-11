from __future__ import annotations

import hmac
import os
import time
from collections import defaultdict
from threading import Lock
from typing import Optional

from fastapi import Header, HTTPException

_RATE_LOCK = Lock()
_RATE_BUCKETS: dict[str, list[float]] = defaultdict(list)


def verify_api_key(x_api_key: Optional[str]) -> None:
    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(status_code=503, detail="API_KEY is not configured")
    if not x_api_key or not hmac.compare_digest(x_api_key, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


def _rate_limit_per_minute() -> int:
    try:
        return max(0, int(os.getenv("RATE_LIMIT_PER_MINUTE", "120")))
    except ValueError:
        return 120


def enforce_rate_limit(x_api_key: Optional[str] = Header(default=None)) -> None:
    limit = _rate_limit_per_minute()
    if limit <= 0:
        return
    key = x_api_key or "anonymous"
    now = time.time()
    window_start = now - 60.0
    with _RATE_LOCK:
        hits = [t for t in _RATE_BUCKETS[key] if t >= window_start]
        if len(hits) >= limit:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        hits.append(now)
        _RATE_BUCKETS[key] = hits
