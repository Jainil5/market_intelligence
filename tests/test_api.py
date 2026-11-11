from datetime import date
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

import main


def test_health_without_supabase():
    with patch("data_manager.services.health.check_supabase", return_value={"ok": False, "detail": "down"}):
        client = TestClient(main.app)
        response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["api_key_configured"] is True
    assert body["version"] == "1.4.0"


def test_update_prices_requires_api_key():
    client = TestClient(main.app)
    response = client.post("/update/prices", json={})
    assert response.status_code == 401


def test_backfill_requires_date():
    client = TestClient(main.app)
    response = client.post(
        "/backfill/prices",
        json={"stock_id": "STK001"},
        headers={"x-api-key": "test-secret-key"},
    )
    assert response.status_code == 422


def test_update_prices_with_backfill():
    fake_result = {
        "stock_id": "STK001",
        "status": "updated",
        "rows_upserted": 3,
        "fetch_from": "2024-01-01",
        "latest_trade_date": "2024-01-05",
        "fundamentals_updated": False,
        "prediction_updated": False,
    }
    with patch("data_manager.routes.jobs.using_demo_market", return_value=False), patch(
        "data_manager.routes.jobs.update_one_stock", return_value=fake_result
    ) as mock_update, patch(
        "data_manager.routes.jobs._attach_job",
        side_effect=lambda _name, result: result,
    ):
        client = TestClient(main.app)
        response = client.post(
            "/update/prices",
            json={"stock_id": "STK001", "backfill_from": "2024-01-01"},
            headers={"x-api-key": "test-secret-key"},
        )
    assert response.status_code == 200
    mock_update.assert_called_once_with(
        "STK001",
        include_fundamentals=False,
        backfill_from=date(2024, 1, 1),
    )


def test_news_providers_respect_env(monkeypatch):
    monkeypatch.setenv("NEWS_PROVIDERS", "custom")
    mock_sb = MagicMock()
    mock_sb.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [
        {"stock_id": "STK001", "symbol": "RELIANCE", "company_name": "Reliance", "active": True}
    ]
    custom_fetcher = MagicMock(return_value=[{"headline": "Custom", "source_url": "https://example.com/a"}])
    with patch("data_manager.services.news_updater.get_supabase", return_value=mock_sb), patch(
        "data_manager.services.news_updater._load_external_fetcher",
        return_value=custom_fetcher,
    ), patch("data_manager.services.news_updater.fetch_google_news") as mock_google:
        from data_manager.services.news_updater import update_news_for_all_stocks

        result = update_news_for_all_stocks(stock_id="STK001")
    mock_google.assert_not_called()
    custom_fetcher.assert_called_once_with("STK001")
    assert result["articles_submitted"] == 1
