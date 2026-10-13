"""One-off: re-create this bot's custom emojis as application emojis.

Downloads each emoji from the Discord CDN by the ID hardcoded in EmojiHelper and
uploads it to the running bot's application, so the bot can use it in any server
without depending on the guild the originals live in. Safe to re-run: names that
already exist on the application are skipped.
"""
import asyncio
import urllib.request

import discord

import config
from helpers.EmojiHelper import EMOJI_MARKUP_LIST

CDN = "https://cdn.discordapp.com/emojis/{}.png"
# The CDN rejects urllib's default User-Agent with a 403.
USER_AGENT = "DiscordBot (https://github.com/AsyncEclipse/DiscordBot, 2.0)"


def _download_all():
    images = {}
    for markup in EMOJI_MARKUP_LIST:
        name, emoji_id = markup.strip("<>").split(":")[1:]
        request = urllib.request.Request(CDN.format(emoji_id), headers={"User-Agent": USER_AGENT})
        images[name] = urllib.request.urlopen(request).read()
    return images


class Uploader(discord.Client):
    async def on_ready(self):
        try:
            existing = {emoji.name for emoji in await self.fetch_application_emojis()}
            images = await asyncio.to_thread(_download_all)
            uploaded = 0
            for name, image in images.items():
                if name in existing:
                    continue
                await self.create_application_emoji(name=name, image=image)
                uploaded += 1
            print(f"{uploaded} uploaded, {len(images) - uploaded} already present")
        finally:
            await self.close()


if __name__ == "__main__":
    Uploader(intents=discord.Intents.none()).run(config.token)
