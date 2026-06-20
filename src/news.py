"""Recent-news fetch via DuckDuckGo (ddgs), filtered to the last N days.

ddgs `timelimit` only offers d/w/m/y, so we pull a month and filter client-side
to the exact window (default 14 days = "last 2 weeks" from the brief).
"""

import re
from datetime import datetime, timedelta, timezone

from ddgs import DDGS

# Legal suffixes that make news queries too literal and return nothing.
_SUFFIXES = re.compile(
    r"\b(limited|ltd|private|pvt|inc|corp|corporation|company|co)\.?\b",
    re.IGNORECASE,
)


def build_query(name: str, ticker: str = "") -> str:
    """Turn a company name + ticker into a search-friendly news query.

    Strips legal suffixes (Limited/Ltd/...) and punctuation, then anchors with
    the bare ticker root so results stay company-specific, e.g.
    'Bharat Electronics BEL stock'.
    """
    clean = _SUFFIXES.sub("", name)
    clean = re.sub(r"[^\w\s&]", " ", clean)          # drop ()/./, etc.
    clean = re.sub(r"\s+", " ", clean).strip()
    root = ticker.split(".")[0].strip()             # BEL.NS -> BEL
    anchor = f" {root}" if root and root.lower() not in clean.lower() else ""
    return f"{clean}{anchor} stock"


def _parse_date(raw):
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def fetch_recent(query: str, days: int = 14, max_results: int = 20) -> list[dict]:
    """Return news articles from the last `days`, newest first.

    Each item: {title, source, date, url, body}. Network/parse failures return
    an empty list rather than raising — the worker treats "no news" as neutral.
    """
    try:
        raw = DDGS().news(
            query, region="in-en", timelimit="m", max_results=max_results
        )
    except Exception:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    articles = []
    for item in raw:
        dt = _parse_date(item.get("date"))
        if dt is not None and dt < cutoff:
            continue
        articles.append(
            {
                "title": item.get("title", "").strip(),
                "source": item.get("source", "").strip(),
                "date": item.get("date", ""),
                "url": item.get("url", ""),
                "body": (item.get("body", "") or "").strip(),
            }
        )

    articles.sort(key=lambda a: a["date"], reverse=True)
    return articles


def to_prompt_block(articles: list[dict]) -> str:
    if not articles:
        return "No news articles found in the window."
    lines = []
    for i, a in enumerate(articles, 1):
        date = (a["date"] or "")[:10]
        body = a["body"][:280]
        lines.append(
            f"[{i}] ({date}) {a['source']}: {a['title']}\n    {body}"
        )
    return "\n".join(lines)
