from __future__ import annotations

import pytest

from data_manager.services import market_data


def test_market_data_mode_forced_demo(monkeypatch):
    monkeypatch.setenv("DEMO_MARKET_DATA", "true")
    assert market_data.market_data_mode() == "demo"


def test_market_data_mode_forced_supabase(monkeypatch):
    monkeypatch.setenv("DEMO_MARKET_DATA", "supabase")
    assert market_data.market_data_mode() == "supabase"
