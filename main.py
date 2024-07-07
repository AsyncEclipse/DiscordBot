import discord
import config
from commands.setup_commands import *
from commands.player_commands import *
from discord.ext import commands
import helpers.game_state_helper as game_state_helper


bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())


@bot.event
async def on_ready():
    await bot.add_cog(SetupCommands(bot))
    await bot.add_cog(PlayerCommands(bot))
    await bot.tree.sync()
    print("Bot is now ready.")

bot.run(config.token)


