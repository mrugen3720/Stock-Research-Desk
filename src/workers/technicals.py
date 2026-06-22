"""The TECHNICALS worker — our "chart analyst" AI.

NEW HERE? Read this file first. All three workers follow the SAME 3-step recipe;
once you get this one, you understand fundamentals.py and news.py too.

The recipe (see analyze() below):
    1. FETCH   real price data from Yahoo Finance.
    2. COMPUTE the indicators (RSI, moving averages...) in plain Python.
       -> We do the MATH ourselves so the AI can't invent wrong numbers.
    3. ASK     the LLM to read those real numbers and return a WorkerReport
       (the strict findings/stance/confidence/sources shape from schema.py).

Run it on its own to see one worker in action:
    python -m src.workers.technicals          # defaults to BEL.NS
    python -m src.workers.technicals TCS.NS
"""

import sys

from langchain_core.messages import HumanMessage, SystemMessage

from .. import config, data, indicators
from ..llm import build_structured_llm
from ..schema import WorkerReport

WORKER_NAME = "technicals"

# The SYSTEM_PROMPT is the AI's job description — it sets the role and the rules
# BEFORE it sees any data. Note how strict it is: "use ONLY these numbers, don't
# invent anything." That discipline is what keeps the worker trustworthy.
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
    """Run the full technicals pipeline for one ticker.

    `model` lets the caller pick which AI model to use for this run; if None we
    fall back to whatever config says this worker should use.
    """
    # STEP 1 — FETCH: one year of daily price candles from Yahoo Finance.
    candles = data.get_daily_candles(ticker, period="1y")

    # STEP 2 — COMPUTE: turn raw prices into indicators (in Python, no AI), then
    # format them as a neat text block to paste into the prompt.
    ind = indicators.compute(candles)
    block = indicators.to_prompt_block(ind)

    # STEP 3 — ASK: build the AI (forced to return a strict WorkerReport) and
    # send it two messages: the job description, then the actual numbers.
    llm = build_structured_llm(WorkerReport, model=model or config.model_for(WORKER_NAME))
    report = llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),                 # the rules
            HumanMessage(                                          # the data
                content=f"Ticker: {ticker} (NSE)\n\nIndicator block:\n{block}"
            ),
        ]
    )
    # `report` is already a validated WorkerReport object (Pydantic guaranteed
    # the shape). If the AI had answered in the wrong shape, this would've erred.
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
