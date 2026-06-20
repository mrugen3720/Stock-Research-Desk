"""Thin yfinance wrapper. One place for all raw market data access."""

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
