"""The very first thing built — a plain data dump for ONE stock. NO AI at all.

This was step 2 of the project, before any agents existed. It just pulls ~6
months of prices plus a few fundamentals and prints them, to prove the data
source works. It's still handy as a quick sanity check: if this prints clean
numbers, the data layer is healthy. A nice, dependency-light file to read first.

Usage:
    python scripts/fetch_one.py          # defaults to BEL.NS
    python scripts/fetch_one.py TCS.NS   # any NSE ticker
"""

import sys

import yfinance as yf


def fmt(value, prefix="", suffix="", dp=2):
    """Format a number, or return 'n/a' if it's missing."""
    if value is None:
        return "n/a"
    try:
        if isinstance(value, (int, float)):
            return f"{prefix}{value:,.{dp}f}{suffix}"
        return f"{prefix}{value}{suffix}"
    except (TypeError, ValueError):
        return "n/a"


def crore(value):
    """Indian-style: render a raw rupee figure in crore (1 crore = 1e7)."""
    if value is None:
        return "n/a"
    try:
        return f"Rs {value / 1e7:,.0f} cr"
    except (TypeError, ValueError):
        return "n/a"


def fetch(ticker_symbol):
    ticker = yf.Ticker(ticker_symbol)

    # --- 6 months of daily candles ---
    candles = ticker.history(period="6mo", interval="1d")
    if candles.empty:
        print(f"ERROR: no price history returned for {ticker_symbol!r}. "
              "Check the symbol (NSE tickers end in .NS).")
        sys.exit(1)

    # --- fundamentals snapshot ---
    info = ticker.info or {}
    return candles, info


def print_report(ticker_symbol, candles, info):
    name = info.get("longName") or info.get("shortName") or ticker_symbol
    currency = info.get("currency", "INR")
    bar = "=" * 64

    print(bar)
    print(f"  {name}  ({ticker_symbol})")
    print(f"  Sector: {info.get('sector', 'n/a')}   "
          f"Industry: {info.get('industry', 'n/a')}")
    print(bar)

    # ---- Price action over the window ----
    first = candles.iloc[0]
    last = candles.iloc[-1]
    period_return = (last["Close"] / first["Close"] - 1) * 100
    hi = candles["High"].max()
    lo = candles["Low"].min()
    avg_vol = candles["Volume"].mean()
    start_date = candles.index[0].date()
    end_date = candles.index[-1].date()

    print("\nPRICE (6-month daily candles)")
    print(f"  Window         : {start_date}  ->  {end_date}  "
          f"({len(candles)} trading days)")
    print(f"  Close (latest) : {fmt(last['Close'], prefix=currency + ' ')}")
    print(f"  Period change  : {fmt(period_return, suffix=' %')}")
    print(f"  6M High / Low  : {fmt(hi)}  /  {fmt(lo)}")
    print(f"  Avg daily vol  : {fmt(avg_vol, dp=0)} shares")

    print("\n  Last 5 sessions (O / H / L / C / Vol):")
    tail = candles.tail(5)
    for idx, row in tail.iterrows():
        print(f"    {idx.date()}  "
              f"{row['Open']:>9.2f}  {row['High']:>9.2f}  "
              f"{row['Low']:>9.2f}  {row['Close']:>9.2f}  "
              f"{int(row['Volume']):>12,}")

    # ---- Fundamentals snapshot ----
    print("\nFUNDAMENTALS (yfinance .info snapshot)")
    print(f"  Market cap     : {crore(info.get('marketCap'))}")
    print(f"  Trailing P/E   : {fmt(info.get('trailingPE'))}")
    print(f"  Forward P/E    : {fmt(info.get('forwardPE'))}")
    print(f"  Price/Book     : {fmt(info.get('priceToBook'))}")
    print(f"  EPS (trailing) : {fmt(info.get('trailingEps'))}")
    print(f"  Div yield      : {fmt((info.get('dividendYield') or 0), suffix=' %')}")
    print(f"  ROE            : {fmt((info.get('returnOnEquity') or 0) * 100, suffix=' %')}")
    print(f"  Profit margin  : {fmt((info.get('profitMargins') or 0) * 100, suffix=' %')}")
    print(f"  Debt/Equity    : {fmt(info.get('debtToEquity'))}")
    print(f"  52W High / Low : {fmt(info.get('fiftyTwoWeekHigh'))}  /  "
          f"{fmt(info.get('fiftyTwoWeekLow'))}")
    print(f"  Total revenue  : {crore(info.get('totalRevenue'))}")

    print("\n" + bar)
    print("  Phase 2 OK. Data pulled with no agents involved.")
    print(bar)


def main():
    ticker_symbol = sys.argv[1] if len(sys.argv) > 1 else "BEL.NS"
    candles, info = fetch(ticker_symbol)
    print_report(ticker_symbol, candles, info)


if __name__ == "__main__":
    main()
