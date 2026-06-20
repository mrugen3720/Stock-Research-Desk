"""The Judge. Reads the dossier + the full Bull/Bear debate and rules.

Outputs a strict Verdict: direction, conviction, the one-line thesis, the single
invalidator, and a concrete price level where the idea is dead. No order is ever
placed — this is a recommendation for a human.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from ..llm import build_structured_llm
from ..schema import Verdict
from . import render

SYSTEM_PROMPT = (
    "You are the JUDGE on an equity research desk for Indian (NSE) stocks. You have "
    "the workers' dossier and a two-round Bull vs Bear debate. Weigh both sides on "
    "the strength of evidence, not rhetoric. Reward arguments grounded in the "
    "dossier's numbers; discount unsupported claims and ones successfully rebutted.\n\n"
    "Deliver a verdict:\n"
    "- direction: long, short, or avoid. Choose 'avoid' when the edge is unclear "
    "or the debate is a genuine stalemate.\n"
    "- conviction: 0-1, honest about how decisive the evidence is.\n"
    "- thesis: ONE sentence with the call and its core reason.\n"
    "- invalidator: the SINGLE most important thing that would prove you wrong.\n"
    "- dead_price: a specific INR price level at which the idea is dead. For a long "
    "it sits below the current price (a level that breaks the bull case); for a "
    "short, above it; for avoid, the level that would force a rethink. Anchor it to "
    "the current price and the technicals (support/resistance, ATR, 52w levels).\n"
    "- dead_price_rationale: why that level kills the thesis.\n\n"
    "Never recommend placing an order automatically; a human approves all trades."
)


def judge(dossier: dict, transcript: list[dict]) -> Verdict:
    human = (
        f"DOSSIER:\n{render.dossier_to_text(dossier)}\n\n"
        f"DEBATE:\n{render.transcript_to_text(transcript)}\n\n"
        "Now issue your verdict."
    )
    llm = build_structured_llm(Verdict)
    return llm.invoke(
        [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=human)]
    )
