# Stock Research Desk

A learning project: a multi-agent stock research desk for the Indian market, built to
learn **LangGraph's supervisor pattern**. The subject is the Indian stock market (NSE).
**Making money is not the goal** — this never places orders. A human approves every trade.

## Architecture (target end state)

- **Supervisor** — receives a ticker, delegates, does no analysis itself.
- **Workers** (run in parallel), each returning the *same* strict JSON shape
  (`findings`, `stance`, `confidence`, `sources`):
  - **Technicals** — daily candles from yfinance.
  - **Fundamentals** — yfinance `.info` and `.financials`.
  - **News** — DuckDuckGo search via `ddgs`, last 2 weeks.
- **Bull vs Bear** — debate the bundled dossier for 2 rounds (round 2 attacks the
  opponent's weakest claim).
- **Judge** — outputs a verdict: direction, conviction, the one thing that invalidates
  the thesis, and a price level where the idea is dead.
- **Delivery** — verdict sent to Telegram. No automatic orders, ever.

## Models

Workers and debaters run on **Groq** (free, OpenAI-compatible). **NVIDIA NIM** is kept
configured as a fallback. All keys live in `.env` (never hardcoded).

## Build order

- [x] Phase 0 — project skeleton + git
- [x] Phase 1 — venv, dependencies, `.env` template
- [x] Phase 2 — plain data-fetch script for ONE ticker (no agents)
- [ ] Phase 3 — one worker agent, standalone, strict JSON output
- [ ] Phase 4 — supervisor + one worker (LangGraph)
- [ ] Phase 5 — the other two workers, in parallel
- [ ] Phase 6 — Bull/Bear debate + Judge
- [ ] Phase 7 — Telegram delivery + cron

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in your keys
```

## Phase 2 usage

```bash
source venv/bin/activate
python scripts/fetch_one.py          # defaults to BEL.NS
python scripts/fetch_one.py TCS.NS   # any NSE ticker
```
