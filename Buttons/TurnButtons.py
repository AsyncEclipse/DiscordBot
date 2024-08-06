import discord
from discord.ext import commands
from discord.ui import View
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from Buttons.BuildButtons import Build, BuildLocation

class Turn(discord.ui.View):
    def __init__(self, interaction, player_id):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.player = self.game.get_player(str(player_id))
        self.author = player_id

    @discord.ui.button(label=f"Build", style=discord.ButtonStyle.success)
    async def build (self, interaction: discord.Interaction, button: discord.ui.Button):
        game = GamestateHelper(interaction.channel)
        tiles = game.get_owned_tiles(interaction.user.id)
        tiles.sort()
        view=View()
        for i in tiles:
            button2 = BuildLocation(i, discord.ButtonStyle.primary, self.author)
            view.add_item(button2)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention}, choose which tile you would like to build in.", view=view)


    @discord.ui.button(label="Research", style=discord.ButtonStyle.primary)
    async def research(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Research")


    @discord.ui.button(label="Upgrade", style=discord.ButtonStyle.success)
    async def upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Upgrade")

    async def interaction_check(self, interaction: discord.Interaction):
        if interaction.user.id != self.author:
           await interaction.response.send_message("These buttons are not for you.")
        else:
            return True