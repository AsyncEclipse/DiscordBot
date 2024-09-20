import discord
import time
from commands.tile_commands import TileCommands
import config
from commands.setup_commands import SetupCommands
from commands.player_commands import PlayerCommands
from helpers import ImageCache
from listeners.ButtonListener import ButtonListener
from discord.ext import commands


class DiscordBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def setup_hook(self) -> None:
        print("Bot is starting")
        await self.add_cog(SetupCommands(self))
        await self.add_cog(TileCommands(self))
        await self.add_cog(PlayerCommands(self))
        await self.add_cog(ButtonListener(self))
        await self.tree.sync()
        start_time = time.perf_counter()
        print(f"Starting to load images")
        imageCache = ImageCache.ImageCacheHelper("images/resources")
        # imageCache.load_images()
        end_time = time.perf_counter()
        elapsed_time = end_time - start_time
        print(f"Total elapsed time for image load: {elapsed_time:.2f} seconds")
        print("Bot is now ready.")

bot = DiscordBot(command_prefix="$", intents=discord.Intents.all())
bot.run(config.token)

