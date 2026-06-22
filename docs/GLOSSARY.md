# Glossary — every scary word, explained simply

Plain-English definitions for the terms used in this project. Skim it once; come
back when a word trips you up.

---

## AI / agent terms

**LLM (Large Language Model)**
The "AI brain" (like GPT or Llama). It's a program that's very good at reading
and writing text and reasoning in words. It is **not** reliable at arithmetic —
which is why we calculate numbers in plain Python and only let the LLM *interpret*
them.

**Agent**
An LLM that's been given one specific job and a set of instructions (a "system
prompt"). "The Judge agent" = the AI told to act like a judge and follow the
judge's rules. We have six agents.

**Prompt**
The text we send the LLM. A **system prompt** sets the role and rules ("You are a
technical analyst, only use the numbers given…"). A **human/user prompt** carries
the actual data ("Here are the indicators: …").

**Multi-agent orchestration**
The whole point of this project: getting *several* agents to work together in the
right order to do something one agent couldn't do alone. The "orchestration" is
the coordination logic.

**Supervisor pattern**
A specific orchestration style: one "manager" agent (the supervisor) delegates
work to specialist agents and gathers their results, but does no analysis itself.

**Structured output / strict JSON**
Forcing the LLM to answer in an exact, predefined format instead of free text. We
use it so the rest of the program can rely on the answer's shape. Enforced by
Pydantic.

**Fallback**
A backup plan. If the main AI provider (Groq) fails, the call automatically
retries on the backup (NVIDIA NIM). The user never notices.

**Temperature**
A setting (0 to ~1) controlling how "random/creative" the LLM is. We use **0** for
consistency — we want repeatable, grounded answers, not creative ones.

---

## Library / tooling terms

**LangGraph**
The library that lets us draw the multi-agent workflow as a graph of **nodes**
(steps) and **edges** (arrows), and runs them in order while passing a shared
**state** along. `src/graph/desk.py` is our graph.

**Node**
One box in the graph — a Python function that does one step (e.g. "run a worker"
or "judge").

**Edge**
An arrow between nodes — "after this node, go to that one." A **conditional edge**
chooses the next node based on the state (e.g. "another debate round, or the
Judge?").

**State**
The shared "clipboard" of data that travels through the graph. Each node can read
it and add to it. In our code it's the `DeskState` dictionary.

**Reducer**
A rule for *combining* updates when multiple nodes write to the same state field
at once. Our parallel workers all add to `reports`; the reducer merges them
instead of overwriting.

**`Send` (fan-out)**
A LangGraph feature that launches several nodes **at the same time** (in
parallel). It's how the three workers run simultaneously.

**Pydantic**
A Python library that defines and *enforces* data shapes. If data doesn't match
the defined shape, Pydantic raises an error. It guarantees our "strict JSON."

**LangChain**
The toolkit underneath that talks to LLM providers and offers helpers like
`with_structured_output` (turn an LLM into one that returns a Pydantic shape) and
`with_fallbacks` (add a backup provider).

**yfinance**
A Python library that downloads stock data from Yahoo Finance (prices, company
info, financials). Our `src/data.py` wraps it.

**ddgs (DuckDuckGo Search)**
A library to search the web/news via DuckDuckGo. Powers the news worker.

**Groq / NVIDIA NIM**
Two providers that *host* AI models behind an API. Groq is our primary (free,
fast); NIM is the fallback. Both speak the same "OpenAI-compatible" format, so
our code talks to them the same way.

**`.env`**
A plain text file holding secrets and settings (API keys, model names). It is
**gitignored** so secrets never get committed. `config.py` reads it.

**venv (virtual environment)**
An isolated Python setup for this project, so its libraries don't clash with other
projects. You "activate" it with `source venv/bin/activate`.

**cron**
The operating system's scheduler. We use it to run the desk automatically (e.g.
weekday mornings).

---

## Stock-market terms (just enough)

**NSE / ticker / `.NS`**
NSE = National Stock Exchange of India. A **ticker** is a stock's short code.
Yahoo adds `.NS` for NSE stocks (e.g. `RELIANCE.NS`, `BEL.NS`).

**Technicals**
Analysis based on price/volume *patterns* (charts), not the company's business.

**Fundamentals**
Analysis based on the company's *business* numbers (earnings, debt, valuation).

**Bullish / Bearish / Neutral**
Bullish = expecting the price to go up. Bearish = down. Neutral = no clear edge.

**Candle / OHLCV**
One day's price summary: Open, High, Low, Close, Volume. A "daily candle."

**SMA (Simple Moving Average)**
The average closing price over the last N days (e.g. SMA20 = last 20 days). Shows
the trend.

**RSI (Relative Strength Index)**
A 0–100 momentum gauge. Above ~70 = "overbought" (maybe too hot); below ~30 =
"oversold" (maybe too cold).

**MACD**
A momentum indicator comparing two moving averages; its sign hints at whether
upward or downward momentum is building.

**ATR (Average True Range)**
A measure of how much a stock typically moves in a day — i.e. its volatility.

**P/E, P/B, ROE, D/E**
Company-quality ratios: Price/Earnings (how expensive vs. profit), Price/Book,
Return on Equity (how profitably it uses shareholders' money), Debt/Equity (how
much it borrows).

**Crore**
Indian number unit = 10,000,000 (ten million). We show big rupee figures in crore
because that's how Indian investors read them.

**Verdict fields (the Judge's output)**
- *direction*: long (buy idea) / short (sell idea) / avoid (no edge).
- *conviction*: 0–1, how strong the call is.
- *invalidator*: the single thing that would prove the call wrong.
- *dead_price*: the price level at which the idea is officially dead.
