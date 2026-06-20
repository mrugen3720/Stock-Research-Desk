"""Channel-agnostic bot core: free-text query -> resolved ticker -> verdict.

Any chat adapter (Telegram now; Discord/WhatsApp later) calls `run_for_query`
and then formats the result for its platform. This keeps the resolve+desk logic
in one place, independent of the messaging channel.
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
