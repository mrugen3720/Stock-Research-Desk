"""Risk-defined trade levels + rupee position sizing.

For a candidate, turn price + ATR into an entry zone, an ATR/structure stop, a
2:1+ target, and the SHARE QUANTITY that caps the loss at RISK_PER_TRADE_PCT of
ACCOUNT_CAPITAL. This is what makes "little risk" structural rather than a hope.
"""

import math

from .. import config

# (stop ATR multiple, reward:risk target) per horizon.
_PARAMS = {"swing": (2.0, 2.0), "positional": (3.0, 2.5)}


def compute_levels(row: dict, horizon: str,
                   capital: float | None = None, risk_pct: float | None = None) -> dict:
    """Return entry/stop/target/RR + share qty + rupee risk for one candidate."""
    capital = capital if capital is not None else config.ACCOUNT_CAPITAL
    risk_pct = risk_pct if risk_pct is not None else config.RISK_PER_TRADE_PCT
    k, rr_target = _PARAMS.get(horizon, _PARAMS["swing"])

    entry = float(row["last_close"])
    atr = float(row.get("atr14") or 0) or entry * 0.02   # fallback 2% if ATR missing
    swing_low = float(row.get("swing_low") or 0)

    # Stop = the safer (lower) of the ATR stop and just under the recent swing low.
    atr_stop = entry - k * atr
    struct_stop = swing_low * 0.995 if swing_low > 0 else atr_stop
    stop = round(min(atr_stop, struct_stop), 2)

    risk_per_share = round(entry - stop, 2)
    if risk_per_share <= 0:
        return {"valid": False, "reason": "non-positive stop distance"}

    target = round(entry + rr_target * risk_per_share, 2)
    rr = round((target - entry) / risk_per_share, 2)

    budget = capital * (risk_pct / 100.0)
    qty = int(math.floor(budget / risk_per_share))
    rupee_risk = round(qty * risk_per_share, 2)
    deploy = round(qty * entry, 2)

    return {
        "valid": qty >= 1 and rr >= 2,
        "entry": round(entry, 2),
        "entry_zone": (round(entry * 0.99, 2), round(entry, 2)),
        "stop": stop,
        "target": target,
        "risk_per_share": risk_per_share,
        "reward_risk": rr,
        "qty": qty,
        "rupee_risk": rupee_risk,
        "rupee_deploy": deploy,
        "note": "" if qty >= 1 else "1 share risks more than your budget — raise capital or risk%",
    }
