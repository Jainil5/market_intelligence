from __future__ import annotations

import logging
from datetime import date, timedelta
import pandas as pd
import yfinance as yf

from .retry_utils import retry_call

logger = logging.getLogger(__name__)

def fetch_ohlcv(yfinance_symbol: str, start_date: date | None = None) -> list[dict]:
    """Fetch daily OHLCV. Yahoo's end date is exclusive; use tomorrow to include today."""
    start = start_date or (date.today() - timedelta(days=10))
    end = date.today() + timedelta(days=1)

    def _download():
        return yf.download(
            yfinance_symbol,
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=False,
            multi_level_index=False,
            repair=True,
            timeout=20,
        )

    frame = retry_call(_download, label=f"yfinance.download({yfinance_symbol})")
    if frame is None or frame.empty:
        return []
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    rows=[]
    for idx, row in frame.iterrows():
        rows.append({
            "trade_date": pd.Timestamp(idx).date().isoformat(),
            "open": float(row["Open"]), "high": float(row["High"]),
            "low": float(row["Low"]), "close": float(row["Close"]),
            "volume": int(row["Volume"]) if pd.notna(row.get("Volume")) else None,
            "adj_close": float(row["Adj Close"]) if "Adj Close" in row and pd.notna(row["Adj Close"]) else None,
        })
    return rows

def fetch_fundamentals(yfinance_symbol: str) -> dict:
    """Return a compact, JSON-safe fundamentals snapshot from yfinance."""
    def _load_info():
        ticker = yf.Ticker(yfinance_symbol)
        return ticker.get_info() or {}

    info = retry_call(_load_info, label=f"yfinance.info({yfinance_symbol})")
    def clean(v):
        if v is None: return None
        try:
            if pd.isna(v): return None
        except (TypeError, ValueError): pass
        if hasattr(v, "item"): v=v.item()
        if isinstance(v, (str, int, float, bool)): return v
        return str(v)
    keys = [
        "marketCap", "trailingPE", "forwardPE", "priceToBook", "enterpriseValue",
        "totalRevenue", "revenuePerShare", "grossProfits", "ebitda", "netIncomeToCommon",
        "profitMargins", "operatingMargins", "returnOnEquity", "returnOnAssets",
        "debtToEquity", "currentRatio", "quickRatio", "trailingEps", "bookValue",
        "dividendYield", "payoutRatio", "currency", "financialCurrency",
    ]
    snapshot={k: clean(info.get(k)) for k in keys if info.get(k) is not None}
    snapshot["company_name"] = clean(info.get("longName") or info.get("shortName"))
    snapshot["updated_at"] = pd.Timestamp.utcnow().isoformat()
    return snapshot
