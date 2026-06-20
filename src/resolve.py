"""Resolve free-text stock names/abbreviations to an NSE (.NS) ticker.

The user should be able to type "reliance", "tata steel", "Tata Power", "cdsl",
"BEL", "infosys" — and we figure out the right NSE symbol. Strategy, cheapest
first:

1. Curated aliases for short forms search handles poorly (rel, ril, l&t, sbi...).
2. Already a ticker? (RELIANCE.NS / TATASTEEL.BO) -> normalize to .NS.
3. A bare symbol? ("BEL", "tatasteel") -> try SYMBOL.NS and verify it has data.
4. Yahoo search -> prefer an NSE (NSI) equity; else take the best equity and
   swap its suffix to .NS, verifying it resolves.

Returns (ticker, display_name). Raises ValueError if nothing resolves.
"""

import re

import yfinance as yf

# Short forms / nicknames that plain search resolves poorly or ambiguously.
ALIASES = {
    "rel": "RELIANCE.NS",
    "ril": "RELIANCE.NS",
    "reliance": "RELIANCE.NS",
    "l&t": "LT.NS",
    "lt": "LT.NS",
    "larsen": "LT.NS",
    "sbi": "SBIN.NS",
    "tata steel": "TATASTEEL.NS",
    "tisco": "TATASTEEL.NS",          # old name: Tata Iron & Steel Co.
    "tata power": "TATAPOWER.NS",
    "tata motors": "TATAMOTORS.NS",
    "telco": "TATAMOTORS.NS",         # old name: Tata Engineering & Locomotive Co.
    "tata comm": "TATACOMM.NS",
    "tata communications": "TATACOMM.NS",
    "cdsl": "CDSL.NS",
    "bel": "BEL.NS",
    "hal": "HAL.NS",
    "infy": "INFY.NS",
    "infosys": "INFY.NS",
    "tcs": "TCS.NS",
    # Rebrands where the old name no longer maps to a live NSE symbol.
    "zomato": "ETERNAL.NS",
    "eternal": "ETERNAL.NS",
}

_TICKER_RE = re.compile(r"[A-Za-z0-9&-]{1,15}\.(NS|BO)", re.IGNORECASE)
_SYMBOL_RE = re.compile(r"[A-Za-z0-9&-]{1,15}")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip()).lower()


def _name_of(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info or {}
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker


def _is_valid(ticker: str) -> bool:
    """A ticker is usable if it returns recent price history."""
    try:
        return not yf.Ticker(ticker).history(period="5d").empty
    except Exception:
        return False


def _search_resolve(query: str):
    try:
        quotes = yf.Search(query, max_results=10).quotes
    except Exception:
        quotes = []

    # Prefer an NSE-listed equity outright.
    for q in quotes:
        if q.get("exchange") == "NSI" and q.get("quoteType") == "EQUITY" and q.get("symbol"):
            sym = q["symbol"]
            return sym, q.get("shortname") or q.get("longname") or sym

    # Otherwise take the best equity (often a .BO/BSE listing) and swap to .NS.
    for q in quotes:
        if q.get("quoteType") == "EQUITY" and q.get("symbol"):
            root = q["symbol"].split(".")[0]
            cand = f"{root}.NS"
            if _is_valid(cand):
                return cand, q.get("shortname") or q.get("longname") or cand

    return None


def resolve(query: str):
    """Resolve free text to (ticker, display_name). Raises ValueError on failure."""
    raw = query.strip()
    if not raw:
        raise ValueError("empty query")
    key = _norm(raw)

    # 1. Curated alias.
    if key in ALIASES:
        t = ALIASES[key]
        return t, _name_of(t)

    # 2. Already a ticker.
    if _TICKER_RE.fullmatch(raw):
        t = raw.upper()
        if t.endswith(".BO"):
            alt = t[:-3] + ".NS"
            if _is_valid(alt):
                return alt, _name_of(alt)
        return t, _name_of(t)

    # 3. Bare single-token symbol -> try SYMBOL.NS.
    if _SYMBOL_RE.fullmatch(raw) and " " not in raw:
        cand = raw.upper() + ".NS"
        if _is_valid(cand):
            return cand, _name_of(cand)

    # 4. Yahoo search.
    found = _search_resolve(raw)
    if found:
        return found

    raise ValueError(
        f"Could not resolve {query!r} to an NSE stock. Try the ticker (e.g. RELIANCE.NS)."
    )
