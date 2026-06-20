"""Phase 7 entry point: run the desk on one or more tickers and deliver verdicts.

This is what cron calls. Each ticker runs the full graph (workers -> debate ->
judge); the verdict is printed and (unless --no-send) delivered to Telegram.

Usage:
    python -m src.run BEL.NS                 # run + deliver
    python -m src.run BEL.NS TCS.NS          # several tickers
    python -m src.run BEL.NS --no-send       # dry run, print only (no Telegram)
"""

import sys
import traceback
from datetime import datetime, timezone

from . import delivery
from .delivery import telegram
from .graph.desk import run_desk


def process(ticker: str, send: bool):
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"\n===== {ticker} @ {stamp} =====")
    final = run_desk(ticker)
    dossier, verdict = final["dossier"], final["verdict"]

    print(
        f"VERDICT {ticker}: {verdict['direction']} "
        f"(conviction {verdict['conviction']}), dead@ {verdict['dead_price']}"
    )

    if send:
        channel = delivery.deliver_verdict(dossier, verdict)
        print(f"-> delivered via {channel}")
    else:
        print("-> --no-send: skipped delivery. Telegram message preview:\n")
        print(telegram.format_verdict(dossier, verdict))


def main():
    args = [a for a in sys.argv[1:] if a != "--no-send"]
    send = "--no-send" not in sys.argv[1:]
    tickers = args or ["BEL.NS"]

    failures = 0
    for ticker in tickers:
        try:
            process(ticker, send)
        except Exception:
            failures += 1
            print(f"!! FAILED on {ticker}:")
            traceback.print_exc()

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
