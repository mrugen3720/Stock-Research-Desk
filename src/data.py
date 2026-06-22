"""The data tap — the ONLY file that talks to the market-data source.

Everything here is a thin wrapper around `yfinance` (a library that downloads
free stock data from Yahoo Finance). Keeping all of that behind these few
functions means the rest of the code just calls e.g. `get_daily_candles("BEL.NS")`
and never has to care *where* the data comes from. If we ever swap data sources,
this is the only file that changes.
"""

import yfinance as yf


def get_daily_candles(ticker: str, period: str = "1y"):
    """Daily OHLCV for a ticker. Raises ValueError if nothing comes back.

    A 1-year window (vs Phase 2's 6mo) gives enough history for SMA-200 and a
    real 52-week reference.
    """
    candles = yf.Ticker(ticker).history(period=period, interval="1d")
    if candles.empty:
        raise ValueError(
            f"No price history for {ticker!r}. Check the symbol "
            "(NSE tickers end in .NS)."
        )
    return candles


def get_info(ticker: str) -> dict:
    """yfinance .info snapshot (valuation, margins, balance-sheet ratios)."""
    return yf.Ticker(ticker).info or {}


def get_financials(ticker: str):
    """Annual income statement (yfinance .financials). May be empty."""
    return yf.Ticker(ticker).financials


def get_last_price(ticker: str):
    """Latest close. Anchors the Judge's 'dead price' level. None on failure."""
    try:
        candles = yf.Ticker(ticker).history(period="5d", interval="1d")
        if candles.empty:
            return None
        return round(float(candles["Close"].iloc[-1]), 2)
    except Exception:
        return None
