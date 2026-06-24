"""Bulk price download for the whole universe — chunked + daily-cached.

Fetching 500 tickers one-by-one is slow; `yf.download` pulls many at once.
Results are cached per day so repeated scans/backtests are instant.
"""

import time
from pathlib import Path

import pandas as pd
import yfinance as yf

_CACHE_DIR = Path("data/ohlcv")


def get_bulk_ohlcv(
    tickers: list[str], period: str = "1y", chunk: int = 50, use_cache: bool = True
) -> dict[str, pd.DataFrame]:
    """Return {ticker: OHLCV DataFrame} for many tickers.

    Cached to `data/ohlcv/bulk_<period>_<today>.pkl`. Each frame has the
    Open/High/Low/Close/Volume columns + a DatetimeIndex, exactly what
    `indicators.compute` expects.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache = _CACHE_DIR / f"bulk_{period}_{pd.Timestamp.today().date()}.pkl"
    if use_cache and cache.exists():
        return _split(pd.read_pickle(cache))

    frames = []
    for i in range(0, len(tickers), chunk):
        part = tickers[i : i + chunk]
        df = yf.download(
            part, period=period, interval="1d", auto_adjust=True,
            progress=False, group_by="ticker", threads=True,
        )
        if not df.empty:
            frames.append(df)
        time.sleep(0.4)  # be gentle with the free endpoint

    if not frames:
        return {}
    big = pd.concat(frames, axis=1)
    try:
        big.to_pickle(cache)
    except Exception:
        pass
    return _split(big)


def _split(big: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split a (ticker, field) multi-column frame into per-ticker frames."""
    out: dict[str, pd.DataFrame] = {}
    if big.empty:
        return out
    tickers = list(dict.fromkeys(big.columns.get_level_values(0)))
    for t in tickers:
        sub = big[t].dropna(how="all")
        if not sub.empty and "Close" in sub.columns and sub["Close"].notna().sum() > 60:
            out[t] = sub
    return out
