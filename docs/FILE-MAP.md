# File Map — what every file is, and why it exists

Read the [Big Guide](GUIDE.md) first for the story. This page is the reference:
each file in one short paragraph, in the order you'd naturally meet it.

Legend: 🧠 = core logic you should understand · 🔧 = helper/plumbing ·
📤 = output/delivery · 🤖 = a thing you run.

---

## The shared building blocks (`src/*.py`)

### 🧠 `src/schema.py` — the contracts
Defines the two fixed "shapes" of data: `WorkerReport` (what every worker must
return: findings/stance/confidence/sources) and `Verdict` (what the Judge
returns: direction/conviction/thesis/invalidator/dead_price). These are the
"forms everyone fills out." Built with Pydantic, which *enforces* the shape.
**Why:** so every other part of the system can trust the data looks the same.

### 🧠 `src/config.py` — the settings desk
Reads your `.env` file (API keys, model choices) and exposes them to the rest of
the code. Also holds `model_for(role)` — the function that decides which AI model
each agent uses. **Why:** one place for all settings, so secrets are never
hard-coded and models are easy to swap.

### 🧠 `src/llm.py` — the AI factory
Builds the actual connection to the AI provider. Two builders:
`build_structured_llm()` (forces strict-JSON answers — used by workers + judge)
and `build_chat_llm()` (plain prose — used by the debaters). Both try Groq first,
then fall back to NVIDIA NIM if Groq fails. **Why:** every agent gets its AI the
same way, with automatic backup.

### 🔧 `src/data.py` — the data tap
Thin wrapper around `yfinance` (Yahoo Finance). Fetches daily candles, company
info, financials, and the latest price. **Why:** one place that touches the
market-data source, so the rest of the code doesn't care where data comes from.

### 🔧 `src/indicators.py` — the chart math
Pure Python (no AI) that turns raw price candles into technical indicators:
moving averages, RSI, MACD, ATR, returns, volume trends. **Why:** so the
technicals worker reasons over *real, calculated* numbers, not AI guesses.

### 🔧 `src/fundamentals.py` — the company-numbers math
Pure Python that pulls valuation, profitability, growth, and balance-sheet
figures from Yahoo's data and formats them (Indian-style, in crore). **Why:**
same reason as indicators — give the AI real facts to read.

### 🔧 `src/news.py` — the headline fetcher
Searches DuckDuckGo for recent news (last ~2 weeks), cleans it up, and builds a
smart search query from a company name. **Why:** feeds the news worker real,
recent headlines.

### 🧠 `src/resolve.py` — the name detective
Turns whatever you type ("reliance", "tata steel", "tisco", "cdsl", "BEL") into
the correct NSE ticker (RELIANCE.NS, TATASTEEL.NS…). Uses a nickname list, then
direct-ticker checks, then Yahoo search. **Why:** so you never have to memorize
exact ticker symbols.

---

## The workers (`src/workers/`) — the three analysts

Each worker follows the **same recipe**: fetch data → compute facts in Python →
ask the LLM to read the facts and return a strict `WorkerReport`. They all expose
one function: `analyze(ticker, model=None)`.

### 🧠 `src/workers/technicals.py`
The chart analyst. Uses `indicators.py`. Reads trend, momentum, and volume; picks
a stance. **Start here** if you want to understand one worker fully — the other
two are the same pattern.

### 🧠 `src/workers/fundamentals.py`
The accountant. Uses `fundamentals.py`. Weighs valuation vs. quality (a great
company can still be a bad buy if it's too expensive).

### 🧠 `src/workers/news.py`
The journalist. Uses `news.py`. Judges whether recent headlines are net positive,
negative, or just noise.

---

## The debate team (`src/agents/`)

### 🔧 `src/agents/render.py` — the formatter
Turns the dossier (all worker reports) and the running debate into clean text
that the debaters and Judge can read in their prompts. **Why:** keep prompt
formatting in one place, not copy-pasted.

### 🧠 `src/agents/debaters.py` — Bull & Bear
One function, `argue(side, …)`, used for both sides. Round 1 = opening argument;
round 2 = "find the opponent's weakest claim and attack it." Returns prose (not
JSON). **Why:** a structured disagreement surfaces risks a single opinion would
miss.

### 🧠 `src/agents/judge.py` — the decider
Reads the dossier + the full debate and returns a strict `Verdict`: a direction
(long/short/avoid), conviction, the one thing that would prove it wrong, and a
price level where the idea is dead. **Why:** someone has to make the final,
accountable call — and weigh evidence over rhetoric.

---

## The conductor (`src/graph/`)

### 🧠 `src/graph/desk.py` — the orchestra conductor ⭐
The heart of the project. Defines the LangGraph: the shared `state`, every node
(supervisor, run_worker, bundle, bull, bear, judge), and the edges connecting
them — including the parallel `Send` fan-out and the 2-round debate loop.
`run_desk(ticker, model_overrides)` runs the whole thing. **Why:** this is
multi-agent orchestration itself — the actual subject of the project.

---

## Delivery (`src/delivery/`)

### 📤 `src/delivery/telegram.py`
Formats a verdict as a Telegram HTML message and sends it via the bot.

### 📤 `src/delivery/email.py`
Formats a verdict as a plain-text + HTML email and sends it via SMTP (Gmail-
friendly). The reliable fallback channel.

### 📤 `src/delivery/__init__.py` — the router
`deliver_verdict()` tries Telegram first, then email, and reports which one
worked (or raises if all fail). **Why:** one call delivers, with automatic
fallback.

---

## The bots (`src/bot/`)

### 🧠 `src/bot/core.py` — the channel-agnostic brain ⭐
`run_for_query(query, model_overrides)`: resolve text → run the desk → return a
tidy result dict. Knows nothing about Discord/Telegram. **Why:** every chat
channel reuses this one function; the channels are just thin skins over it.

### 🤖 `src/bot/discord_bot.py`
The Discord bot you actually use. Shows the model-picker dropdowns, runs the
desk, and replies with a colored verdict embed. Built on `core.py`.

### 🤖 `src/bot/telegram_bot.py`
The Telegram equivalent (long-polling). Same `core.py` underneath; waiting on the
India ban to lift.

---

## Top-level runnables & scripts

### 🤖 `src/run.py`
The command-line entry point and what cron calls. Accepts stock names or tickers,
resolves them, runs the desk, and delivers each verdict. Has `--no-send` (dry
run) and `-i` (interactive) modes.

### 🤖 `scripts/fetch_one.py`
The very first thing built (Phase 2): a no-AI script that just pulls and prints
data for one stock. A good sanity check that data fetching works.

### 🤖 `scripts/run_desk_cron.sh`
Shell wrapper for the scheduled job: activates the virtual environment, runs the
desk for a list of tickers, and logs the output. Pointed at by your crontab.

---

## Config & meta files

| File | What it is |
|------|-----------|
| `.env` | Your real secrets and settings. **Never committed** (gitignored). |
| `.env.example` | A blank template of `.env` so others know what to fill in. |
| `requirements.txt` | The exact list of Python libraries to install. |
| `.gitignore` | Tells git which files to never track (venv, .env, logs…). |
| `README.md` | The project's front page (setup + run commands). |
| `docs/` | This documentation. |
