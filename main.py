import os
import sys
import asyncio
import logging

import aiohttp
import discord
from discord.ext import commands

from crypto import init_crypto
from database import init_db, save_token, get_token, delete_token
from quest_engine import QuestEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
log = logging.getLogger("link-bot")

API_BASE = "https://discord.com/api/v9"

client = commands.Bot(command_prefix="!", self_bot=True)
active_engines: dict[int, QuestEngine] = {}


async def _validate_token(token: str):
    try:
        async with aiohttp.ClientSession(
            headers={"Authorization": token}
        ) as s:
            async with s.get(f"{API_BASE}/users/@me") as r:
                if r.status == 200:
                    data = await r.json()
                    tag = f"{data.get('username')}#{data.get('discriminator', '0')}"
                    return True, tag
                return False, None
    except Exception:
        return False, None


@client.event
async def on_ready():
    await init_db()
    print(f"[+] Logged in as {client.user}. Listening for commands.")


@client.command(name="link")
async def link_cmd(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if not isinstance(ctx.channel, discord.DMChannel):
        try:
            await ctx.author.send("❌ `!link` works only in DMs. DM me.")
        except Exception:
            pass
        return

    await ctx.author.send(
        "🔗 **Account Linking**\n\n"
        "Paste your Discord **user token** below.\n\n"
        "It will be encrypted with AES-256-GCM before storage. "
        "Plaintext is never written to disk.\n\n"
        "Send `!cancel` to abort."
    )

    def check(m):
        return m.author == ctx.author and isinstance(m.channel, discord.DMChannel)

    try:
        msg = await client.wait_for("message", check=check, timeout=120.0)
    except asyncio.TimeoutError:
        await ctx.author.send("⏰ Timed out. Run `!link` again.")
        return

    if msg.content.strip().lower() == "!cancel":
        await ctx.author.send("❌ Linking cancelled.")
        return

    token_plain = msg.content.strip()
    try:
        await msg.delete()
    except Exception:
        pass

    ok, tag = await _validate_token(token_plain)
    if not ok:
        await ctx.author.send("❌ Invalid token. Try again with `!link`.")
        return

    await save_token(ctx.author.id, token_plain, tag or "")
    del token_plain

    await ctx.author.send(
        f"✅ **Linked!** `{tag}`\n\n"
        "Token stored encrypted. Quests run in background.\n"
        "Use `!unlink` to stop and delete."
    )

    if ctx.author.id in active_engines:
        active_engines[ctx.author.id].stop()

    tok = await get_token(ctx.author.id)
    if not tok:
        await ctx.author.send("❌ Token retrieval failed. Relink with `!link`.")
        return

    async def notify(text):
        try:
            await ctx.author.send(text)
        except Exception:
            pass

    engine = QuestEngine(tok, ctx.author.id, notify)
    active_engines[ctx.author.id] = engine
    asyncio.create_task(engine.start())


@client.command(name="unlink")
async def unlink_cmd(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass

    if ctx.author.id in active_engines:
        active_engines[ctx.author.id].stop()
        del active_engines[ctx.author.id]

    await delete_token(ctx.author.id)
    await ctx.author.send("🔓 **Unlinked.** Token removed. Quests stopped.")


@client.command(name="status")
async def status_cmd(ctx):
    try:
        await ctx.message.delete()
    except Exception:
        pass
    tok = await get_token(ctx.author.id)
    if tok:
        await ctx.author.send("🟢 **Linked** — quests running in background.")
    else:
        await ctx.author.send("🔴 **Not linked.** Use `!link`.")


def main():
    init_crypto()

    my_token = os.getenv("DISCORD_SELF_TOKEN")
    if not my_token:
        print("ERROR: set DISCORD_SELF_TOKEN env var (your own user token).")
        sys.exit(1)

    client.run(my_token, bot=False)


if __name__ == "__main__":
    main()
