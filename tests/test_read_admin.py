from unittest.mock import patch

from fastapi.testclient import TestClient

import main


def test_list_stocks_read_api(monkeypatch):
    monkeypatch.setenv("DEMO_MARKET_DATA", "supabase")
    fake = [{"stock_id": "STK001", "symbol": "RELIANCE", "active": True}]
    with patch("data_manager.routes.read.list_stocks", return_value=fake):
        client = TestClient(main.app)
        response = client.get("/stocks", headers={"x-api-key": "test-secret-key"})
    assert response.status_code == 200
    assert response.json()["stocks"][0]["stock_id"] == "STK001"


def test_admin_create_stock():
    with patch("data_manager.routes.admin.get_stock", side_effect=[None, {"stock_id": "STK003"}]), patch(
        "data_manager.routes.admin.create_stock",
        return_value={"stock_id": "STK003"},
    ):
        client = TestClient(main.app)
        response = client.post(
            "/admin/stocks",
            headers={"x-api-key": "test-secret-key"},
            json={
                "stock_id": "STK003",
                "symbol": "INFY",
                "yfinance_symbol": "INFY.NS",
                "company_name": "Infosys",
            },
        )
    assert response.status_code == 200
    assert response.json()["status"] == "created"


def test_market_overview_route():
    with patch("data_manager.routes.read.build_market_overview", return_value=[{"stock_id": "STK001"}]):
        client = TestClient(main.app)
        response = client.get("/stocks/overview/market", headers={"x-api-key": "test-secret-key"})
    assert response.status_code == 200
    assert response.json()["stocks"][0]["stock_id"] == "STK001"
