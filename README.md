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

### Per-agent models

Each agent (the three workers, the two debaters, the Judge) can run on its own
Groq model. Set any of these in `.env` (blank = use `GROQ_MODEL`):

```
MODEL_TECHNICALS=
MODEL_FUNDAMENTALS=
MODEL_NEWS=
MODEL_BULL=
MODEL_BEAR=
MODEL_JUDGE=openai/gpt-oss-120b
```

The NVIDIA NIM fallback model is shared across all agents. Each desk run prints
the resolved model map, e.g. `[supervisor] models: {... 'judge': 'openai/gpt-oss-120b'}`.
List your account's models: `GET https://api.groq.com/openai/v1/models`.

## Build order

- [x] Phase 0 — project skeleton + git
- [x] Phase 1 — venv, dependencies, `.env` template
- [x] Phase 2 — plain data-fetch script for ONE ticker (no agents)
- [x] Phase 3 — one worker agent, standalone, strict JSON output
- [x] Phase 4 — supervisor + one worker (LangGraph)
- [x] Phase 5 — the other two workers, in parallel
- [x] Phase 6 — Bull/Bear debate + Judge
- [x] Phase 7 — Telegram delivery + cron

## Running the full desk

```bash
source venv/bin/activate
python -m src.graph.desk BEL.NS        # workers -> debate -> judge, prints everything
python -m src.run BEL.NS --no-send     # full pipeline, preview Telegram msg, no send
python -m src.run BEL.NS HAL.NS        # run + deliver to Telegram
```

## Telegram delivery

1. Put your bot token in `.env` as `TELEGRAM_BOT_TOKEN`.
2. Send your bot any message from your Telegram account.
3. Get your chat id:
   `https://api.telegram.org/bot<TOKEN>/getUpdates` -> `result[].message.chat.id`.
4. Put it in `.env` as `TELEGRAM_CHAT_ID`.
5. Test: `python -m src.run BEL.NS`.

No order is ever placed. Every message ends with "Human approves all trades."

## Email fallback

If Telegram delivery fails (or is unconfigured), the desk falls back to email.
`src.delivery.deliver_verdict` tries Telegram first, then email, and reports
which channel succeeded.

For Gmail: create an **App Password** (Google Account → Security → App passwords),
then in `.env`:

```
EMAIL_ADDRESS=you@gmail.com
EMAIL_APP_PASSWORD=your_16_char_app_password
EMAIL_TO=you@gmail.com
```

Defaults are `smtp.gmail.com:587` (STARTTLS); port `465` uses implicit SSL.

## Inbound Telegram bot

Chat the bot a stock name and it replies with a verdict (long polling — no public
URL needed, but Telegram must be reachable on your network):

```bash
source venv/bin/activate
python -m src.bot.telegram_bot
```

Then message the bot "tata steel", "cdsl", "BEL", etc. The resolve+desk logic
lives in `src/bot/core.py` (channel-agnostic), so a Discord/WhatsApp adapter can
reuse it.

## Inbound Discord bot (works in India today)

Telegram is banned in India as of mid-2026; Discord is not, and (like Telegram
polling) needs no public URL. Same desk, different channel.

Setup:
1. Create an app + bot at https://discord.com/developers/applications, copy the
   **bot token** into `.env` as `DISCORD_BOT_TOKEN`.
2. Invite the bot to your server (OAuth2 URL with the `bot` and
   `applications.commands` scopes).
3. (Optional) set `DISCORD_GUILD_ID` to your server id so `/stock` appears
   instantly.
4. Run it:

```bash
source venv/bin/activate
python -m src.bot.discord_bot
```

Then type `/stock query: tata steel` in your server. To accept plain-text
messages too (e.g. just typing "cdsl"), enable the **Message Content Intent** in
the Developer Portal and set `DISCORD_MESSAGE_CONTENT=true`.

## Scheduled runs (cron)

`scripts/run_desk_cron.sh` activates the venv, runs the tickers in its `TICKERS`
array (default `BEL.NS HAL.NS`), and appends to `logs/desk-YYYY-MM-DD.log`.

Installed crontab entry (weekdays 08:30 IST, pre-market):

```
30 8 * * 1-5 "/path/to/scripts/run_desk_cron.sh" # stock-research-desk
```

On macOS, the `cron` daemon may need **Full Disk Access** (System Settings ->
Privacy & Security) to run successfully.

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
