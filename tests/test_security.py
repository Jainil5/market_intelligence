import os

import pytest
from fastapi import HTTPException

from data_manager.security import enforce_rate_limit, verify_api_key


def test_verify_api_key_rejects_invalid():
    os.environ["API_KEY"] = "secret"
    with pytest.raises(HTTPException) as exc:
        verify_api_key("wrong")
    assert exc.value.status_code == 401


def test_rate_limit_blocks(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "2")
    enforce_rate_limit("k1")
    enforce_rate_limit("k1")
    with pytest.raises(HTTPException) as exc:
        enforce_rate_limit("k1")
    assert exc.value.status_code == 429
