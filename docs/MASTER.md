# MASTER — the everything reference

The single, exhaustive source of truth for this project: what it is, how it
works, every file, how to run it, how it's deployed, how to continue on a new
machine, and every gotcha learned the hard way. Pairs with the auto-loaded
[../CLAUDE.md](../CLAUDE.md).

> **No secret values are in this document.** Only the *names* of the environment
> variables. The real values live in `.env` (gitignored) — copy that file
> between machines yourself.

---

## 1. Overview & goal

A multi-agent **stock research desk** for the Indian market (NSE). You give it a
stock; a team of AI "analysts" research it, two of them debate it, a judge rules,
and the verdict is delivered to you in chat (Discord) or email.

It is a **learning project** about **multi-agent orchestration** using LangGraph's
supervisor pattern. The subject is the Indian market because the owner follows it.
**Making money is explicitly not the goal, and the system never places an order** —
a human approves every trade.

## 2. Architecture & the journey of one request

```
You: "tata steel"
  1. RESOLVE   -> TATASTEEL.NS                         (src/resolve.py)
  2. SUPERVISOR: dispatch 3 workers IN PARALLEL        (src/graph/desk.py)
       technicals | fundamentals | news   -> each a WorkerReport
  3. BUNDLE    -> one "dossier" + current price
  4. DEBATE    Bull r1 -> Bear r1 -> Bull r2 -> Bear r2 (src/agents/debaters.py)
  5. JUDGE     -> Verdict                                (src/agents/judge.py)
  6. DELIVER   -> Discord / email / Telegram             (src/bot/, src/delivery/)
```

Key mechanics (all in `src/graph/desk.py`):
- **Supervisor pattern** — the supervisor node only *delegates*; it does no analysis.
- **Parallel fan-out** — uses LangGraph's `Send` to launch all 3 workers at once;
  total time ≈ the slowest worker, not the sum. The `Send` payload must carry
  `models` so per-run model overrides reach the worker branches.
- **Reducer-merged `reports`** — the 3 parallel workers each write to `reports`;
  an `operator`-style merge reducer (`merge_reports`) keeps all three.
- **2-round debate loop** — a conditional edge `route_debate` loops
  `bull -> bear` until `rounds_done == ROUNDS` (2), then routes to `judge`.
  The `transcript` accumulates via an `operator.add` reducer.
- **State** — `DeskState` (a TypedDict) is the shared clipboard passed node-to-node.

Beginner tutorial version of all this: [GUIDE.md](GUIDE.md).

## 3. Complete file map (all tracked files)

**Shared building blocks (`src/`)**
| File | Purpose |
|---|---|
| `src/schema.py` | The strict data contracts: `WorkerReport` and `Verdict` (Pydantic). |
| `src/config.py` | Loads `.env`; exposes keys/models; `model_for(role)`. |
| `src/llm.py` | LLM factory: Groq primary + NIM fallback; structured vs chat builders. |
| `src/data.py` | yfinance wrapper (candles, info, financials, last price). |
| `src/indicators.py` | Pure-Python technical indicators (SMA/RSI/MACD/ATR…). |
| `src/fundamentals.py` | Pure-Python fundamentals extraction (valuation/margins…). |
| `src/news.py` | DuckDuckGo news fetch + query builder + 14-day filter. |
| `src/resolve.py` | Free-text name → NSE ticker (aliases + Yahoo search). |
| `src/run.py` | CLI entry point (used by cron); resolve → run → deliver; `-i`, `--no-send`. |

**Workers (`src/workers/`)** — same recipe: fetch → compute (Python) → LLM → `WorkerReport`.
| File | Purpose |
|---|---|
| `src/workers/technicals.py` | Chart analyst (the template worker — read first). |
| `src/workers/fundamentals.py` | Company-numbers analyst (valuation vs quality). |
| `src/workers/news.py` | Headline-sentiment analyst. |

**Debate & judge (`src/agents/`)**
| File | Purpose |
|---|---|
| `src/agents/debaters.py` | Bull & Bear; round 2 attacks the opponent's weakest claim. |
| `src/agents/judge.py` | Reads dossier + debate → strict `Verdict`. |
| `src/agents/render.py` | Formats dossier/transcript into prompt text. |

**Orchestration (`src/graph/`)**
| File | Purpose |
|---|---|
| `src/graph/desk.py` | The LangGraph: state, nodes, edges, `Send` fan-out, debate loop, `run_desk()`. |

