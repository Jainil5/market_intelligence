from __future__ import annotations

from unittest.mock import patch

from data_manager.services.demo_market import build_demo_market_overview, list_demo_stocks


def test_nifty100_catalog_size():
    with patch.dict("os.environ", {"DEMO_CATALOG": "nifty100"}, clear=False):
        rows = list_demo_stocks()
    assert len(rows) == 100


def test_demo_overview_uses_batch():
    fake_quotes = {
        "RELIANCE.NS": [
            {"trade_date": "2025-01-01", "open": 1, "high": 1, "low": 1, "close": 100, "volume": 1},
            {"trade_date": "2025-01-02", "open": 1, "high": 1, "low": 1, "close": 102, "volume": 1},
        ]
    }
    with patch.dict("os.environ", {"DEMO_CATALOG": "demo"}, clear=False), patch(
        "data_manager.services.demo_market._batch_quotes",
        return_value={k: v for k, v in fake_quotes.items()},
    ), patch("data_manager.services.demo_market._load_catalog") as mock_cat:
        mock_cat.return_value = [
            {
                "stock_id": "DEMO_RELIANCE",
                "symbol": "RELIANCE",
                "yfinance_symbol": "RELIANCE.NS",
                "company_name": "Reliance",
                "exchange": "NSE",
            }
        ]
        overview = build_demo_market_overview(price_limit=2)
    assert overview[0]["close"] == 102
    assert overview[0]["day_change_pct"] == 2.0
