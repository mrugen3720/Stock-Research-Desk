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


# --- Interactive model picker -------------------------------------------------

# (label, model id). "__default__" means "use the .env config for that role".
MODEL_CHOICES = [
    ("Default (.env)", "__default__"),
    ("llama-3.3-70b-versatile", "llama-3.3-70b-versatile"),
    ("llama-3.1-8b-instant (fast)", "llama-3.1-8b-instant"),
    ("gpt-oss-120b (big reasoning)", "openai/gpt-oss-120b"),
    ("gpt-oss-20b", "openai/gpt-oss-20b"),
    ("qwen3-32b", "qwen/qwen3-32b"),
    ("llama-4-scout-17b", "meta-llama/llama-4-scout-17b-16e-instruct"),
]

# Which agent roles each dropdown controls.
_GROUP_ROLES = {
    "workers": ["technicals", "fundamentals", "news"],
    "debaters": ["bull", "bear"],
    "judge": ["judge"],
}


class _ModelSelect(discord.ui.Select):
    """One dropdown that sets the model for a group of agents."""

    def __init__(self, group: str, placeholder: str, row: int):
        self.group = group
        options = [
            discord.SelectOption(label=label, value=value, default=(i == 0))
            for i, (label, value) in enumerate(MODEL_CHOICES)
        ]
        super().__init__(placeholder=placeholder, options=options,
                         min_values=1, max_values=1, row=row)

    async def callback(self, interaction: discord.Interaction):
        self.view.selections[self.group] = self.values[0]
        for opt in self.options:                 # keep the pick visibly selected
            opt.default = opt.value == self.values[0]
        await interaction.response.edit_message(view=self.view)


class ModelPicker(discord.ui.View):
    """Dropdowns for workers / debaters / judge, plus a Run button."""

    def __init__(self, query: str, user_id: int):
        super().__init__(timeout=180)
        self.query = query
        self.user_id = user_id
        self.selections = {g: "__default__" for g in _GROUP_ROLES}
        self.add_item(_ModelSelect("workers", "Workers (technicals, fundamentals, news)", 0))
        self.add_item(_ModelSelect("debaters", "Debaters (bull & bear)", 1))
        self.add_item(_ModelSelect("judge", "Judge", 2))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                "This isn't your request — start your own with /stock.", ephemeral=True
            )
            return False
        return True

    def _overrides(self) -> dict:
        overrides = {}
        for group, roles in _GROUP_ROLES.items():
            val = self.selections.get(group, "__default__")
            if val and val != "__default__":
                for role in roles:
                    overrides[role] = val
        return overrides

    def _summary(self) -> str:
        parts = []
        for group in _GROUP_ROLES:
            val = self.selections[group]
            parts.append(f"{group}={'default' if val == '__default__' else val.split('/')[-1]}")
        return ", ".join(parts)

    @discord.ui.button(label="Run analysis", style=discord.ButtonStyle.success, emoji="▶️", row=3)
    async def run(self, interaction: discord.Interaction, button: discord.ui.Button):
        overrides = self._overrides()
        for child in self.children:
            child.disabled = True
        await interaction.response.edit_message(
            content=f"🔎 Researching **{self.query}** ({self._summary()})… ~1 min.",
            view=self,
        )
        result = await asyncio.to_thread(core.run_for_query, self.query, overrides)
        if result["ok"]:
            await interaction.followup.send(embed=build_embed(result))
        else:
            await interaction.followup.send("⚠️ " + result["error"])
        self.stop()


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
        view = ModelPicker(query, interaction.user.id)
        await interaction.response.send_message(
            content=f"⚙️ **{query}** — pick models (or just hit Run for defaults):",
            view=view,
        )

    @client.event
    async def on_message(message: discord.Message):
        if message.author == client.user or not config.DISCORD_MESSAGE_CONTENT:
            return
        content = (message.content or "").strip()
        if not content or content.startswith("/"):
            return
        view = ModelPicker(content, message.author.id)
        await message.reply(
            content=f"⚙️ **{content}** — pick models (or just hit Run for defaults):",
            view=view,
        )

    return client


def main():
    if not config.DISCORD_BOT_TOKEN:
        raise RuntimeError("DISCORD_BOT_TOKEN not set in .env.")
    print("Discord bot starting. Press Ctrl+C to stop.")
    build_client().run(config.DISCORD_BOT_TOKEN)


if __name__ == "__main__":
    main()
