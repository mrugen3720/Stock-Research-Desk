"""The Bull and Bear debaters.

Each reads the dossier (and the debate so far) and argues its side in prose.
Round 1 is an opening case. Round 2 must single out the opponent's weakest
claim and attack it directly, then reinforce its own thesis.
"""

from langchain_core.messages import HumanMessage, SystemMessage

from .. import config
from ..llm import build_chat_llm
from . import render

_SIDE = {
    "bull": ("BULL", "the long (bullish) case", "BEAR"),
    "bear": ("BEAR", "the short (bearish) case", "BULL"),
}

_SYSTEM = (
    "You are the {label} analyst in an equity research debate on an Indian (NSE) "
    "stock. You argue {case}. Ground every point in the dossier's worker findings "
    "(technicals, fundamentals, news) — cite specific numbers. Be sharp and "
    "concise (max ~180 words). Do not invent data. Acknowledge you are arguing one "
    "side on purpose; the Judge will weigh both."
)

_ROUND1 = (
    "ROUND 1. Make your strongest opening case for {case}. Lead with your two or "
    "three best points from the dossier."
)

_ROUND2 = (
    "ROUND 2. Read the {opp}'s argument below. Identify their SINGLE WEAKEST claim, "
    "name it explicitly, and attack it with evidence from the dossier. Then restate "
    "why your thesis still holds.\n\nDEBATE SO FAR:\n{transcript}"
)


def argue(side: str, dossier: dict, transcript: list[dict], rnd: int) -> str:
    label, case, opp = _SIDE[side]
    system = _SYSTEM.format(label=label, case=case)

    if rnd == 1:
        task = _ROUND1.format(case=case)
    else:
        task = _ROUND2.format(opp=opp, transcript=render.transcript_to_text(transcript))

    human = (
        f"DOSSIER:\n{render.dossier_to_text(dossier)}\n\n"
        f"YOUR TASK:\n{task}"
    )
    llm = build_chat_llm(model=config.model_for(side))
    resp = llm.invoke([SystemMessage(content=system), HumanMessage(content=human)])
    return resp.content.strip()


def bull(dossier: dict, transcript: list[dict], rnd: int) -> str:
    return argue("bull", dossier, transcript, rnd)


def bear(dossier: dict, transcript: list[dict], rnd: int) -> str:
    return argue("bear", dossier, transcript, rnd)
