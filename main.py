from __future__ import annotations

import logging
import os
import time
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from data_manager.routes.admin import router as admin_router
from data_manager.routes.auth import router as auth_router
from data_manager.routes.dashboard import router as dashboard_router
from data_manager.routes.jobs import router as jobs_router
from data_manager.routes.metrics import router as metrics_router
from data_manager.routes.read import router as read_router
from data_manager.services.health import build_health_payload

load_dotenv()
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger(__name__)

API_VERSION = "1.4.0"


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - started) * 1000)
        response.headers["x-request-id"] = request_id
        logger.info(
            "%s %s %s %sms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response


def create_app() -> FastAPI:
    app = FastAPI(title="Market Intelligence Data API", version=API_VERSION)
    origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]
    if origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    app.add_middleware(RequestLogMiddleware)
    app.include_router(read_router)
    app.include_router(admin_router)
    app.include_router(auth_router)
    app.include_router(jobs_router)
    app.include_router(metrics_router)
    app.include_router(dashboard_router)
    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/health")
    def health():
        payload = build_health_payload(version=API_VERSION)
        payload["environment"] = os.getenv("APP_ENV", "development")
        return payload

    return app


app = create_app()
