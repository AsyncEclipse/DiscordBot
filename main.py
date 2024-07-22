import discord
import config
from commands.setup_commands import *
from commands.player_commands import *
from discord.ext import commands


bot = commands.Bot(command_prefix="$", intents=discord.Intents.all())


@bot.event
async def on_ready():
    await bot.add_cog(SetupCommands(bot))
    await bot.add_cog(PlayerCommands(bot))
    await bot.tree.sync()
    print("Bot is now ready.")

@bot.event
async def on_interaction(interaction):  
    if interaction.type == discord.InteractionType.component:  
        if interaction.data['custom_id'] == "showGame":  
            game = GamestateHelper(interaction.channel)
            await SetupCommands.showGame(interaction,game)
        if interaction.data['custom_id'] == "discardTile":  
            game = GamestateHelper(interaction.channel)
            await interaction.channel.send("Tile discarded")
            await interaction.message.delete()
        if interaction.data['custom_id'].startswith("placeTile"):
            await interaction.response.defer(thinking=True)
            game = GamestateHelper(interaction.channel)
            splitMsg = interaction.data['custom_id'].split("_")
            game.addTile(splitMsg[1],splitMsg[2],0)
            await interaction.followup.send("Tile added to position "+splitMsg[1])
            await interaction.message.delete()
bot.run(config.token)


