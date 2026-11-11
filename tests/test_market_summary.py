from __future__ import annotations

from datetime import date, timedelta

import pytest

from data_manager.services.market_summary import price_freshness, tradingview_symbol


def test_price_freshness_missing():
    assert price_freshness(None)["status"] == "missing"


def test_price_freshness_fresh():
    today = date.today().isoformat()
    assert price_freshness(today)["status"] == "fresh"


def test_price_freshness_stale():
    old = (date.today() - timedelta(days=10)).isoformat()
    assert price_freshness(old, stale_after_days=3)["status"] == "stale"


@pytest.mark.parametrize(
    "stock,expected",
    [
        ({"symbol": "RELIANCE", "yfinance_symbol": "RELIANCE.NS"}, "NSE:RELIANCE"),
        ({"symbol": "TCS", "exchange": "NSE"}, "NSE:TCS"),
        ({"symbol": "X", "yfinance_symbol": "X.BO", "bse_scrip_code": "500325"}, "BSE:500325"),
    ],
)
def test_tradingview_symbol(stock, expected):
    assert tradingview_symbol(stock) == expected
