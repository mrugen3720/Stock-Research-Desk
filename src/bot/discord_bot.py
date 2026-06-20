"""Inbound Discord bot: chat a stock name, get a verdict back.

A thin adapter over the channel-agnostic `core.run_for_query`. Discord uses a
gateway (outbound) connection, so — like Telegram polling — it needs no public
URL and works behind a home network. Unlike Telegram, Discord is not banned in
India, so this is the testable-today channel.

Two ways to ask:
  - /stock <query>   slash command — works out of the box, no special intents.
  - plain text       only if you enable the Message Content Intent in the Discord
                     Developer Portal AND set DISCORD_MESSAGE_CONTENT=true.

Run it:
    python -m src.bot.discord_bot
"""

import asyncio

import discord
from discord import app_commands

from .. import config
from . import core

_COLOR = {"long": 0x2ECC71, "short": 0xE74C3C, "avoid": 0x95A5A6}
_LABEL = {"long": "🟢 LONG", "short": "🔴 SHORT", "avoid": "⚪ AVOID"}


def _clip(text: str, limit: int = 1024) -> str:
    text = str(text)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _guild_id():
    """Parse DISCORD_GUILD_ID to an int, or None (e.g. blank or a placeholder)."""
    raw = config.DISCORD_GUILD_ID
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        print(
            f"[discord] DISCORD_GUILD_ID={raw!r} is not a numeric id; "
            "falling back to global command sync."
        )
        return None


def build_embed(result: dict) -> discord.Embed:
    """Render a successful verdict result as a Discord embed."""
    v, d = result["verdict"], result["dossier"]
    direction = v["direction"]

    embed = discord.Embed(
        title=f"{d['ticker']} — {_LABEL.get(direction, direction)}",
        description=_clip(v["thesis"], 4096),
        color=_COLOR.get(direction, 0x95A5A6),
    )
    embed.add_field(name="Price", value=f"INR {d.get('last_price')}", inline=True)
    embed.add_field(name="Conviction", value=str(v["conviction"]), inline=True)
    embed.add_field(name="Name", value=_clip(result.get("name", d["ticker"]), 256), inline=True)
    embed.add_field(name="❌ Invalidator", value=_clip(v["invalidator"]), inline=False)
    embed.add_field(
        name="💀 Idea dead at",
        value=_clip(f"INR {v['dead_price']} — {v['dead_price_rationale']}"),
        inline=False,
    )
    stances = " | ".join(
        f"{n}: {d['reports'][n]['stance']} ({d['reports'][n]['confidence']})"
        for n in sorted(d["reports"])
    )
    embed.add_field(name="🔎 Workers", value=_clip(stances), inline=False)
    embed.set_footer(text="No order placed. Human approves all trades.")
    return embed


def build_client() -> discord.Client:
    intents = discord.Intents.default()
    if config.DISCORD_MESSAGE_CONTENT:
        intents.message_content = True

    client = discord.Client(intents=intents)
    tree = app_commands.CommandTree(client)

    @client.event
    async def on_ready():
        # Sync slash commands: instantly to a guild if given, else globally.
        gid = _guild_id()
        if gid is not None:
            guild = discord.Object(id=gid)
            tree.copy_global_to(guild=guild)
            await tree.sync(guild=guild)
            print(f"Discord bot ready as {client.user}. /stock synced to guild {gid}.")
        else:
            await tree.sync()
            print(
                f"Discord bot ready as {client.user}. /stock synced globally "
                "(can take up to ~1 hour to appear)."
            )

    @tree.command(name="stock", description="Research an NSE stock (name or ticker).")
    @app_commands.describe(query="e.g. tata steel, reliance, cdsl, BEL")
    async def stock(interaction: discord.Interaction, query: str):
        # Desk run is slow; defer to get past Discord's 3s response deadline.
        await interaction.response.defer(thinking=True)
        result = await asyncio.to_thread(core.run_for_query, query)
        if result["ok"]:
            await interaction.followup.send(embed=build_embed(result))
        else:
            await interaction.followup.send("⚠️ " + result["error"])

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user or not config.DISCORD_MESSAGE_CONTENT:
            return
        content = (message.content or "").strip()
        if not content or content.startswith("/"):
            return
        async with message.channel.typing():
            notice = await message.reply(f"🔎 Researching **{content}**… ~1 min.")
            result = await asyncio.to_thread(core.run_for_query, content)
        if result["ok"]:
            await notice.edit(content=None, embed=build_embed(result))
        else:
            await notice.edit(content="⚠️ " + result["error"])

    return client


def main():
    if not config.DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN not set in .env.")
    print("Discord bot starting. Press Ctrl+C to stop.")
    build_client().run(config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
