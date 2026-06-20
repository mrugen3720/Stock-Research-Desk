"""Phase 5: the news worker. Standalone, strict JSON output.

Pipeline: DuckDuckGo news (last 2 weeks) -> headline/snippet block -> LLM reads
ONLY those articles -> WorkerReport.

Run it directly:
    python -m src.workers.news          # defaults to BEL.NS
    python -m src.workers.news TCS.NS
"""

import sys

from langchain_core.messages import HumanMessage, SystemMessage

from .. import config, data, news
from ..llm import build_structured_llm
from ..schema import WorkerReport

WORKER_NAME = "news"

SYSTEM_PROMPT = (
    "You are the NEWS worker on an equity research desk covering Indian (NSE) "
    "stocks. You are given recent news headlines and snippets (last ~2 weeks) for "
    "one company. Assess sentiment and materiality from ONLY these articles. Do "
    "not use outside knowledge or invent stories.\n\n"
    "Judge:\n"
    "- Sentiment: are the items net positive, negative, or mixed for the stock?\n"
    "- Materiality: orders/contracts, results, guidance, regulatory or management "
    "news move the needle; routine 'stocks to watch' listicles do not.\n"
    "- Recency and repetition: several independent items on the same positive "
    "(or negative) development strengthen the read.\n\n"
    "Rules:\n"
    "- findings: 3-6 short bullets, each referencing a specific article/event.\n"
    "- stance: bullish, bearish, or neutral.\n"
    "- confidence: 0-1. If there is little/no real news or it is purely generic "
    "market chatter, use neutral with low confidence.\n"
    "- sources: the publications/headlines you relied on."
)


def analyze(ticker: str, model: str | None = None) -> WorkerReport:
    info = data.get_info(ticker)
    name = info.get("longName") or info.get("shortName") or ticker
    query = news.build_query(name, ticker)

    articles = news.fetch_recent(query, days=14)
    block = news.to_prompt_block(articles)

    llm = build_structured_llm(WorkerReport, model=model or config.model_for(WORKER_NAME))
    return llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=(
                    f"Ticker: {ticker} (NSE), company: {name}\n"
                    f"Articles found: {len(articles)}\n\n{block}"
                )
            ),
        ]
    )


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BEL.NS"
    print(f"Running {WORKER_NAME} worker on {ticker} ...\n")
    report = analyze(ticker)
    print(f"type: {type(report).__name__} (validated)")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
