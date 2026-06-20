"""Telegram delivery of the Judge's verdict.

Formats the verdict (plus a short dossier summary) into an HTML message and
sends it via the bot. NO order is ever placed — the message always states that
a human approves every trade.
"""

import asyncio
import html

from telegram import Bot
from telegram.constants import ParseMode

from .. import config

_DIRECTION = {
    "long": "🟢 LONG",
    "short": "🔴 SHORT",
    "avoid": "⚪ AVOID",
}


def _esc(x) -> str:
    return html.escape(str(x))


def _conviction_bar(conviction: float) -> str:
    filled = round(max(0.0, min(1.0, conviction)) * 5)
    return "▰" * filled + "▱" * (5 - filled)


def format_verdict(dossier: dict, verdict: dict) -> str:
    """Build the HTML message body for one verdict."""
    ticker = _esc(dossier.get("ticker"))
    price = dossier.get("last_price")
    direction = _DIRECTION.get(verdict["direction"], _esc(verdict["direction"]))

    # One-line stance summary from each worker.
    stances = []
    for name in sorted(dossier.get("reports", {})):
        rep = dossier["reports"][name]
        stances.append(f"{_esc(name)}: <b>{_esc(rep['stance'])}</b> ({rep['confidence']})")
    stance_line = " | ".join(stances)

    lines = [
        f"📊 <b>{ticker}</b> — research verdict",
        f"Price: <b>INR {_esc(price)}</b>",
        "",
        f"{direction}   conviction {_conviction_bar(verdict['conviction'])} "
        f"({verdict['conviction']})",
        "",
        f"<b>Thesis:</b> {_esc(verdict['thesis'])}",
        "",
        f"❌ <b>Invalidator:</b> {_esc(verdict['invalidator'])}",
        f"💀 <b>Idea dead at:</b> INR {_esc(verdict['dead_price'])}",
        f"    <i>{_esc(verdict['dead_price_rationale'])}</i>",
        "",
        f"🔎 {stance_line}",
        "",
        "<i>No order placed. Human approves all trades.</i>",
    ]
    return "\n".join(lines)


async def _send_async(token: str, chat_id: str, text: str):
    bot = Bot(token)
    await bot.send_message(
        chat_id=chat_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def send_message(text: str, chat_id: str | None = None):
    """Send raw HTML text to Telegram. Raises if token/chat id are missing."""
    token = config.TELEGRAM_BOT_TOKEN
    chat_id = chat_id or config.TELEGRAM_CHAT_ID
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env.")
    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID is not set (pass chat_id or set .env).")
    asyncio.run(_send_async(token, chat_id, text))


def deliver_verdict(dossier: dict, verdict: dict, chat_id: str | None = None):
    """Format and send one verdict."""
    send_message(format_verdict(dossier, verdict), chat_id=chat_id)
