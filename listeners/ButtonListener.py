import discord
from discord.ext import commands
from helpers.GamestateHelper import GamestateHelper
from commands.setup_commands import SetupCommands

class ButtonListener(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @commands.Cog.listener()
    async def on_interaction(self, interaction):
        if interaction.type == discord.InteractionType.component:
            if interaction.data["custom_id"].startswith("place_tile"):
                await interaction.response.defer(thinking=True)
                game = GamestateHelper(interaction.channel)
                msg = interaction.data["custom_id"].split("_")
                game.add_tile(msg[2], 0, msg[3])
                await interaction.followup.send(f"Tile added to position {msg[2]}")
                await interaction.message.delete()
            if interaction.data['custom_id'].startswith("discard_tile"):
                game = GamestateHelper(interaction.channel)
                msg = interaction.data["custom_id"].split("_")
                game.tile_discard(msg[2])
                await interaction.channel.send("Tile discarded")
                await interaction.message.delete()