**Delivery (`src/delivery/`)**
| File | Purpose |
|---|---|
| `src/delivery/__init__.py` | `deliver_verdict()` router: try Telegram, fall back to email. |
| `src/delivery/telegram.py` | Format + send a verdict to Telegram (push). |
| `src/delivery/email.py` | Format + send a verdict by SMTP email (push). |

**Bots (`src/bot/`)**
| File | Purpose |
|---|---|
| `src/bot/core.py` | Channel-agnostic `run_for_query(query, model_overrides)`. |
| `src/bot/discord_bot.py` | Discord bot + model-picker dropdowns (the live one). |
| `src/bot/telegram_bot.py` | Telegram bot (built; waiting on India ban). |

**Scripts & deploy**
| File | Purpose |
|---|---|
| `scripts/fetch_one.py` | Phase-2 no-AI data dump for one ticker (sanity check). |
| `scripts/run_desk_cron.sh` | Cron wrapper (venv + run + dated log). |
| `deploy/setup.sh` | One-shot server installer (venv, deps, systemd). |
| `deploy/stock-bot.service` | systemd unit for the always-on bot. |
| `deploy/requirements-server.txt` | Pinned top-level deps for the server (skips `audioop-lts`). |
| `deploy/README.md` | The server deploy runbook. |

**Docs & config**
| File | Purpose |
|---|---|
| `README.md` | Front page (setup + run). |
| `docs/GUIDE.md`, `docs/FILE-MAP.md`, `docs/GLOSSARY.md`, `docs/README.md` | Beginner docs. |
| `.env.example` | Template of every env var (no values). |
| `requirements.txt` | Full pinned deps (frozen on macOS Python 3.14). |
| `.gitignore` | Excludes `venv/`, `.env`, `__pycache__/`, `logs/`, `data/*`. |
| `data/.gitkeep`, `logs/` (untracked) | Scratch space. |
| `src/**/__init__.py` | Package markers (empty). |
| `.claude/settings.local.json` | Local Claude Code permission allowlist. |

## 4. Data contracts (`src/schema.py`)

**`WorkerReport`** (every worker returns this):
- `findings: list[str]` — 3–6 bullets, each citing a specific number.
- `stance: "bullish" | "bearish" | "neutral"`
- `confidence: float` 0–1
- `sources: list[str]`

**`Verdict`** (the Judge returns this):
- `direction: "long" | "short" | "avoid"`
- `conviction: float` 0–1
- `thesis: str` (one sentence)
- `invalidator: str` (the single thing that proves it wrong)
- `dead_price: float` (INR level where the idea is dead)
- `dead_price_rationale: str`

Pydantic **enforces** these shapes — a wrong-shaped LLM answer raises.

## 5. Models & LLM config

- **Providers:** Groq (primary, free, OpenAI-compatible) and NVIDIA NIM
  (fallback). Both via `langchain_openai.ChatOpenAI` with different base URLs.
  Fallback is automatic via `with_fallbacks` (`src/llm.py`).
- **Default model:** `GROQ_MODEL` = `openai/gpt-oss-120b` (set in `config.py`
  default and in `.env`). Fallback model: `NVIDIA_NIM_MODEL`.
- **Per-agent overrides:** `config.model_for(role)` returns a role's model,
  falling back to `GROQ_MODEL`. Roles + env vars:
  `technicals`→`MODEL_TECHNICALS`, `fundamentals`→`MODEL_FUNDAMENTALS`,
  `news`→`MODEL_NEWS`, `bull`→`MODEL_BULL`, `bear`→`MODEL_BEAR`,
  `judge`→`MODEL_JUDGE`. Blank = use `GROQ_MODEL`.
- **Per-request override:** the Discord bot shows **dropdowns** (workers /
  debaters / judge) before each run; choices flow as `model_overrides` through
  `core.run_for_query → run_desk → graph state → each agent`.
- **Builders:** workers + judge use `build_structured_llm(schema, model)`
  (forces JSON); debaters use `build_chat_llm(model)` (prose).
- **Available Groq chat models (mid-2026):** `openai/gpt-oss-120b` (default,
  deep reasoning), `llama-3.3-70b-versatile` (balanced), `llama-3.1-8b-instant`
  (fast), `openai/gpt-oss-20b`, `qwen/qwen3-32b`,
  `meta-llama/llama-4-scout-17b-16e-instruct`. List yours:
  `GET https://api.groq.com/openai/v1/models`.

## 6. Secrets & `.env`

`.env` is **gitignored**. `.env.example` is the committed template. Variable names:

