"""THE CONDUCTOR — the whole research desk wired together with LangGraph.

This is the heart of the project and the actual subject ("multi-agent
orchestration"). If the workers/agents are the musicians, this file is the
conductor that tells them when to play.

The full flow (each box below is a "node" = a Python function further down):

    START
      -> supervisor          (manager: picks which workers to run; no analysis)
      -> [technicals | fundamentals | news]   (3 workers, ALL AT ONCE via `Send`)
      -> bundle              (glue the 3 reports into one "dossier" + add price)
      -> bull -> bear        (debate round 1)
      -> (loop back to bull for round 2, then...)
      -> judge               (reads everything, issues the Verdict)
    END

KEY LANGGRAPH IDEAS USED HERE (see GLOSSARY.md):
  - State    : a shared "clipboard" (DeskState) passed between nodes.
  - Node     : one step = one function that reads the state and returns updates.
  - Edge     : an arrow "after this node, go to that one".
  - Send     : launches the 3 workers in PARALLEL instead of one-by-one.
  - Reducer  : merges updates when parallel nodes write the same field at once.

Run it directly to watch every step print:
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

from .. import config, data
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
    """Reducer: merge worker reports from parallel branches into one dict.

    The 3 workers finish at roughly the same time and each wants to add its
    report to `reports`. Without a reducer, the last one would overwrite the
    others. This says "when two updates arrive, MERGE them" so all 3 survive.
    """
    merged = dict(left or {})
    merged.update(right or {})
    return merged


# DeskState is the shared "clipboard" carried through the whole graph. Every node
# receives it, reads what it needs, and returns the fields it wants to add/change.
# `total=False` just means "not every field has to be present at every step".
class DeskState(TypedDict, total=False):
    ticker: str                          # the stock, e.g. "BEL.NS" (set at entry)
    models: dict                         # optional per-role model overrides
    plan: list[str]                      # which workers the supervisor chose
    worker: str                          # per-branch: which worker this Send runs
    # `Annotated[..., reducer]` attaches the merge rule explained above. These two
    # fields get written by parallel/repeated nodes, so they need reducers:
    reports: Annotated[dict, merge_reports]     # name -> report (parallel workers)
    transcript: Annotated[list, operator.add]   # debate turns (appended each round)
    dossier: dict                        # the bundled reports + current price
    rounds_done: int                     # how many Bull+Bear rounds are finished
    verdict: dict                        # the Judge's final call


def _model(state: DeskState, role: str) -> str:
    """Effective model for a role: a per-run override wins, else the .env config."""
    return (state.get("models") or {}).get(role) or config.model_for(role)


def supervisor(state: DeskState) -> DeskState:
    """Decide which workers to dispatch. No analysis happens here."""
    plan = list(WORKER_REGISTRY.keys())
    print(f"[supervisor] ticker={state['ticker']} -> dispatching {plan}")
    models = {role: _model(state, role)
              for role in (*plan, "bull", "bear", "judge")}
    print(f"[supervisor] models: {models}")
    return {"plan": plan}


def dispatch(state: DeskState):
    """Conditional edge: fan out one Send per planned worker.

    The Send payload must carry `models`, since fan-out branches start from this
    payload, not the full graph state.
    """
    return [
        Send("run_worker", {
            "ticker": state["ticker"],
            "worker": name,
            "models": state.get("models", {}),
        })
        for name in state["plan"]
    ]


def run_worker(state: DeskState) -> DeskState:
    """Run a single worker (named in the Send payload) and record its report."""
    name = state["worker"]
    model = _model(state, name)
    report = WORKER_REGISTRY[name](state["ticker"], model)
    print(f"[{name}] ({model}) "
          f"stance={report.stance} confidence={report.confidence}")
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
    arg = debaters.bull(state["dossier"], state.get("transcript", []), rnd, _model(state, "bull"))
    print(f"[bull r{rnd}] {arg.splitlines()[0][:90]}...")
    return {"transcript": [{"round": rnd, "side": "bull", "text": arg}]}


def bear(state: DeskState) -> DeskState:
    """Bear debater for the current round; closes out the round counter."""
    rnd = state.get("rounds_done", 0) + 1
    arg = debaters.bear(state["dossier"], state.get("transcript", []), rnd, _model(state, "bear"))
    print(f"[bear r{rnd}] {arg.splitlines()[0][:90]}...")
    return {
        "transcript": [{"round": rnd, "side": "bear", "text": arg}],
        "rounds_done": rnd,
    }


def route_debate(state: DeskState) -> str:
    """The "fork in the road" after each debate round.

    This is a CONDITIONAL EDGE: instead of always going to the same next node,
    it returns the NAME of the next node based on the state. Here: if we haven't
    done ROUNDS (2) rounds yet, loop back to "bull"; otherwise go to "judge".
    That single line is what creates the 2-round debate loop.
    """
    return "bull" if state["rounds_done"] < ROUNDS else "judge"


def judge(state: DeskState) -> DeskState:
    """Read dossier + debate and issue the verdict."""
    jmodel = _model(state, "judge")
    verdict = judge_agent.judge(state["dossier"], state["transcript"], jmodel)
    print(f"[judge] ({jmodel}) direction={verdict.direction} "
          f"conviction={verdict.conviction} dead_price={verdict.dead_price}")
    return {"verdict": verdict.model_dump()}


def build_graph():
    """Assemble the diagram from the module docstring into a runnable graph.

    Two phases: first add every node (the boxes), then add every edge (the
    arrows). LangGraph then knows the whole flow and can execute it.
    """
    g = StateGraph(DeskState)

    # 1) The boxes — register each node function under a name.
    g.add_node("supervisor", supervisor)
    g.add_node("run_worker", run_worker)
    g.add_node("bundle", bundle)
    g.add_node("bull", bull)
    g.add_node("bear", bear)
    g.add_node("judge", judge)

    # 2) The arrows — connect the boxes in order.
    g.add_edge(START, "supervisor")                 # begin at the supervisor
    # `dispatch` returns Send objects -> fans out to run_worker once per worker,
    # all in parallel. (Conditional edge because the targets are decided at runtime.)
    g.add_conditional_edges("supervisor", dispatch, ["run_worker"])
    g.add_edge("run_worker", "bundle")              # every worker -> bundle
    # The debate: bundle -> bull -> bear -> (loop to bull OR go to judge) -> END.
    g.add_edge("bundle", "bull")
    g.add_edge("bull", "bear")
    g.add_conditional_edges("bear", route_debate, ["bull", "judge"])
    g.add_edge("judge", END)                         # the verdict is the finish line

    return g.compile()                              # turn the diagram into a runnable


def run_desk(ticker: str, model_overrides: dict | None = None) -> dict:
    """Run the desk end to end and return the final state.

    `model_overrides` maps a role (technicals/fundamentals/news/bull/bear/judge)
    to a Groq model id for this run only; unset roles use the .env config.
    """
    return build_graph().invoke({"ticker": ticker, "models": model_overrides or {}})


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
