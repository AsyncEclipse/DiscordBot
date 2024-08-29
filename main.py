import discord
from commands.tile_commands import TileCommands
import config
from commands.setup_commands import SetupCommands
from commands.player_commands import PlayerCommands
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
    print("Bot is now ready.")


bot.run(config.token)


