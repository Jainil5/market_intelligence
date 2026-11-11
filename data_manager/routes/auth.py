from __future__ import annotations

import os

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from data_manager.deps import SESSION_COOKIE, require_api_key
from data_manager.security import verify_api_key

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    api_key: str = Field(min_length=8)


@router.post("/login")
def login(payload: LoginRequest, response: Response):
    verify_api_key(payload.api_key)
    secure = os.getenv("APP_ENV", "development").lower() == "production"
    max_age = int(os.getenv("SESSION_MAX_AGE_SEC", str(60 * 60 * 24 * 7)))
    response.set_cookie(
        SESSION_COOKIE,
        payload.api_key,
        httponly=True,
        samesite="lax",
        secure=secure,
        max_age=max_age,
        path="/",
    )
    return {"status": "ok", "session": "cookie", "max_age_sec": max_age}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "logged_out"}


@router.get("/session")
def session(_: str = Depends(require_api_key)):
    return {"authenticated": True}
