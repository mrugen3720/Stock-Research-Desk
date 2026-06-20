"""Phase 4: the research desk as a LangGraph supervisor graph.

Flow:
    START -> supervisor -> (Send fan-out) -> run_worker[...] -> bundle -> END

The supervisor does NO analysis. It only picks which workers to dispatch and
emits a `Send` per worker. Each branch runs one worker and writes its report
into a reduced `reports` dict, so adding the other two workers in Phase 5 is
just a longer dispatch list — the wiring below does not change.

Run it directly:
    python -m src.graph.desk            # defaults to BEL.NS
    python -m src.graph.desk TCS.NS
"""

import json
import operator
import sys
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from .. import data
from ..agents import debaters, judge as judge_agent
from ..workers import fundamentals, news, technicals

# Registry of available workers: name -> callable(ticker) -> WorkerReport.
# Every name here is dispatched in parallel by the supervisor.
WORKER_REGISTRY = {
    "technicals": technicals.analyze,
    "fundamentals": fundamentals.analyze,
    "news": news.analyze,
}

# Number of Bull/Bear debate rounds before the Judge rules.
ROUNDS = 2


def merge_reports(left: dict | None, right: dict | None) -> dict:
    """Reducer: merge worker reports from parallel branches into one dict."""
    merged = dict(left or {})
    merged.update(right or {})
    return merged


class DeskState(TypedDict, total=False):
    ticker: str                          # set once at entry
    plan: list[str]                      # supervisor's chosen workers
    worker: str                          # per-branch: which worker this Send runs
    reports: Annotated[dict, merge_reports]  # name -> report dict (reduced)
    dossier: dict                        # bundled worker reports + price
    transcript: Annotated[list, operator.add]  # debate, appended each turn
    rounds_done: int                     # completed Bull+Bear rounds
    verdict: dict                        # the Judge's final call


def supervisor(state: DeskState) -> DeskState:
    """Decide which workers to dispatch. No analysis happens here."""
    plan = list(WORKER_REGISTRY.keys())
    print(f"[supervisor] ticker={state['ticker']} -> dispatching {plan}")
    return {"plan": plan}


def dispatch(state: DeskState):
    """Conditional edge: fan out one Send per planned worker."""
    return [
        Send("run_worker", {"ticker": state["ticker"], "worker": name})
        for name in state["plan"]
    ]


def run_worker(state: DeskState) -> DeskState:
    """Run a single worker (named in the Send payload) and record its report."""
    name = state["worker"]
    report = WORKER_REGISTRY[name](state["ticker"])
    print(f"[{name}] stance={report.stance} confidence={report.confidence}")
    return {"reports": {name: report.model_dump()}}


def bundle(state: DeskState) -> DeskState:
    """Collect every worker report into one dossier (with current price)."""
    dossier = {
        "ticker": state["ticker"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workers": sorted(state["reports"].keys()),
        "last_price": data.get_last_price(state["ticker"]),
        "reports": state["reports"],
    }
    print(f"[supervisor] bundled dossier from {dossier['workers']} "
          f"(price={dossier['last_price']})")
    return {"dossier": dossier}


def bull(state: DeskState) -> DeskState:
    """Bull debater for the current round."""
    rnd = state.get("rounds_done", 0) + 1
    arg = debaters.bull(state["dossier"], state.get("transcript", []), rnd)
    print(f"[bull r{rnd}] {arg.splitlines()[0][:90]}...")
    return {"transcript": [{"round": rnd, "side": "bull", "text": arg}]}


def bear(state: DeskState) -> DeskState:
    """Bear debater for the current round; closes out the round counter."""
    rnd = state.get("rounds_done", 0) + 1
    arg = debaters.bear(state["dossier"], state.get("transcript", []), rnd)
    print(f"[bear r{rnd}] {arg.splitlines()[0][:90]}...")
    return {
        "transcript": [{"round": rnd, "side": "bear", "text": arg}],
        "rounds_done": rnd,
    }


def route_debate(state: DeskState) -> str:
    """After each round: another round, or hand off to the Judge."""
    return "bull" if state["rounds_done"] < ROUNDS else "judge"


def judge(state: DeskState) -> DeskState:
    """Read dossier + debate and issue the verdict."""
    verdict = judge_agent.judge(state["dossier"], state["transcript"])
    print(f"[judge] direction={verdict.direction} "
          f"conviction={verdict.conviction} dead_price={verdict.dead_price}")
    return {"verdict": verdict.model_dump()}


def build_graph():
    """Compile the full desk graph: workers -> debate loop -> judge."""
    g = StateGraph(DeskState)
    g.add_node("supervisor", supervisor)
    g.add_node("run_worker", run_worker)
    g.add_node("bundle", bundle)
    g.add_node("bull", bull)
    g.add_node("bear", bear)
    g.add_node("judge", judge)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", dispatch, ["run_worker"])
    g.add_edge("run_worker", "bundle")
    # Debate: bundle -> bull -> bear -> (loop to bull | judge) -> END.
    g.add_edge("bundle", "bull")
    g.add_edge("bull", "bear")
    g.add_conditional_edges("bear", route_debate, ["bull", "judge"])
    g.add_edge("judge", END)
    return g.compile()


def run_desk(ticker: str) -> dict:
    """Run the desk end to end and return the final state."""
    return build_graph().invoke({"ticker": ticker})


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BEL.NS"
    print(f"=== research desk: workers -> debate -> judge on {ticker} ===\n")
    final = run_desk(ticker)

    print("\n--- DEBATE TRANSCRIPT ---")
    for turn in final["transcript"]:
        print(f"\n[Round {turn['round']} | {turn['side'].upper()}]")
        print(turn["text"])

    print("\n--- DOSSIER ---")
    print(json.dumps(final["dossier"], indent=2))

    print("\n--- VERDICT ---")
    print(json.dumps(final["verdict"], indent=2))


if __name__ == "__main__":
    main()
