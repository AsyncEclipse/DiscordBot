import discord
from commands.tile_commands import *
import config
from commands.setup_commands import *
from commands.player_commands import *
from listeners.ButtonListener import *
from discord.ext import commands


bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())


@bot.event
async def on_ready():
    await bot.add_cog(SetupCommands(bot))
    await bot.add_cog(TileCommands(bot))
    await bot.add_cog(PlayerCommands(bot))
    await bot.add_cog(ButtonListener(bot))
    await bot.tree.sync()
    print("Bot is now ready.")


bot.run(config.token)


