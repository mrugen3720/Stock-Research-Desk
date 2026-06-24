"""Deterministic factor scoring (NO LLM here — pure math, so it's backtestable).

Two stages:
  - price_factors(ohlcv)      : momentum + trend/technical from price (all 500, cheap).
  - fundamental_factors(...)  : quality + value from yfinance .info (top names only).
Then rank_and_score() turns raw factors into cross-sectional 0-100 percentile
component scores and a horizon-weighted composite 0-100.

Factor families follow NSE's published methodology: Momentum (vol-adjusted
6m/12m return), Quality (ROE, low debt, margins), Value (low P/E, P/B), plus a
Trend/Technical read (price vs SMA50/200, distance from 52w high).
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .. import data, fundamentals, indicators

# Composite weights per horizon (must sum to 1.0 within each row).
_WEIGHTS = {
    "swing":      {"momentum": 0.35, "technical": 0.35, "quality": 0.15, "value": 0.15},
    "positional": {"momentum": 0.15, "technical": 0.15, "quality": 0.35, "value": 0.35},
}
_FUND_CACHE = Path("data/fundamentals")


def _pct_rank(s: pd.Series, ascending: bool = True) -> pd.Series:
    """Cross-sectional percentile rank, 0-100 (higher = better)."""
    return s.rank(ascending=ascending, pct=True) * 100.0


def price_factors(ohlcv: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Per-ticker momentum + trend factors + the fields levels.py needs."""
    rows = {}
    for ticker, df in ohlcv.items():
        try:
            ind = indicators.compute(df)
            close = df["Close"].dropna()
            if len(close) < 60 or not ind.get("last_close"):
                continue
            ret_12m = float(close.iloc[-1] / close.iloc[0] - 1) * 100
            ret_6m = ind.get("ret_6m_pct") or 0.0
            daily = close.pct_change().dropna()
            vol = float(daily.std() * math.sqrt(252)) if len(daily) > 20 else np.nan
            mom_raw = (0.4 * ret_6m + 0.6 * ret_12m) / (vol + 1e-6) if vol and vol > 0 else (0.4 * ret_6m + 0.6 * ret_12m)
            swing_low = float(df["Low"].tail(10).min())
            rows[ticker] = {
                "last_close": ind["last_close"],
                "atr14": ind.get("atr14"),
                "sma20": ind.get("sma20"),
                "sma50": ind.get("sma50"),
                "sma200": ind.get("sma200"),
                "swing_low": round(swing_low, 2),
                "price_vs_sma50_pct": ind.get("price_vs_sma50_pct"),
                "price_vs_sma200_pct": ind.get("price_vs_sma200_pct"),
                "rsi14": ind.get("rsi14"),
                "macd_hist": ind.get("macd_hist"),
                "pct_below_52w_high": ind.get("pct_below_52w_high"),
                "ret_6m_pct": ret_6m,
                "ret_12m_pct": round(ret_12m, 2),
                "avg_volume_20d": ind.get("avg_volume_20d"),
                "mom_raw": round(float(mom_raw), 4),
                "above_sma200": bool(ind.get("price_vs_sma200_pct") and ind["price_vs_sma200_pct"] > 0),
            }
        except Exception:
            continue
    return pd.DataFrame.from_dict(rows, orient="index")


def fundamental_factors(tickers: list[str]) -> pd.DataFrame:
    """Per-ticker quality + value factors from yfinance .info (daily-cached)."""
    _FUND_CACHE.mkdir(parents=True, exist_ok=True)
    cache = _FUND_CACHE / f"fund_{pd.Timestamp.today().date()}.json"
    cached = json.loads(cache.read_text()) if cache.exists() else {}

    rows = {}
    dirty = False
    for ticker in tickers:
        if ticker in cached:
            rows[ticker] = cached[ticker]
            continue
        try:
            m = fundamentals.compute(data.get_info(ticker))
            rows[ticker] = {
                "roe_pct": m.get("roe_pct"),
                "debt_to_equity": m.get("debt_to_equity"),
                "profit_margin_pct": m.get("profit_margin_pct"),
                "trailing_pe": m.get("trailing_pe"),
                "price_to_book": m.get("price_to_book"),
                "earnings_growth_pct": m.get("earnings_growth_pct"),
            }
            cached[ticker] = rows[ticker]
            dirty = True
        except Exception:
            continue
    if dirty:
        try:
            cache.write_text(json.dumps(cached))
        except Exception:
            pass
    return pd.DataFrame.from_dict(rows, orient="index")


def rank_and_score(price_df: pd.DataFrame, fund_df: pd.DataFrame, horizon: str) -> pd.DataFrame:
    """Combine raw factors into 0-100 component scores + a composite (0-100)."""
    w = _WEIGHTS.get(horizon, _WEIGHTS["swing"])
    df = price_df.copy()

    # Momentum (higher better).
    df["momentum_score"] = _pct_rank(df["mom_raw"])

    # Technical: trend strength + closeness to 52w high (less-negative = better).
    tech = pd.concat([
        _pct_rank(df["price_vs_sma50_pct"]),
        _pct_rank(df["price_vs_sma200_pct"]),
        _pct_rank(df["pct_below_52w_high"]),   # e.g. -3 ranks above -30
    ], axis=1).mean(axis=1)
    df["technical_score"] = tech

    # Quality + value (joined; lower P/E, P/B, debt are better -> ascending=False).
    if not fund_df.empty:
        f = fund_df.reindex(df.index)
        qual = pd.concat([
            _pct_rank(f["roe_pct"]),
            _pct_rank(f["debt_to_equity"], ascending=False),
            _pct_rank(f["profit_margin_pct"]),
        ], axis=1).mean(axis=1)
        val = pd.concat([
            _pct_rank(f["trailing_pe"], ascending=False),
            _pct_rank(f["price_to_book"], ascending=False),
        ], axis=1).mean(axis=1)
    else:
        qual = pd.Series(np.nan, index=df.index)
        val = pd.Series(np.nan, index=df.index)
    # Missing fundamentals -> neutral 50 (don't nuke a price-strong name).
    df["quality_score"] = qual.fillna(50.0)
    df["value_score"] = val.fillna(50.0)

    df["composite"] = (
        w["momentum"] * df["momentum_score"]
        + w["technical"] * df["technical_score"]
        + w["quality"] * df["quality_score"]
        + w["value"] * df["value_score"]
    ).round(1)

    return df.sort_values("composite", ascending=False)
