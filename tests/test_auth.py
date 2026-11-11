from unittest.mock import patch

import os

from fastapi.testclient import TestClient

import main


def test_login_sets_cookie():
    os.environ["API_KEY"] = "test-secret-key"
    client = TestClient(main.app)
    response = client.post("/auth/login", json={"api_key": "test-secret-key"})
    assert response.status_code == 200
    assert response.cookies.get("mi_api_key") == "test-secret-key"


def test_session_with_cookie():
    os.environ["API_KEY"] = "test-secret-key"
    client = TestClient(main.app)
    client.post("/auth/login", json={"api_key": "test-secret-key"})
    response = client.get("/auth/session")
    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def test_metrics_with_cookie_only():
    os.environ["API_KEY"] = "test-secret-key"
    fake = {"active_stocks": 1, "price_rows": 2, "news_rows": 3, "announcement_rows": 4}
    with patch("data_manager.services.health.platform_metrics", return_value=fake):
        client = TestClient(main.app)
        client.post("/auth/login", json={"api_key": "test-secret-key"})
        response = client.get("/metrics")
    assert response.status_code == 200
    assert response.json()["metrics"]["active_stocks"] == 1
