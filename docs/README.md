# Documentation

Friendly, from-scratch docs for this project. Written for someone new to the
codebase (or to coding) — lots of plain English and analogies.

**Read in this order:**

1. **[GUIDE.md](GUIDE.md)** — the big picture. What we're building, the cast of
   AI agents, and the full journey of one request from "tata steel" to a verdict.
   *Start here.*

2. **[FILE-MAP.md](FILE-MAP.md)** — every file in the project, one paragraph
   each: what it is and why it exists. Your reference when you open a file and
   think "wait, what does this one do?"

3. **[GLOSSARY.md](GLOSSARY.md)** — every technical word (LLM, LangGraph, RSI,
   Pydantic…) explained in one or two simple sentences.

After the docs, the **code itself** is commented in plain English for beginners.
A good reading path through the code:

```
src/schema.py          (the "forms" everyone fills out)
  → src/workers/technicals.py   (one complete worker, start to finish)
    → src/graph/desk.py         (the conductor that runs all six agents)
      → src/bot/core.py         (the shared brain the chat bots call)
```

For setup and run commands, see the main [../README.md](../README.md).
