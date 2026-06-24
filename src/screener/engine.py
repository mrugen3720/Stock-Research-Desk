"""The screener funnel — universe -> rank -> top picks with levels & score.

Cheap price/momentum factors run on all 500; fundamentals (slow) are fetched
only for the top ~120 price-ranked names. The final ranked list is cached per
day so the Discord command is instant.

    python -m src.screener.engine            # swing, prints top 10
    python -m src.screener.engine positional
"""

import json
import sys
from pathlib import Path

import pandas as pd

from . import data_bulk, factors, levels, score, universe

_CACHE = Path("data/ranked")


def run_screen(horizon: str = "swing", top_n: int = 10,
               universe_limit: int | None = None, use_cache: bool = True) -> list[dict]:
    """Return the top_n ranked picks (each a dict of factors + levels + score)."""
    _CACHE.mkdir(parents=True, exist_ok=True)
    cache = _CACHE / f"ranked_{horizon}_{pd.Timestamp.today().date()}.json"
    if use_cache and universe_limit is None and cache.exists():
        return json.loads(cache.read_text())[:top_n]

    tickers = universe.get_universe(limit=universe_limit)
    ohlcv = data_bulk.get_bulk_ohlcv(tickers, period="1y", use_cache=use_cache)
    pf = factors.price_factors(ohlcv)
    if pf.empty:
        return []

    # Stage 1: price-only rank -> top names worth fetching fundamentals for.
    price_only = factors.rank_and_score(pf, pd.DataFrame(), "swing")
    top_for_fund = price_only.head(120).index.tolist()
    fund_df = factors.fundamental_factors(top_for_fund)

    # Stage 2: full horizon-weighted composite.
    scored = factors.rank_and_score(pf, fund_df, horizon)

    picks = []
    for ticker, row in scored.iterrows():
        r = row.to_dict()
        lv = levels.compute_levels(r, horizon)
        if not lv.get("valid"):
            continue
        picks.append({
            "ticker": ticker,
            "horizon": horizon,
            "score": score.trade_score(r),
            "composite": r["composite"],
            "momentum": round(float(r["momentum_score"]), 0),
            "technical": round(float(r["technical_score"]), 0),
            "quality": round(float(r["quality_score"]), 0),
            "value": round(float(r["value_score"]), 0),
            "ret_6m_pct": r.get("ret_6m_pct"),
            "ret_12m_pct": r.get("ret_12m_pct"),
            "rsi14": r.get("rsi14"),
            **lv,
        })
        if len(picks) >= max(top_n, 10):
            break

    picks.sort(key=lambda p: p["score"], reverse=True)
    if universe_limit is None:
        try:
            cache.write_text(json.dumps(picks))
        except Exception:
            pass
    return picks[:top_n]


def main():
    horizon = sys.argv[1] if len(sys.argv) > 1 else "swing"
    print(f"Screening Nifty 500 ({horizon}) ...\n")
    picks = run_screen(horizon, use_cache=False)
    for i, p in enumerate(picks, 1):
        print(f"{i:>2}. {p['ticker']:14s} score={p['score']:>3}  "
              f"entry={p['entry']:>8}  stop={p['stop']:>8}  target={p['target']:>8}  "
              f"R:R={p['reward_risk']}  qty={p['qty']}")


if __name__ == "__main__":
    main()
