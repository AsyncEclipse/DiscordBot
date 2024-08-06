import discord
from discord.ext import commands
from discord.ui import View
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from Buttons.BuildButtons import Build, BuildLocation

class Turn(discord.ui.View):
    def __init__(self, interaction):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.p1 = self.game.get_player(interaction.user.id)

    @discord.ui.button(label=f"Build", style=discord.ButtonStyle.success)
    async def build (self, interaction: discord.Interaction, button: discord.ui.Button):
        game = GamestateHelper(interaction.channel)
        tiles = game.get_owned_tiles(interaction.user.id)
        tiles.sort()
        view=View()
        for i in tiles:
            button2 = BuildLocation(i, discord.ButtonStyle.primary)
            view.add_item(button2)

        await interaction.response.send_message(f"{interaction.user.mention}, choose which tile you would like to build in.", view=view)


    @discord.ui.button(label="Research", style=discord.ButtonStyle.primary)
    async def research(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Research")


    @discord.ui.button(label="Upgrade", style=discord.ButtonStyle.success)
    async def upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Upgrade")

