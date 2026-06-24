"""Paper-trade tracker — log every pick, then measure what actually happened.

This is how we validate the screener LIVE (vs only in backtest). Each pick is
appended to data/recommendations.csv; update_outcomes() walks forward day-by-day
to mark hit-target / hit-stop / open and compute the realized R multiple, then
scorecard() reports the running win-rate and expectancy.

    python -m src.screener.tracker      # update outcomes + print the scorecard
"""

from pathlib import Path

import pandas as pd
import yfinance as yf

_LOG = Path("data/recommendations.csv")
_COLS = ["date", "ticker", "horizon", "score", "entry", "stop", "target",
         "qty", "reward_risk", "status", "exit_date", "exit_price", "R"]


def _load() -> pd.DataFrame:
    if _LOG.exists():
        return pd.read_csv(_LOG)
    return pd.DataFrame(columns=_COLS)


def log_recommendations(picks: list[dict], horizon: str) -> int:
    """Append today's picks (skipping ones already logged today). Returns count."""
    _LOG.parent.mkdir(parents=True, exist_ok=True)
    df = _load()
    today = str(pd.Timestamp.today().date())
    existing = set(zip(df.get("date", []), df.get("ticker", []), df.get("horizon", [])))
    new = []
    for p in picks:
        key = (today, p["ticker"], horizon)
        if key in existing:
            continue
        new.append({
            "date": today, "ticker": p["ticker"], "horizon": horizon,
            "score": p["score"], "entry": p["entry"], "stop": p["stop"],
            "target": p["target"], "qty": p["qty"], "reward_risk": p["reward_risk"],
            "status": "open", "exit_date": "", "exit_price": "", "R": "",
        })
    if new:
        pd.concat([df, pd.DataFrame(new)], ignore_index=True).to_csv(_LOG, index=False)
    return len(new)


def update_outcomes() -> pd.DataFrame:
    """Resolve open trades against subsequent prices. Stop checked before target."""
    df = _load()
    if df.empty:
        return df
    for i, row in df[df["status"] == "open"].iterrows():
        try:
            hist = yf.Ticker(row["ticker"]).history(start=row["date"])
        except Exception:
            continue
        hist = hist[hist.index.date > pd.to_datetime(row["date"]).date()]  # forward only
        for ts, bar in hist.iterrows():
            if bar["Low"] <= row["stop"]:                 # conservative: stop first
                df.loc[i, ["status", "exit_date", "exit_price", "R"]] = \
                    ["stop", str(ts.date()), round(row["stop"], 2), -1.0]
                break
            if bar["High"] >= row["target"]:
                df.loc[i, ["status", "exit_date", "exit_price", "R"]] = \
                    ["target", str(ts.date()), round(row["target"], 2), float(row["reward_risk"])]
                break
    df.to_csv(_LOG, index=False)
    return df


def scorecard(df: pd.DataFrame | None = None) -> dict:
    """Aggregate closed trades into win-rate / avg R / expectancy."""
    df = _load() if df is None else df
    closed = df[df["status"].isin(["stop", "target"])]
    n = len(closed)
    if n == 0:
        return {"closed": 0, "open": int((df["status"] == "open").sum())}
    R = pd.to_numeric(closed["R"], errors="coerce")
    wins = int((closed["status"] == "target").sum())
    return {
        "closed": n,
        "open": int((df["status"] == "open").sum()),
        "win_rate_pct": round(100 * wins / n, 1),
        "avg_R": round(float(R.mean()), 2),
        "expectancy_R": round(float(R.mean()), 2),
        "total_R": round(float(R.sum()), 2),
    }


def main():
    update_outcomes()
    sc = scorecard()
    print("Paper-trade scorecard:")
    for k, v in sc.items():
        print(f"  {k:14s}: {v}")
    if sc.get("closed", 0) == 0:
        print("  (no closed trades yet — let some picks play out, then re-run)")


if __name__ == "__main__":
    main()
