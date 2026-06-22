"""The chart math — turns raw prices into technical indicators (NO AI here).

This file is plain arithmetic with pandas/numpy. It exists because of a core
rule of the project: the AI must never compute numbers (it can confidently get
them wrong). So we calculate the real indicators — moving averages, RSI, MACD,
ATR, returns, volume trends — here, and the technicals worker only *interprets*
them.

Two functions matter to a reader:
  - compute(df)         -> a dict of numbers (the actual indicators).
  - to_prompt_block(d)  -> those numbers as a tidy text block for the AI prompt.
The underscore-prefixed helpers (_rsi, _macd, _atr) are the individual formulas.
"""

import numpy as np
import pandas as pd


def _round(x, dp=2):
    """Round to a float, or return None for NaN/missing so prompts say 'n/a'."""
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return None
    return round(float(x), dp)


def _rsi(close: pd.Series, period: int = 14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    # Wilder's smoothing via EWM.
    avg_gain = gain.ewm(alpha=1 / period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = close.ewm(span=fast, adjust=False).mean()
    ema_slow = close.ewm(span=slow, adjust=False).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    return macd, signal_line, macd - signal_line


def _atr(df: pd.DataFrame, period: int = 14):
    high, low, close = df["High"], df["Low"], df["Close"]
    prev_close = close.shift(1)
    true_range = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1
    ).max(axis=1)
    return true_range.ewm(alpha=1 / period, min_periods=period).mean()


def compute(df: pd.DataFrame) -> dict:
    """Return a dict of technical indicators for the latest session."""
    close = df["Close"]
    last = close.iloc[-1]

    sma20 = close.rolling(20).mean().iloc[-1]
    sma50 = close.rolling(50).mean().iloc[-1]
    sma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else np.nan

    rsi14 = _rsi(close).iloc[-1]
    macd, signal, hist = _macd(close)
    atr14 = _atr(df).iloc[-1]

    hi_52w, lo_52w = df["High"].max(), df["Low"].min()
    vol = df["Volume"]
    avg_vol20 = vol.rolling(20).mean().iloc[-1]
    last_vol = vol.iloc[-1]

    def ret_over(days):
        if len(close) <= days:
            return np.nan
        return (last / close.iloc[-1 - days] - 1) * 100

    return {
        "last_close": _round(last),
        "sma20": _round(sma20),
        "sma50": _round(sma50),
        "sma200": _round(sma200),
        "price_vs_sma20_pct": _round((last / sma20 - 1) * 100) if sma20 else None,
        "price_vs_sma50_pct": _round((last / sma50 - 1) * 100) if sma50 else None,
        "price_vs_sma200_pct": (
            _round((last / sma200 - 1) * 100) if sma200 and not np.isnan(sma200) else None
        ),
        "golden_cross_50_over_200": (
            bool(sma50 > sma200) if not np.isnan(sma200) else None
        ),
        "rsi14": _round(rsi14),
        "macd": _round(macd.iloc[-1], 3),
        "macd_signal": _round(signal.iloc[-1], 3),
        "macd_hist": _round(hist.iloc[-1], 3),
        "atr14": _round(atr14),
        "atr14_pct_of_price": _round(atr14 / last * 100) if last else None,
        "ret_1m_pct": _round(ret_over(21)),
        "ret_3m_pct": _round(ret_over(63)),
        "ret_6m_pct": _round(ret_over(126)),
        "high_52w": _round(hi_52w),
        "low_52w": _round(lo_52w),
        "pct_below_52w_high": _round((last / hi_52w - 1) * 100),
        "pct_above_52w_low": _round((last / lo_52w - 1) * 100),
        "last_volume": int(last_vol) if not np.isnan(last_vol) else None,
        "avg_volume_20d": int(avg_vol20) if not np.isnan(avg_vol20) else None,
        "volume_vs_avg_pct": _round((last_vol / avg_vol20 - 1) * 100) if avg_vol20 else None,
        "window_start": str(df.index[0].date()),
        "window_end": str(df.index[-1].date()),
        "sessions": int(len(df)),
    }


def to_prompt_block(ind: dict) -> str:
    """Render the indicator dict as a compact, labelled text block for the LLM."""
    def g(k):
        v = ind.get(k)
        return "n/a" if v is None else v

    return (
        f"Data window: {g('window_start')} -> {g('window_end')} "
        f"({g('sessions')} sessions)\n"
        f"Last close: {g('last_close')}\n"
        f"Moving averages: SMA20={g('sma20')}, SMA50={g('sma50')}, SMA200={g('sma200')}\n"
        f"Price vs MAs (%): vs20={g('price_vs_sma20_pct')}, "
        f"vs50={g('price_vs_sma50_pct')}, vs200={g('price_vs_sma200_pct')}\n"
        f"Golden cross (SMA50>SMA200): {g('golden_cross_50_over_200')}\n"
        f"RSI(14): {g('rsi14')}\n"
        f"MACD: {g('macd')} | signal: {g('macd_signal')} | hist: {g('macd_hist')}\n"
        f"ATR(14): {g('atr14')} ({g('atr14_pct_of_price')}% of price)\n"
        f"Returns (%): 1m={g('ret_1m_pct')}, 3m={g('ret_3m_pct')}, 6m={g('ret_6m_pct')}\n"
        f"52-week: high={g('high_52w')}, low={g('low_52w')}, "
        f"{g('pct_below_52w_high')}% from high, {g('pct_above_52w_low')}% above low\n"
        f"Volume: last={g('last_volume')}, 20d-avg={g('avg_volume_20d')}, "
        f"vs-avg={g('volume_vs_avg_pct')}%"
    )
