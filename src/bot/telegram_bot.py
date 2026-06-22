"""The Telegram chat bot — you message it a stock name, it replies a verdict.

"Inbound" = it LISTENS for your messages (the opposite of src/delivery/telegram.py,
which only pushes out finished verdicts). It's a thin skin over the shared brain
`core.run_for_query` — it just receives text and formats the reply.

How it listens: "long polling" means the bot keeps asking Telegram "any new
messages?" — it dials OUT, so it works behind your home Wi-Fi with no public web
address. (Currently waiting on the India Telegram ban to lift; use the Discord
bot meanwhile.) The slow desk run is pushed to a background thread
(asyncio.to_thread) so the bot doesn't freeze while it works.

Run it:
    python -m src.bot.telegram_bot
"""

import asyncio
import html

from telegram import Update
from telegram.constants import ChatAction, ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .. import config
from ..delivery import telegram as tg_fmt
from . import core

WELCOME = (
    "📈 <b>Stock Research Desk</b>\n\n"
    "Send me an Indian (NSE) stock — a name or a ticker. Examples:\n"
    "• <code>tata steel</code>\n• <code>reliance</code>\n• <code>cdsl</code>\n"
    "• <code>BEL</code>\n\n"
    "I'll run technicals, fundamentals and news through a Bull/Bear debate and a "
    "Judge, then send a verdict.\n\n"
    "<i>No orders are ever placed. You approve all trades.</i>"
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME, parse_mode=ParseMode.HTML)


async def handle_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = (update.message.text or "").strip()
    if not query:
        return

    await update.message.chat.send_action(ChatAction.TYPING)
    notice = await update.message.reply_text(
        f"🔎 Researching <b>{html.escape(query)}</b>… this takes ~1 minute.",
        parse_mode=ParseMode.HTML,
    )

    # The desk run is blocking + slow; keep the event loop free.
    result = await asyncio.to_thread(core.run_for_query, query)

    if result["ok"]:
        text = tg_fmt.format_verdict(result["dossier"], result["verdict"])
    else:
        text = "⚠️ " + html.escape(result["error"])

    await context.bot.edit_message_text(
        chat_id=notice.chat_id,
        message_id=notice.message_id,
        text=text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


def build_application() -> Application:
    if not config.TELEGRAM_BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN not set in .env.")
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler(["start", "help"], start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_query))
    return app


def main():
    app = build_application()
    print("Telegram bot starting (long polling). Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
