"""Historical backtest of the momentum/technical ranking + ATR trade rules.

Monthly, we rank the universe by point-in-time momentum (only data available
then), "buy" the top N, and simulate the swing rules (2*ATR stop, 2R target,
max-hold) forward bar-by-bar. Reports win-rate, avg R, expectancy, CAGR, and max
drawdown, and saves an equity curve.

IMPORTANT LIMITATION: yfinance `.info` is current-only, so QUALITY/VALUE factors
are NOT point-in-time and are excluded here. This backtest validates the
price/momentum + technical edge and the exit rules only. Past results are not
future returns.

    python -m src.screener.backtest            # ~3y, top 20/month, 150-name universe
"""

import sys

import numpy as np
import pandas as pd

from .. import indicators
from . import data_bulk, universe

RISK_FRAC = 0.01      # 1% of equity risked per trade (for the equity curve)
MAX_HOLD = 20         # trading days (swing)
TOP_N = 20            # positions per monthly rebalance
ATR_K, RR = 2.0, 2.0  # stop multiple, reward:risk


def _close_matrix(ohlcv: dict) -> pd.DataFrame:
    cols = {t: df["Close"] for t, df in ohlcv.items() if "Close" in df}
    return pd.DataFrame(cols).sort_index()


def _simulate_trade(df: pd.DataFrame, d) -> float | None:
    """Return realized R for entering `df` at date d under the swing rules."""
    upto = df.loc[:d]
    if len(upto) < 60:
        return None
    atr = indicators.compute(upto).get("atr14")
    entry = float(upto["Close"].iloc[-1])
    if not atr or atr <= 0:
        return None
    stop = entry - ATR_K * atr
    risk = entry - stop
    target = entry + RR * risk
    fwd = df.loc[df.index > d].head(MAX_HOLD)
    if fwd.empty:
        return None
    for _, bar in fwd.iterrows():
        if bar["Low"] <= stop:
            return -1.0
        if bar["High"] >= target:
            return RR
    return float((fwd["Close"].iloc[-1] - entry) / risk)   # time exit


def run_backtest(universe_limit: int = 150, period: str = "3y") -> dict:
    tickers = universe.get_universe(limit=universe_limit)
    ohlcv = data_bulk.get_bulk_ohlcv(tickers, period=period, use_cache=True)
    close = _close_matrix(ohlcv)
    if close.empty:
        return {"error": "no data"}

    idx = close.index
    # Last available trading day of each month (point-in-time, no calendar gaps).
    months = idx.to_period("M")
    rebal = [idx[np.where(months == p)[0][-1]] for p in months.unique()]

    trades = []
    for d in rebal:
        loc = idx.get_loc(d)
        if loc < 252:
            continue
        now = close.iloc[loc]
        c6 = close.iloc[loc - 126]
        c12 = close.iloc[loc - 252]
        mom = (0.4 * (now / c6 - 1) + 0.6 * (now / c12 - 1)).dropna()
        for t in mom.sort_values(ascending=False).head(TOP_N).index:
            r = _simulate_trade(ohlcv[t], d)
            if r is not None:
                trades.append({"exit_order": d, "ticker": t, "R": r})

    if not trades:
        return {"error": "no trades"}
    tdf = pd.DataFrame(trades).sort_values("exit_order").reset_index(drop=True)

    # Equity curve: compound fixed-fractional risk per trade, in time order.
    equity = (1 + RISK_FRAC * tdf["R"]).cumprod()
    peak = equity.cummax()
    max_dd = float(((equity - peak) / peak).min() * 100)
    years = (idx[-1] - idx[0]).days / 365.25
    cagr = float(equity.iloc[-1] ** (1 / years) - 1) * 100 if years > 0 else 0.0

    out_path = f"data/backtest_{period}_{pd.Timestamp.today().date()}.csv"
    pd.DataFrame({"equity": equity.values}).to_csv(out_path, index=False)

    R = tdf["R"]
    return {
        "trades": len(tdf),
        "win_rate_pct": round(100 * float((R > 0).mean()), 1),
        "avg_R": round(float(R.mean()), 3),
        "expectancy_R": round(float(R.mean()), 3),
        "CAGR_pct": round(cagr, 1),
        "max_drawdown_pct": round(max_dd, 1),
        "equity_curve_csv": out_path,
    }


def main():
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 150
    print(f"Backtesting momentum/technical ranking on {limit} names ...\n")
    res = run_backtest(universe_limit=limit)
    for k, v in res.items():
        print(f"  {k:18s}: {v}")
    print("\nNote: momentum/technical + ATR rules only. Quality/Value are NOT "
          "point-in-time (yfinance .info is current-only) and were excluded.")
    print("Past results are not future returns. Paper-trade before risking capital.")


if __name__ == "__main__":
    main()
