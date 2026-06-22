"""The command-line front door — run the desk from a terminal (no chat app).

This is the non-bot way to use the project: from a terminal, analyze one or more
stocks and have the verdict delivered (or just printed). It's also what the
scheduled cron job calls each morning. Three handy modes: normal (run + deliver),
`--no-send` (just print, don't email/Telegram), and `-i` (interactive REPL).

Accepts free-text names OR tickers — "reliance", "tata steel", "cdsl", "BEL",
"RELIANCE.NS" all work; each is resolved to an NSE (.NS) ticker first.

Usage:
    python -m src.run BEL.NS                  # run + deliver
    python -m src.run "tata steel" reliance   # several stocks (quote multi-word names)
    python -m src.run cdsl --no-send          # dry run, print only (no delivery)
    python -m src.run -i                       # interactive: type a name, get a verdict
"""

import sys
import traceback
from datetime import datetime, timezone

from . import delivery, resolve
from .delivery import telegram
from .graph.desk import run_desk


def process(query: str, send: bool):
    """Resolve a free-text query to a ticker, run the desk, deliver the verdict."""
    ticker, name = resolve.resolve(query)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"\n===== {query!r} -> {ticker} ({name}) @ {stamp} =====")

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


def interactive(send: bool):
    """REPL: type a stock name (or ticker), get a verdict. 'quit' to exit."""
    print("Interactive desk. Type a stock name or ticker (e.g. 'tata steel', "
          "'cdsl', 'BEL'). Type 'quit' to exit.")
    while True:
        try:
            query = input("\nstock> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            return
        try:
            process(query, send)
        except Exception:
            print(f"!! FAILED on {query!r}:")
            traceback.print_exc()


def main():
    argv = sys.argv[1:]
    send = "--no-send" not in argv
    args = [a for a in argv if a not in ("--no-send", "-i", "--interactive")]

    if "-i" in argv or "--interactive" in argv:
        interactive(send)
        return

    queries = args or ["BEL.NS"]
    failures = 0
    for query in queries:
        try:
            process(query, send)
        except Exception:
            failures += 1
            print(f"!! FAILED on {query!r}:")
            traceback.print_exc()

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
