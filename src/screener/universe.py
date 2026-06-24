"""The Nifty 500 universe — the list of stocks the screener ranks.

Downloads the official constituents CSV from niftyindices.com (cached weekly),
and falls back to a small bundled list if the download is blocked. Returns
tickers as `SYMBOL.NS` (yfinance form).
"""

import io
import time
from pathlib import Path

import pandas as pd
import requests

_CACHE = Path("data/nifty500.csv")
_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"
_MAX_AGE_S = 7 * 24 * 3600  # refresh weekly

# Minimal fallback (large, liquid names) so the screener still runs offline.
_FALLBACK = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "BHARTIARTL", "SBIN",
    "LT", "ITC", "HINDUNILVR", "KOTAKBANK", "AXISBANK", "BAJFINANCE", "MARUTI",
    "SUNPHARMA", "ASIANPAINT", "TITAN", "TATASTEEL", "TATAMOTORS", "TATAPOWER",
    "BEL", "HAL", "CDSL", "IRCTC", "DLF", "ADANIPORTS", "POWERGRID", "NTPC",
    "ONGC", "COALINDIA", "WIPRO", "ULTRACEMCO", "NESTLEIND", "GRASIM", "CIPLA",
]


def _fresh(path: Path) -> bool:
    return path.exists() and (time.time() - path.stat().st_mtime) < _MAX_AGE_S


def _symbols() -> list[str]:
    """Raw symbols (no .NS) — from cache, else fresh download, else fallback."""
    if _fresh(_CACHE):
        try:
            return pd.read_csv(_CACHE)["Symbol"].dropna().astype(str).tolist()
        except Exception:
            pass
    try:
        resp = requests.get(_URL, headers={"User-Agent": "Mozilla/5.0"}, timeout=25)
        resp.raise_for_status()
        df = pd.read_csv(io.StringIO(resp.text))
        _CACHE.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(_CACHE, index=False)
        return df["Symbol"].dropna().astype(str).tolist()
    except Exception:
        if _CACHE.exists():  # stale cache beats nothing
            try:
                return pd.read_csv(_CACHE)["Symbol"].dropna().astype(str).tolist()
            except Exception:
                pass
    return _FALLBACK


def get_universe(limit: int | None = None) -> list[str]:
    """Nifty 500 tickers as `SYMBOL.NS`. `limit` truncates (handy for testing)."""
    syms = [f"{s.strip()}.NS" for s in _symbols() if s and str(s).strip()]
    return syms[:limit] if limit else syms
