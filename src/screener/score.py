"""The 0-100 "take this trade" score.

Factor rank (the composite) dominates, nudged by setup quality (trend alignment,
not over-extended). Deterministic — same inputs always give the same score.
"""


def trade_score(row: dict) -> int:
    """Blend the factor composite (0-100) with a setup-quality adjustment."""
    composite = float(row.get("composite") or 0)

    setup = 50.0
    if row.get("above_sma200"):
        setup += 25
    else:
        setup -= 10
    if (row.get("macd_hist") or 0) > 0:
        setup += 15
    rsi = row.get("rsi14")
    if rsi is not None:
        if rsi > 78:          # over-extended — worse entry
            setup -= 20
        elif rsi < 35:        # falling knife
            setup -= 15
    setup = max(0.0, min(100.0, setup))

    return int(round(0.7 * composite + 0.3 * setup))