| Name | What it is / where to get it |
|---|---|
| `GROQ_API_KEY` | Groq console (console.groq.com) — primary LLM. |
| `NVIDIA_NIM_API_KEY` | NVIDIA NIM — fallback LLM. |
| `DISCORD_BOT_TOKEN` | Discord Developer Portal → your app → Bot. |
| `DISCORD_GUILD_ID` | Your Discord server ID (Developer Mode → right-click server). Instant slash sync. |
| `DISCORD_MESSAGE_CONTENT` | `true` to accept plain-text msgs (needs the Message Content Intent enabled). |
| `TELEGRAM_BOT_TOKEN` | BotFather (Telegram). Built but India-blocked. |
| `TELEGRAM_CHAT_ID` | Your chat id (`getUpdates`). Currently unset → delivery falls back to email. |
| `EMAIL_ADDRESS` | Sender Gmail address. |
| `EMAIL_APP_PASSWORD` | Gmail **App Password** (not your login password; needs 2FA). |
| `EMAIL_TO` | Recipient (usually same as sender). |
| `GROQ_MODEL` | Default model for all agents (`openai/gpt-oss-120b`). |
| `MODEL_TECHNICALS` … `MODEL_JUDGE` | Optional per-agent model overrides. |

**Moving machines:** copy your `.env` across by hand (USB, password manager,
secure paste) — it is never in git. On the server, `.env` rode up via `rsync`.

## 7. Running locally

**Setup (Mac/Linux):**
```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in keys
```
**Setup (Windows, PowerShell):**
```powershell
py -m venv venv ; venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then edit .env
```
**Run modes (same on both OSes):**
```bash
python -m src.run "tata steel"        # resolve + run + deliver (email/Discord)
python -m src.run reliance cdsl       # several at once
python -m src.run cdsl --no-send      # run + print, no delivery
python -m src.run -i                  # interactive REPL
python -m src.graph.desk BEL.NS       # run the graph, print every step
python -m src.workers.technicals BEL.NS   # one worker standalone
python -m src.bot.discord_bot         # start the Discord bot
```

## 8. Discord bot

1. Create an app + bot at https://discord.com/developers/applications; copy the
   **bot token** → `DISCORD_BOT_TOKEN`.
2. Invite it (OAuth2 → URL Generator → scopes **`bot`** + **`applications.commands`**).
3. Optional: set `DISCORD_GUILD_ID` (your server id) so `/stock` appears instantly.
4. For plain-text messages (not just `/stock`): enable **Message Content Intent**
   in the portal (Bot tab) and set `DISCORD_MESSAGE_CONTENT=true`.
5. Run `python -m src.bot.discord_bot`. Use `/stock query: tata steel`, pick
   models in the dropdowns, hit Run. Long-polling = no public URL needed.

## 9. Delivery channels

- **Email** (`src/delivery/email.py`) — stdlib SMTP, Gmail App Password. The
  reliable fallback and what cron uses.
- **Telegram** (`src/delivery/telegram.py`, `src/bot/telegram_bot.py`) — built,
  but Telegram is banned in India (mid-2026) → delivery auto-falls-back to email.
- **Router** (`src/delivery/__init__.py`) — `deliver_verdict()` tries Telegram,
  then email; returns which channel worked.

## 10. Deployment (Oracle Cloud — the live setup)

**Server:** Oracle Cloud "Always Free", Mumbai region. Shape
**`VM.Standard.E2.1.Micro`** (AMD, 1 GB RAM) — the ARM `A1.Flex` (6 GB) was out
of capacity, so we used the AMD micro **+ a 2 GB swap file**. OS **Ubuntu 24.04**
(x86_64). Reserved public IP **`129.154.246.121`**, SSH user **`ubuntu`**.

