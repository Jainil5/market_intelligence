from __future__ import annotations

import logging
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from .retry_utils import retry_call

logger = logging.getLogger(__name__)


def _frame_to_rows(frame: pd.DataFrame) -> list[dict]:
    frame = frame.dropna(subset=["Close"])
    frame = frame.dropna(subset=["Open", "High", "Low", "Close"])
    rows: list[dict] = []
    for idx, row in frame.iterrows():
        rows.append(
            {
                "trade_date": pd.Timestamp(idx).date().isoformat(),
                "open": float(row["Open"]),
                "high": float(row["High"]),
                "low": float(row["Low"]),
                "close": float(row["Close"]),
                "volume": int(row["Volume"]) if pd.notna(row.get("Volume")) else None,
                "adj_close": float(row["Adj Close"]) if "Adj Close" in row and pd.notna(row["Adj Close"]) else None,
            }
        )
    return rows


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
            repair=False,
            timeout=20,
        )

    frame = retry_call(_download, label=f"yfinance.download({yfinance_symbol})")
    if frame is None or frame.empty:
        return []
    if isinstance(frame.columns, pd.MultiIndex):
        frame = frame.droplevel(0, axis=1) if frame.columns.nlevels > 1 else frame
    return _frame_to_rows(frame)


def batch_recent_ohlcv(yfinance_symbols: list[str], *, lookback_days: int = 10) -> dict[str, list[dict]]:
    """
    Fetch recent daily bars for many tickers in one Yahoo request.
    Returns map yfinance_symbol -> ascending date rows.
    """
    symbols = [s for s in dict.fromkeys(yfinance_symbols) if s]
    if not symbols:
        return {}
    start = date.today() - timedelta(days=max(lookback_days, 5))
    end = date.today() + timedelta(days=1)

    def _download():
        return yf.download(
            symbols if len(symbols) > 1 else symbols[0],
            start=start.isoformat(),
            end=end.isoformat(),
            interval="1d",
            auto_adjust=False,
            actions=False,
            progress=False,
            threads=True,
            group_by="ticker",
            repair=False,
            timeout=60,
        )

    frame = retry_call(_download, label=f"yfinance.batch({len(symbols)})")
    if frame is None or frame.empty:
        return {}

    out: dict[str, list[dict]] = {}
    if len(symbols) == 1:
        out[symbols[0]] = _frame_to_rows(frame)
        return out

    for sym in symbols:
        try:
            level0 = frame.columns.get_level_values(0)
            if sym not in level0:
                continue
            sub = frame[sym].dropna(how="all")
            if sub.empty:
                continue
            sub = sub.dropna(subset=["Close"], how="all")
            if sub.empty:
                continue
            out[sym] = _frame_to_rows(sub)
        except Exception:
            logger.exception("Failed parsing batch frame for %s", sym)
    return out


def fetch_fundamentals(yfinance_symbol: str) -> dict:
    """Return a compact, JSON-safe fundamentals snapshot from yfinance."""

    def _load_info():
        ticker = yf.Ticker(yfinance_symbol)
        return ticker.get_info() or {}

    info = retry_call(_load_info, label=f"yfinance.info({yfinance_symbol})")

    def clean(v):
        if v is None:
            return None
        try:
            if pd.isna(v):
                return None
        except (TypeError, ValueError):
            pass
        if hasattr(v, "item"):
            v = v.item()
        if isinstance(v, (str, int, float, bool)):
            return v
        return str(v)

    keys = [
        "marketCap",
        "trailingPE",
        "forwardPE",
        "priceToBook",
        "enterpriseValue",
        "totalRevenue",
        "revenuePerShare",
        "grossProfits",
        "ebitda",
        "netIncomeToCommon",
        "profitMargins",
        "operatingMargins",
        "returnOnEquity",
        "returnOnAssets",
        "debtToEquity",
        "currentRatio",
        "quickRatio",
        "trailingEps",
        "bookValue",
        "dividendYield",
        "payoutRatio",
        "currency",
        "financialCurrency",
    ]
    snapshot = {k: clean(info.get(k)) for k in keys if info.get(k) is not None}
    snapshot["company_name"] = clean(info.get("longName") or info.get("shortName"))
    snapshot["updated_at"] = pd.Timestamp.utcnow().isoformat()
    return snapshot
