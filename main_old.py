import discord
import time
from commands.tile_commands import TileCommands
import config
from commands.setup_commands import SetupCommands
from commands.player_commands import PlayerCommands
# from helpers import ImageCache
from listeners.ButtonListener import ButtonListener
from discord.ext import commands


bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())


@bot.event
async def on_ready():
    await bot.add_cog(SetupCommands(bot))
    await bot.add_cog(TileCommands(bot))
    await bot.add_cog(PlayerCommands(bot))
    await bot.add_cog(ButtonListener(bot))
    await bot.tree.sync()
    start_time = time.perf_counter()
    print("Starting to load images")
    # imageCache = ImageCache.ImageCacheHelper("images/resources")
    # imageCache.load_images()
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    print(f"Total elapsed time for image load: {elapsed_time:.2f} seconds")
    print("Bot is now ready.")


bot.run(config.token)
