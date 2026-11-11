from __future__ import annotations

import os
from datetime import datetime, timezone

from .job_runs import recent_job_runs
from .platform_metrics import platform_metrics
from .supabase_client import get_supabase

_APP_START = datetime.now(timezone.utc)


def check_supabase() -> dict:
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        return {"ok": False, "detail": "Supabase env vars not set"}
    try:
        get_supabase().table("stock_list").select("stock_id", count="exact").limit(1).execute()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def _latest_job_summary() -> dict | None:
    try:
        rows = recent_job_runs(limit=5)
    except Exception:
        return None
    if not rows:
        return None
    latest = rows[0]
    return {
        "job_name": latest.get("job_name"),
        "status": latest.get("status"),
        "started_at": latest.get("started_at"),
        "duration_ms": latest.get("duration_ms"),
    }


def _demo_catalog_health() -> dict | None:
    from .market_data import using_demo_market

    if not using_demo_market():
        return None
    from .demo_market import catalog_label, demo_price_source, list_demo_stocks

    return {
        "name": catalog_label(),
        "symbols": len(list_demo_stocks()),
        "price_source": demo_price_source(),
    }


def build_health_payload(*, version: str = "1.4.0") -> dict:
    supabase = check_supabase()
    status = "ok" if supabase["ok"] else "degraded"
    uptime_sec = int((datetime.now(timezone.utc) - _APP_START).total_seconds())
    latest_job = _latest_job_summary()
    from .market_data import market_data_mode

    return {
        "status": status,
        "service": "market-intelligence-data-api",
        "version": version,
        "uptime_seconds": uptime_sec,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "latest_job": latest_job,
        "market_data": market_data_mode(),
        "demo_catalog": _demo_catalog_health(),
        "checks": {
            "api_key_configured": bool(os.getenv("API_KEY")),
            "supabase": supabase,
            "storage_bucket_configured": bool(os.getenv("SUPABASE_STORAGE_BUCKET")),
            "prediction_hook": bool(os.getenv("PREDICTION_FUNCTION")),
        },
    }


def build_metrics_payload() -> dict:
    return {"metrics": platform_metrics(), "timestamp": datetime.now(timezone.utc).isoformat()}
