"""Example prediction hook. Set PREDICTION_FUNCTION=prediction.predict:predict_stock in .env."""
from __future__ import annotations

from typing import Any


def predict_stock(*, stock: dict, prices: list[dict]) -> dict[str, Any]:
    closes = [float(row["close"]) for row in prices if row.get("close") is not None]
    if len(closes) < 5:
        return {
            "model": "sma_crossover_example",
            "signal": "insufficient_data",
            "stock_id": stock.get("stock_id"),
            "bars": len(closes),
        }
    sma5 = sum(closes[-5:]) / 5
    sma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else sma5
    signal = "bullish" if sma5 > sma20 else "bearish" if sma5 < sma20 else "neutral"
    return {
        "model": "sma_crossover_example",
        "signal": signal,
        "stock_id": stock.get("stock_id"),
        "as_of": prices[-1].get("trade_date"),
        "sma5": round(sma5, 4),
        "sma20": round(sma20, 4),
        "last_close": closes[-1],
    }
