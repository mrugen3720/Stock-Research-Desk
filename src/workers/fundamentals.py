"""Phase 5: the fundamentals worker. Standalone, strict JSON output.

Pipeline: yfinance .info + .financials -> extract metrics in Python -> LLM reads
ONLY those numbers -> WorkerReport.

Run it directly:
    python -m src.workers.fundamentals          # defaults to BEL.NS
    python -m src.workers.fundamentals TCS.NS
"""

import sys

from langchain_core.messages import HumanMessage, SystemMessage

from .. import config, data, fundamentals
from ..llm import build_structured_llm
from ..schema import WorkerReport

WORKER_NAME = "fundamentals"

SYSTEM_PROMPT = (
    "You are the FUNDAMENTALS worker on an equity research desk covering Indian "
    "(NSE) stocks. You are given a snapshot of valuation, profitability, growth, "
    "and balance-sheet metrics for one company. Analyze ONLY those numbers. Do "
    "not use outside knowledge or invent figures.\n\n"
    "Weigh the evidence:\n"
    "- Valuation: P/E, forward P/E, P/B, PEG vs the quality of the business.\n"
    "- Profitability: ROE, ROA, net/operating/gross margins.\n"
    "- Growth: revenue and earnings growth (both .info and YoY from financials).\n"
    "- Financial health: debt/equity, current & quick ratios, cash vs debt.\n"
    "- Shareholder return: dividend yield, payout ratio.\n\n"
    "Rules:\n"
    "- findings: 3-6 short bullets, each citing a specific metric value.\n"
    "- stance: bullish, bearish, or neutral. A great business at a rich valuation "
    "is not automatically bullish; weigh price against quality.\n"
    "- confidence: 0-1; lower it when signals conflict (e.g. strong ROE but "
    "stretched P/E) or when key metrics are missing (n/a).\n"
    "- sources: the metric groups you relied on."
)


def analyze(ticker: str) -> WorkerReport:
    info = data.get_info(ticker)
    financials = data.get_financials(ticker)
    metrics = fundamentals.compute(info, financials)
    block = fundamentals.to_prompt_block(metrics)

    llm = build_structured_llm(WorkerReport, model=config.model_for(WORKER_NAME))
    return llm.invoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=f"Ticker: {ticker} (NSE)\n\nFundamentals:\n{block}"
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
