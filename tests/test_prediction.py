from prediction.predict import predict_stock


def test_predict_stock_insufficient_data():
    result = predict_stock(stock={"stock_id": "STK001"}, prices=[{"close": 1.0}] * 3)
    assert result["signal"] == "insufficient_data"


def test_predict_stock_sma_signal():
    prices = [{"trade_date": f"2024-01-{i:02d}", "close": float(i)} for i in range(1, 26)]
    result = predict_stock(stock={"stock_id": "STK001"}, prices=prices)
    assert result["signal"] in {"bullish", "bearish", "neutral"}
    assert result["model"] == "sma_crossover_example"
