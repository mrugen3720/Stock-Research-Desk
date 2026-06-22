"""The shared brain every chat bot calls — independent of any platform.

"Channel-agnostic" means this file knows NOTHING about Discord or Telegram. It
does the real work — take your text, find the stock, run the whole desk, hand
back a tidy result — and each bot is just a thin "skin" that calls this and
formats the answer for its own app.

WHY: write the hard logic once. Adding a new channel (WhatsApp, Slack...) then
means writing a small adapter, not re-doing the pipeline.

The result is always a dict with `ok`:
  ok=True  -> has ticker, name, dossier, verdict
  ok=False -> has a friendly `error` string
It never raises, so the calling bot can stay simple.
"""

from .. import resolve
from ..graph.desk import run_desk


def run_for_query(query: str, model_overrides: dict | None = None) -> dict:
    """Resolve a free-text query and run the desk.

    `model_overrides` (optional) maps a role to a model id for this run only.

    Returns a dict with:
      ok=True  -> {ok, query, ticker, name, dossier, verdict}
      ok=False -> {ok, query, error, [ticker, name]}
    Never raises — adapters can rely on the dict shape.
    """
    query = (query or "").strip()
    if not query:
        return {"ok": False, "query": query, "error": "Please send a stock name or ticker."}

    try:
        ticker, name = resolve.resolve(query)
    except Exception:
        return {
            "ok": False,
            "query": query,
            "error": (
                f"Couldn't find an NSE stock matching '{query}'. "
                "Try a name like 'tata steel' or a ticker like RELIANCE.NS."
            ),
        }

    try:
        final = run_desk(ticker, model_overrides=model_overrides)
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "query": query,
            "ticker": ticker,
            "name": name,
            "error": f"Analysis failed for {ticker} ({name}): {type(exc).__name__}: {exc}",
        }

    return {
        "ok": True,
        "query": query,
        "ticker": ticker,
        "name": name,
        "dossier": final["dossier"],
        "verdict": final["verdict"],
    }
