from __future__ import annotations

from typing import Annotated, Optional

from fastapi import Cookie, Depends, Header

from data_manager.security import enforce_rate_limit, verify_api_key

SESSION_COOKIE = "mi_api_key"


def resolve_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="x-api-key"),
    mi_api_key: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> str:
    key = x_api_key or mi_api_key
    enforce_rate_limit(key)
    verify_api_key(key)
    return key or ""


def require_api_key(key: str = Depends(resolve_api_key)) -> str:
    return key


ApiKeyDep = Annotated[str, Depends(require_api_key)]
