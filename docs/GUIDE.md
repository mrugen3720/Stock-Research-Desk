# The Big Guide (start here)

This is a friendly, from-scratch tour of the project. No prior knowledge assumed.
If a word looks scary, check the [Glossary](GLOSSARY.md). For a quick "what is
each file" lookup, see the [File Map](FILE-MAP.md).

---

## 1. What are we building, in one sentence?

> A team of small AI "analysts" that research a single Indian stock, argue about
> it, and hand you a final verdict on your phone — **without ever placing a trade.**

Think of it like a tiny **research desk** at an investment firm, except every
seat is filled by an AI instead of a person. You hand them a stock ("Tata
Steel"), they go to work, and a one-page verdict comes back.

**Important:** this is a *learning project*. The goal is to learn how to make
several AI agents work together (called **multi-agent orchestration**). Making
money is explicitly **not** the goal, and the system never buys or sells anything.

---

## 2. The cast of characters (the "agents")

An **agent** here just means "an AI given one job and a clear set of
instructions." We have six of them, plus a manager.

| Role | Real-world job it imitates | What it actually does |
|------|----------------------------|-----------------------|
| **Supervisor** | The desk manager | Hands the stock to the workers. Does **no** analysis itself. |
| **Technicals worker** | Chart analyst | Looks at price patterns (moving averages, RSI, MACD…). |
| **Fundamentals worker** | Accountant | Looks at the company's numbers (P/E, profit, debt…). |
| **News worker** | Journalist | Reads the last 2 weeks of headlines. |
| **Bull** | The optimist | Argues why you SHOULD buy. |
| **Bear** | The pessimist | Argues why you should NOT. |
| **Judge** | The boss who decides | Reads the debate and gives the final call. |

The three workers each produce a small report. The Bull and Bear **debate** over
those reports for two rounds. The Judge reads everything and rules.

---

## 3. The journey of one request (the whole story)

Let's follow what happens when you type `tata steel` into Discord.

```
You: "tata steel"
        │
        ▼
1. RESOLVE   "tata steel" ──► TATASTEEL.NS        (figure out the real ticker)
        │
        ▼
2. SUPERVISOR  splits the work, sends it to 3 workers AT THE SAME TIME
        │
        ├──► Technicals worker  ─┐
        ├──► Fundamentals worker ─┤  (run in parallel — all at once)
        └──► News worker         ─┘
        │
        ▼
3. BUNDLE    glue the 3 reports into one "dossier" (+ today's price)
        │
        ▼
4. DEBATE    Bull argues ► Bear argues ► (round 2) Bull rebuts ► Bear rebuts
        │
        ▼
5. JUDGE     reads the dossier + debate ──► VERDICT
        │
        ▼
6. DELIVER   the verdict goes back to you (Discord / email / Telegram)
```

Every step above is a real piece of code. Here's where each lives:

1. **Resolve** → [`src/resolve.py`](../src/resolve.py)
2–5. **Supervisor → workers → debate → judge** → all orchestrated in
   [`src/graph/desk.py`](../src/graph/desk.py)
6. **Deliver** → [`src/delivery/`](../src/delivery/) and the bots in
   [`src/bot/`](../src/bot/)

---

## 4. The one rule every worker obeys: the "strict shape"

This is the most important idea in the whole project, so read it twice.

Every worker — no matter what it analyzes — must answer in the **exact same
format**. We call it the **strict JSON shape**, and it lives in
[`src/schema.py`](../src/schema.py):

```python
findings    # a list of short bullet points, each citing a real number
stance      # one of: "bullish", "bearish", "neutral"
confidence  # a number from 0 to 1 (how sure it is)
sources     # what the answer is based on
```

**Why force everyone to speak the same language?** Because the Bull, Bear, and
Judge that come later don't want three differently-shaped reports. If everyone
answers in the same shape, the rest of the system can treat all workers
identically. It's like making every analyst fill out the **same one-page form** —
the boss can then read them all the same way.

We enforce this with a tool called **Pydantic** (see Glossary). If the AI tries
to answer in the wrong shape, Pydantic rejects it. So "strict" is a real
guarantee, not a polite request.

---

## 5. Where do the numbers come from? (LLMs don't do math)

A subtle but crucial design choice: **the AI never calculates the numbers.**

Large Language Models (LLMs — the "brains" like GPT) are great at *reasoning with
words* but unreliable at *arithmetic*. They can confidently invent a wrong
number. That's dangerous for a finance tool.

So we split the job:

- **Plain Python** fetches and calculates the hard facts (price, RSI, P/E, etc.)
  → see [`indicators.py`](../src/indicators.py), [`fundamentals.py`](../src/fundamentals.py),
  [`news.py`](../src/news.py).
- **The LLM** only *reads those real numbers* and *reasons* about them (bullish?
  bearish? how confident?).

So when the technicals worker says "RSI is 58", that 58 was computed by Python
from real price data — the AI just interpreted it. This keeps the AI honest.

---

## 6. What is LangGraph and why use it?

When you have one AI call, you just... call it. But here we have **six**, some
running at the same time, some depending on each other (the Judge can't run
before the debate). Coordinating that by hand gets messy fast.

**LangGraph** is a library for drawing that coordination as a **graph** — boxes
(steps) connected by arrows (what runs next). Our graph looks like:

```
START → supervisor → [3 workers in parallel] → bundle
      → bull → bear → (loop back for round 2?) → judge → END
```

Each box is a Python function called a **node**. The arrows are **edges**.
LangGraph runs the boxes in the right order and carries a shared clipboard of
data (called the **state**) from box to box. All of this is set up in
[`src/graph/desk.py`](../src/graph/desk.py) — that file *is* the diagram above,
written in code.

Two LangGraph tricks worth knowing:

- **Parallel fan-out (`Send`)** — the supervisor uses a feature called `Send` to
  launch all three workers *at once* instead of one after another. That's why a
  run takes "as long as the slowest worker," not "the sum of all three."
- **The loop** — after Bear speaks, a small function checks "have we done 2
  rounds yet?" If no, it loops back to Bull; if yes, it goes to the Judge. That's
  how we get a 2-round debate without copy-pasting the nodes.

---

## 7. Which AI model runs each agent?

All agents run on **Groq** (a free, fast provider of open models), with **NVIDIA
NIM** kept as a backup in case Groq is down. The default model is
`openai/gpt-oss-120b`.

The neat part: **each agent can use a different model.** You might want a fast,
cheap model for the three workers (they just summarize numbers) and a big,
smart model for the Judge (the high-stakes decision). You control this two ways:

- **Permanently** in `.env` (e.g. `MODEL_JUDGE=openai/gpt-oss-120b`).
- **Per request** in Discord — the bot pops up dropdowns so you pick models
  before each run.

The "which model" logic is tiny: `config.model_for("judge")` returns the judge's
model, falling back to the global default if you didn't set one. See
[`src/config.py`](../src/config.py) and [`src/llm.py`](../src/llm.py).

---

## 8. How the verdict reaches you (delivery)

The Judge's verdict can travel three ways, and they share one core:

- **Discord bot** ([`src/bot/discord_bot.py`](../src/bot/discord_bot.py)) — chat a
  stock name, get a verdict card. Works in India today.
- **Email** ([`src/delivery/email.py`](../src/delivery/email.py)) — the fallback;
  also used by the scheduled job.
- **Telegram** ([`src/bot/telegram_bot.py`](../src/bot/telegram_bot.py)) — built,
  but Telegram is banned in India as of mid-2026, so it waits.

All three reuse one channel-agnostic brain:
[`src/bot/core.py`](../src/bot/core.py)'s `run_for_query()`. It takes your text,
resolves it to a ticker, runs the whole desk, and returns the result. Each
channel is just a thin "adapter" that formats that result for its platform. This
is why adding a new channel is easy — the hard work is already shared.

**No order is ever placed.** Every message ends with "Human approves all trades."

---

## 9. The folder map (story → folders)

| Folder | Its job in the story |
|--------|----------------------|
| `src/` | The brains. All the real logic. |
| `src/workers/` | The three analysts (technicals, fundamentals, news). |
| `src/agents/` | The debaters (Bull/Bear) and the Judge. |
| `src/graph/` | The conductor — wires everyone together with LangGraph. |
| `src/delivery/` | Sending the verdict out (Telegram + email). |
| `src/bot/` | The chat bots you talk to (Discord, Telegram) + shared core. |
| `scripts/` | Standalone helpers (the first data test, the cron job). |
| `data/`, `logs/` | Scratch space (ignored by git). |
| `docs/` | You are here. |

The single files in `src/` (`config`, `schema`, `llm`, `data`, `indicators`,
`fundamentals`, `news`, `resolve`, `run`) are shared building blocks the folders
above use. Each is explained in the [File Map](FILE-MAP.md).

---

## 10. How to run it (cheat sheet)

```bash
# one-time
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then paste your keys

# analyze one stock from the terminal (resolves names; emails the verdict)
python -m src.run "tata steel"
python -m src.run reliance cdsl --no-send   # just print, don't send

# the interactive terminal version (type names, get verdicts)
python -m src.run -i

# run the whole graph and see every step printed
python -m src.graph.desk BEL.NS

# start the Discord bot (chat it a stock name)
python -m src.bot.discord_bot
```

When you change any code, **restart the bot** for it to take effect.

---

## 11. What to read next

- [FILE-MAP.md](FILE-MAP.md) — every file, one paragraph each, "what & why."
- [GLOSSARY.md](GLOSSARY.md) — every scary word, explained simply.
- The code itself — it's now full of plain-English comments aimed at a beginner.
  A good first read is [`src/workers/technicals.py`](../src/workers/technicals.py)
  (one complete worker) then [`src/graph/desk.py`](../src/graph/desk.py) (the
  conductor).
