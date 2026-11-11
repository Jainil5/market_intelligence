from __future__ import annotations

from fastapi import APIRouter, Query

from data_manager.deps import ApiKeyDep
from data_manager.services.health import build_metrics_payload
from data_manager.services.job_runs import recent_job_runs

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def metrics(_: ApiKeyDep):
    return build_metrics_payload()


@router.get("/jobs/recent")
def jobs_recent(_: ApiKeyDep, limit: int = Query(default=20, ge=1, le=100)):
    return {"jobs": recent_job_runs(limit=limit)}
