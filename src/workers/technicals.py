"""Phase 3: the technicals worker. Standalone, strict JSON output.

Pipeline: fetch daily candles -> compute indicators in Python -> ask the LLM
(Groq, NIM fallback) to read ONLY those numbers and return a WorkerReport.

Run it directly:
    python -m src.workers.technicals          # defaults to BEL.NS
    python -m src.workers.technicals TCS.NS
"""

import sys

from langchain_core.messages import HumanMessage, SystemMessage

from .. import config, data, indicators
from ..llm import build_structured_llm
from ..schema import WorkerReport

WORKER_NAME = "technicals"

SYSTEM_PROMPT = (
    "You are the TECHNICALS worker on an equity research desk covering Indian "
    "(NSE) stocks. You are given a block of precomputed technical indicators for "
    "one ticker. Analyze ONLY those numbers. Do not use outside knowledge, do not "
    "invent prices, and do not reference anything not in the block.\n\n"
    "Decide a stance and confidence strictly from how the indicators line up:\n"
    "- Trend: price vs SMA20/50/200, golden/death cross.\n"
    "- Momentum: RSI(14) (>70 overbought, <30 oversold), MACD vs signal and "
    "histogram sign.\n"
    "- Location: distance from 52-week high/low, recent 1m/3m/6m returns.\n"
    "- Participation: volume vs its 20-day average.\n\n"
    "Rules for your output:\n"
    "- findings: 3-6 short bullet statements, each citing a specific number from "
    "the block.\n"
    "- stance: bullish, bearish, or neutral.\n"
    "- confidence: 0-1. When trend and momentum disagree, lower it and lean "
    "neutral; only go high when most signals point the same way.\n"
    "- sources: the indicators/data window you relied on."
)


def analyze(ticker: str, model: str | None = None) -> WorkerReport:
    """Run the full technicals pipeline for one ticker."""
    candles = data.get_daily_candles(ticker, period="1y")
    ind = indicators.compute(candles)
    block = indicators.to_prompt_block(ind)

    llm = build_structured_llm(WorkerReport, model=model or config.model_for(WORKER_NAME))
    report = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Ticker: {ticker} (NSE)\n\nIndicator block:\n{block}"
            ),
        ]
    )
    return report


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BEL.NS"
    print(f"Running {WORKER_NAME} worker on {ticker} ...\n")
    report = analyze(ticker)

    # Show it's a real, validated WorkerReport instance, then the strict JSON.
    print(f"type: {type(report).__name__} (validated)")
    print(report.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
