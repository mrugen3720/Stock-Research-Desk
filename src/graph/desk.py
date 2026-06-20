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
import sys
from datetime import datetime, timezone
from typing import Annotated, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from ..workers import technicals

# Registry of available workers: name -> callable(ticker) -> WorkerReport.
# Phase 5 adds "fundamentals" and "news" here.
WORKER_REGISTRY = {
    "technicals": technicals.analyze,
}


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
    dossier: dict                        # final bundle handed downstream


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
    """Collect every worker report into one dossier."""
    dossier = {
        "ticker": state["ticker"],
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "workers": sorted(state["reports"].keys()),
        "reports": state["reports"],
    }
    print(f"[supervisor] bundled dossier from {dossier['workers']}")
    return {"dossier": dossier}


def build_graph():
    """Compile the supervisor graph."""
    g = StateGraph(DeskState)
    g.add_node("supervisor", supervisor)
    g.add_node("run_worker", run_worker)
    g.add_node("bundle", bundle)

    g.add_edge(START, "supervisor")
    g.add_conditional_edges("supervisor", dispatch, ["run_worker"])
    g.add_edge("run_worker", "bundle")
    g.add_edge("bundle", END)
    return g.compile()


def run_desk(ticker: str) -> dict:
    """Run the desk end to end and return the dossier."""
    final = build_graph().invoke({"ticker": ticker})
    return final["dossier"]


def main():
    ticker = sys.argv[1] if len(sys.argv) > 1 else "BEL.NS"
    print(f"=== research desk (supervisor + workers) on {ticker} ===\n")
    dossier = run_desk(ticker)
    print("\n--- DOSSIER ---")
    print(json.dumps(dossier, indent=2))


if __name__ == "__main__":
    main()
