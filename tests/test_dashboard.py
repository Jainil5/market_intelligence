import os
from unittest.mock import patch

from fastapi.testclient import TestClient

import main


def test_dashboard_requires_token():
    client = TestClient(main.app)
    response = client.get("/dashboard")
    assert response.status_code == 401


def test_root_redirects_app():
    client = TestClient(main.app)
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/app"


def test_dashboard_rejects_bad_token():
    client = TestClient(main.app)
    response = client.get("/dashboard", params={"access_token": "wrong"})
    assert response.status_code == 401


def test_spa_app_served():
    client = TestClient(main.app)
    response = client.get("/app")
    assert response.status_code == 200
    assert "Market Intelligence App" in response.text
