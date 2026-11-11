from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from typing import Any

from .supabase_client import get_supabase

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    return os.getenv("JOB_RUNS_ENABLED", "true").lower() in {"1", "true", "yes", "on"}


def start_job(job_name: str) -> dict[str, Any]:
    return {"job_name": job_name, "started_at": time.perf_counter(), "started_iso": datetime.now(timezone.utc).isoformat()}


def finish_job(handle: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    duration_ms = int((time.perf_counter() - handle["started_at"]) * 1000)
    failed = int(result.get("failed") or 0)
    status = "failed" if failed > 0 or result.get("status") == "error" else "ok"
    record = {
        "job_name": handle["job_name"],
        "status": status,
        "summary": result,
        "duration_ms": duration_ms,
        "finished_at": datetime.now(timezone.utc).isoformat(),
    }
    if not _enabled():
        return record
    try:
        get_supabase().table("job_runs").insert(
            {
                "job_name": handle["job_name"],
                "status": status,
                "summary": result,
                "duration_ms": duration_ms,
            }
        ).execute()
    except Exception:
        logger.exception("Failed to persist job_run for %s", handle["job_name"])
    return record


def recent_job_runs(limit: int = 20) -> list[dict]:
    limit = max(1, min(limit, 100))
    try:
        return (
            get_supabase()
            .table("job_runs")
            .select("job_id,job_name,status,duration_ms,started_at,finished_at")
            .order("started_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
    except Exception:
        logger.exception("job_runs table unavailable")
        return []
