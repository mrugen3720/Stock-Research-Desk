# CLAUDE.md — project context (read me first)

This file is auto-loaded by Claude Code. It is the **entry point**; the full
reference is **[docs/MASTER.md](docs/MASTER.md)**.

## What this is

A multi-agent **stock research desk** for the Indian market (NSE). A team of AI
"analysts" research one stock, debate it, and produce a verdict delivered to chat.
It is a **learning project** about multi-agent orchestration (LangGraph supervisor
pattern). **Making money is not a goal.**

## Golden rules (invariants — never break these)

1. **No orders, ever.** The system only recommends; a human approves all trades.
   Every delivered message ends with "Human approves all trades."
2. **Secrets live in `.env`** (gitignored). Never hardcode or commit a key value.
3. **The LLM never computes numbers.** Plain Python calculates indicators/metrics
   (`src/indicators.py`, `src/fundamentals.py`); the LLM only *reasons* over them.
4. **Every worker returns the same strict shape** — `WorkerReport`
   (`findings`, `stance`, `confidence`, `sources`) from `src/schema.py`.

## Architecture & flow

```
your text -> resolve to NSE ticker (src/resolve.py)
  -> supervisor (src/graph/desk.py): fan out to 3 workers IN PARALLEL via Send
       technicals | fundamentals | news   (each returns a WorkerReport)
  -> bundle into one "dossier" (+ current price)
  -> Bull vs Bear debate, 2 rounds (src/agents/debaters.py)
  -> Judge issues a Verdict (src/agents/judge.py)
  -> deliver: Discord / email / Telegram (src/bot/, src/delivery/)
```

`src/graph/desk.py` is the conductor (the LangGraph). `src/bot/core.py` is the
channel-agnostic brain every bot calls.

## Run locally

```bash
python3 -m venv venv && source venv/bin/activate    # Windows: py -m venv venv & venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then fill in keys
python -m src.run "tata steel"        # resolve + run + deliver
python -m src.run cdsl --no-send      # run, print only (no send)
python -m src.graph.desk BEL.NS       # run the graph, print every step
python -m src.bot.discord_bot         # start the Discord bot
```

## Deployment (live)

The Discord bot runs 24/7 on an **Oracle Cloud** free VM, independent of any
laptop. Key facts:
- Reserved public IP **`129.154.246.121`**, SSH user **`ubuntu`**.
- systemd service **`stock-bot`** (auto-start on boot, auto-restart on crash).
- Update: `rsync` the project up, then `sudo systemctl restart stock-bot`.

Full runbook: [deploy/README.md](deploy/README.md) and
[docs/MASTER.md](docs/MASTER.md) § Deployment.

## Screener (`/stock_earn_money`)

A **separate** subsystem (`src/screener/`) from the debate desk: scans the Nifty
500, scores every stock with **deterministic Python factor math** (Momentum +
Trend/Technical + Quality + Value — NO LLM in the ranking path, so it's
backtestable), and returns the top 10 with **entry/stop/target levels** and
**₹ position sizing** (loss capped at `RISK_PER_TRADE_PCT` of `ACCOUNT_CAPITAL`).
- Horizon flag: `swing` (momentum/technical-weighted) or `positional` (quality/value).
- Validate before trusting: `python -m src.screener.backtest` (historical) and
  `python -m src.screener.tracker` (live paper-trade scorecard).
- **Educational only — not investment advice; no orders placed; paper-trade first.**
- Run the scan: `python -m src.screener.engine swing`. Detail: `docs/MASTER.md` § Screener.

## Models

All agents run on **Groq** (default `openai/gpt-oss-120b`), with **NVIDIA NIM**
as automatic fallback. Each agent can override its model via `.env` (`MODEL_*`),
or per-request via the **Discord model picker** dropdowns. Logic: `config.model_for(role)`.

## Secrets (names only — values are in `.env`, never committed)

`GROQ_API_KEY`, `NVIDIA_NIM_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
`DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID`, `DISCORD_MESSAGE_CONTENT`,
`EMAIL_ADDRESS`, `EMAIL_APP_PASSWORD`, `EMAIL_TO`, plus optional `GROQ_MODEL`
and per-agent `MODEL_*`. See `.env.example` for the template. **Copy the real
`.env` between machines yourself — it is not in git.**

## Conventions

- Commits: short imperative subject; end the body with
  `Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>`.
- Push: the git remote uses the SSH alias `github-personal` (authenticates as
  `mrugen3720`). Plain `git@github.com`/HTTPS may fail — see MASTER § GitHub.
- Work goes straight to `main` (no PR flow set up).

## Read more

- **[docs/MASTER.md](docs/MASTER.md)** — the exhaustive reference (everything).
- [docs/GUIDE.md](docs/GUIDE.md) — beginner tutorial (the big picture).
- [docs/FILE-MAP.md](docs/FILE-MAP.md) — what every file does.
- [docs/GLOSSARY.md](docs/GLOSSARY.md) — every term explained.
- [deploy/README.md](deploy/README.md) — server deploy runbook.

**Setting up a new machine (Windows)?** → [docs/MASTER.md](docs/MASTER.md)
§ "Windows quickstart".
