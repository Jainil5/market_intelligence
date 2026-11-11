from __future__ import annotations

import csv

from data_manager.services import csv_store
from data_manager.services.demo_market import get_demo_prices


def test_read_price_rows_from_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICE_HISTORY_DIR", str(tmp_path))
    monkeypatch.setattr(csv_store, "DATA_DIR", tmp_path)
    path = tmp_path / "STK001.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["trade_date", "open", "high", "low", "close", "volume", "adj_close"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "trade_date": "2025-01-01",
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 100,
                "volume": 10,
                "adj_close": 100,
            }
        )
        writer.writerow(
            {
                "trade_date": "2025-01-02",
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 102,
                "volume": 10,
                "adj_close": 102,
            }
        )

    rows = csv_store.read_price_rows("STK001", limit=10)
    assert rows[0]["trade_date"] == "2025-01-02"
    assert rows[0]["close"] == 102


def test_demo_prices_prefer_csv(tmp_path, monkeypatch):
    monkeypatch.setenv("PRICE_HISTORY_DIR", str(tmp_path))
    monkeypatch.setenv("DEMO_CATALOG", "demo")
    monkeypatch.setenv("DEMO_PRICE_SOURCE", "csv")
    monkeypatch.setattr(csv_store, "DATA_DIR", tmp_path)
    path = tmp_path / "DEMO_RELIANCE.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["trade_date", "open", "high", "low", "close", "volume", "adj_close"],
        )
        writer.writeheader()
        writer.writerow(
            {
                "trade_date": "2025-01-02",
                "open": 1,
                "high": 2,
                "low": 1,
                "close": 55,
                "volume": 1,
                "adj_close": 55,
            }
        )

    rows = get_demo_prices("DEMO_RELIANCE", limit=5)
    assert rows[0]["close"] == 55