**Service:** systemd unit **`stock-bot`** (`deploy/stock-bot.service`) →
auto-start on boot, auto-restart on crash. Installed by `deploy/setup.sh`, which
builds a venv and installs `deploy/requirements-server.txt` (the **top-level deps
only**, deliberately **excluding `audioop-lts`** which has no wheel on the
server's Python).

**Connect:**
```bash
ssh -i <your-key>.key ubuntu@129.154.246.121
```
**Update the bot (Mac/Linux):**
```bash
cd <project>
rsync -av --exclude venv --exclude __pycache__ --exclude .git \
  -e "ssh -i <your-key>.key" ./ ubuntu@129.154.246.121:~/stock-research-desk/
ssh -i <your-key>.key ubuntu@129.154.246.121 "sudo systemctl restart stock-bot"
```
**Update the bot (Windows)** — no rsync; use `scp` or git:
```powershell
# option A: scp the changed files
scp -i %USERPROFILE%\.ssh\<your-key>.key -r src ubuntu@129.154.246.121:~/stock-research-desk/
ssh -i %USERPROFILE%\.ssh\<your-key>.key ubuntu@129.154.246.121 "sudo systemctl restart stock-bot"
# option B (cleaner long-term): make the server a git checkout, then `git pull` + restart
```
**Operate:**
```bash
sudo systemctl status stock-bot      # is it running?
journalctl -u stock-bot -f           # live logs
sudo systemctl restart stock-bot     # after an update
```
Full step-by-step (provisioning the VM, swap, first install):
[../deploy/README.md](../deploy/README.md).

## 11. GitHub setup

- Remote: `git@github-personal:mrugen3720/Stock-Research-Desk.git` — uses an SSH
  **host alias** `github-personal` defined in `~/.ssh/config` that points at the
  `mrugen3720` key. `git push` from the project folder just works.
- **Gotcha:** the Mac's *default* SSH key authenticates as a different account
  (`mrugencmarix`) with **no push access** — so plain `git@github.com:` and HTTPS
  (without a PAT) fail. Always use the `github-personal` alias.
- **Windows:** either replicate the alias in `C:\Users\<you>\.ssh\config`:
  ```
  Host github-personal
    HostName github.com
    User git
    IdentityFile C:\Users\<you>\.ssh\<mrugen3720_key>
  ```
  or switch the remote to HTTPS and authenticate with a Personal Access Token
  (`git remote set-url origin https://github.com/mrugen3720/Stock-Research-Desk.git`).

## 12. Build history (condensed)

- **Phases 0–2:** skeleton + git, venv + deps + `.env` template, no-AI data dump.
- **Phase 3:** first worker (technicals) with strict JSON output.
- **Phase 4:** LangGraph supervisor + one worker.
- **Phase 5:** fundamentals + news workers, running in parallel (`Send`).
- **Phase 6:** Bull/Bear 2-round debate + Judge verdict.
- **Phase 7:** Telegram delivery + cron.
- **Post-build:** name resolver (`resolve.py`); email fallback channel; inbound
  Telegram bot; inbound **Discord bot** (the live channel, since Telegram is
  banned in India); per-agent configurable models; the **Discord model-picker
  dropdowns**; default model switched to `openai/gpt-oss-120b`; two beginner-docs
  passes; **Oracle Cloud deployment**; reserved public IP.

## 13. Known gotchas / lessons (don't relearn these)

- **yfinance `dividendYield` is already a percent** (e.g. `1.07` = 1.07%) — do
  NOT ×100, unlike ROE/margins which are fractions.
- **`audioop-lts`** (in `requirements.txt`, pulled by discord.py on Python 3.13+)
  has **no wheel for Python 3.12** → use `deploy/requirements-server.txt` on the
  server instead of the frozen file.
- **Oracle ARM `A1.Flex` is often "out of capacity"** in Mumbai (single AD) →
  fall back to AMD `E2.1.Micro` (1 GB) **+ 2 GB swap**.
- **macOS `chmod` "Operation not permitted" on `~/Downloads`** = the TCC privacy
  block, not a real perm issue → move the SSH key to `~/.ssh` (or grant Terminal
  Full Disk Access).
- **SSH first connect** prompts "Are you sure…(yes/no)?" — you must type **`yes`**
  (blank/Enter fails with "Host key verification failed").
- **OCI "Reserve IPv4 address" menu item reserves the PRIVATE IP** — to keep the
  *public* IP, edit the VNIC's private IP → Public IP type → **Reserved public IP**
  → select your reserved IP.
- **Reserved IP is free only while attached** to a running instance; an
  unattached reserved IP is billed. **Ephemeral** public IPs change only on
  instance stop/start (not reboots), so they're stable for an always-on bot.
- **DuckDuckGo news is fuzzy** — verdicts vary run-to-run; that's inherent, not a bug.
- **Telegram is network-blocked in India** (mid-2026) — the bot/delivery are
  built but use Discord + email meanwhile.

## 14. Windows quickstart (continue work on a Windows PC)

```powershell
# 1. clone (same GitHub account; remote uses the github-personal alias)
git clone git@github-personal:mrugen3720/Stock-Research-Desk.git
cd Stock-Research-Desk

# 2. environment
py -m venv venv ; venv\Scripts\activate
pip install -r requirements.txt

# 3. secrets — copy your .env from the other machine (NOT in git), or:
copy .env.example .env    # then paste the real values into .env

# 4. run locally
python -m src.run "tata steel" --no-send
python -m src.bot.discord_bot

# 5. reach the live server (OpenSSH ships with Windows 10/11)
ssh -i %USERPROFILE%\.ssh\<your-key>.key ubuntu@129.154.246.121
```
Claude Code on the new PC auto-loads `CLAUDE.md`, so it gets full project context
on the first message. For deep detail it reads this file.

## 15. Current status & what's pending

**Done & live:** the Discord bot runs 24/7 on the Oracle VM (reserved IP), code
is on GitHub `main`, systemd keeps it alive, email fallback works.

**Not done / open:**
- The **morning email briefing** (`scripts/run_desk_cron.sh`) is **not** deployed
  on the server (it only ran via the Mac's crontab). Adding it = a `systemd timer`
  on the VM.
- The server has **pending `apt` updates** (`sudo apt update && sudo apt upgrade -y`).
- **No GitHub auto-deploy** — updates are manual (rsync/scp + restart).
- Work goes **straight to `main`** (no PR flow).

## 15b. Screener subsystem (`src/screener/`) — `/stock_earn_money`

A quantitative trade-idea screener, **separate from the LangGraph debate desk**.
It scans the Nifty 500 and ranks stocks by **deterministic factor math** (no LLM
in the ranking path — that's what makes it backtestable and reproducible).

**Files:**
| File | Purpose |
|---|---|
| `src/screener/universe.py` | Nifty 500 constituents (niftyindices CSV, cached weekly, bundled fallback). |
| `src/screener/data_bulk.py` | Chunked `yf.download` + daily pickle cache for the whole universe. |
| `src/screener/factors.py` | Momentum (vol-adj 6m/12m), Trend/Technical, Quality (ROE/debt/margins), Value (P/E,P/B) → cross-sectional 0-100 percentile scores; horizon-weighted composite. |
| `src/screener/levels.py` | Entry zone, ATR/structure stop, 2R target, **₹ position size** (caps loss at risk% of capital). |
| `src/screener/score.py` | Final 0-100 "take this trade" score (composite + setup quality). |
| `src/screener/engine.py` | The funnel: price factors on all 500 → fundamentals on top ~120 → rank → top-N picks; caches daily. |
| `src/screener/tracker.py` | Logs every pick to `data/recommendations.csv`; resolves outcomes; live win-rate/expectancy. |
| `src/screener/backtest.py` | Point-in-time historical backtest of the momentum/technical rules. |

**Factor weights:** swing = momentum .35 / technical .35 / quality .15 / value .15;
positional = momentum .15 / technical .15 / quality .35 / value .35.

**Sizing:** `qty = floor(ACCOUNT_CAPITAL × RISK_PER_TRADE_PCT/100 / (entry − stop))`,
so one losing trade ≈ risk% of capital. Stops = `entry − k×ATR` (swing k=2,
positional k=3) or below the recent swing low; target = 2:1 (swing) / 2.5:1.

**Commands:**
```bash
python -m src.screener.engine swing        # print top 10 swing ideas
python -m src.screener.engine positional
python -m src.screener.backtest 150        # validate historically
python -m src.screener.tracker             # live paper-trade scorecard
# Discord: /stock_earn_money horizon:swing
```

**Honest limits (read before risking money):**
- A screener improves discipline/edge; it is **not** a profit guarantee.
- The backtest validates **momentum/technical only** — yfinance `.info` is
  current-only, so **quality/value factors are NOT point-in-time backtestable**.
- A first run on the example 80–150 name slice showed a *marginal* positive
  expectancy (~0.03R) with a **large (~45%) drawdown** — raw momentum is
  drawdown-prone. Treat results as a starting point to refine (regime filters,
  better entries), and **paper-trade via the tracker for weeks** before real capital.
- Config: `ACCOUNT_CAPITAL`, `RISK_PER_TRADE_PCT`, `MAX_PORTFOLIO_HEAT_PCT` in `.env`.
- All caches + the recommendations log live under `data/` (gitignored).

## 16. Command cheat-sheet

| Goal | Command |
|---|---|
| Run one stock (deliver) | `python -m src.run "tata steel"` |
| Run, no send | `python -m src.run cdsl --no-send` |
| Full graph w/ logs | `python -m src.graph.desk BEL.NS` |
| Start Discord bot | `python -m src.bot.discord_bot` |
| SSH to server | `ssh -i <key> ubuntu@129.154.246.121` |
| Server: status / logs / restart | `sudo systemctl status stock-bot` · `journalctl -u stock-bot -f` · `sudo systemctl restart stock-bot` |
| Push code | `git push origin main` (via `github-personal` alias) |
