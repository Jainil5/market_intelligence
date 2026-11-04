from __future__ import annotations

import os
from datetime import datetime, timezone

from .supabase_client import get_supabase


def check_supabase() -> dict:
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_SERVICE_ROLE_KEY"):
        return {"ok": False, "detail": "Supabase env vars not set"}
    try:
        get_supabase().table("stock_list").select("stock_id", count="exact").limit(1).execute()
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "detail": str(exc)}


def build_health_payload() -> dict:
    supabase = check_supabase()
    status = "ok" if supabase["ok"] else "degraded"
    return {
        "status": status,
        "service": "market-intelligence-data-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {
            "api_key_configured": bool(os.getenv("API_KEY")),
            "supabase": supabase,
        },
    }
