from __future__ import annotations

import json
import os

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from data_manager.security import verify_api_key
from data_manager.services.market_summary import build_market_overview
from data_manager.services.platform_metrics import platform_metrics
from data_manager.deps import SESSION_COOKIE

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory="templates")
APP_INDEX = os.path.join(os.path.dirname(__file__), "..", "..", "static", "app", "index.html")


def _resolve_token(request: Request, access_token: str | None) -> str:
    key = access_token or request.cookies.get(SESSION_COOKIE)
    if not key:
        raise HTTPException(status_code=401, detail="Login required")
    verify_api_key(key)
    return key


@router.get("/")
def root():
    return RedirectResponse(url="/app", status_code=302)


@router.get("/dashboard")
def dashboard(
    request: Request,
    access_token: str | None = Query(default=None, description="Optional; prefer POST /auth/login cookie"),
):
    token = _resolve_token(request, access_token)
    overview = build_market_overview(price_limit=10)
    initial = overview[0] if overview else None
    dashboard_config = json.dumps(
        {
            "accessToken": token,
            "initialStockId": initial["stock_id"] if initial else None,
            "initialTvSymbol": initial["tv_symbol"] if initial else "NSE:NIFTY",
            "watchlist": overview,
        }
    )
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
            "overview": overview,
            "metrics": platform_metrics(),
            "environment": os.getenv("APP_ENV", "development"),
            "initial_stock_id": initial["stock_id"] if initial else None,
            "dashboard_config": dashboard_config,
        },
    )


@router.get("/app")
def spa_app():
    path = os.path.abspath(APP_INDEX)
    if not os.path.isfile(path):
        raise HTTPException(status_code=503, detail="SPA missing")
    return FileResponse(path)
