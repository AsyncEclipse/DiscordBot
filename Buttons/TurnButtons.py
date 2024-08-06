import discord
from discord.ext import commands
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from Buttons.BuildButtons import Build

class Turn(discord.ui.View):
    def __init__(self, interaction):
        super().__init__()
        self.game = GamestateHelper(interaction.channel)
        self.p1 = self.game.get_player(interaction.user.id)

    @discord.ui.button(label=f"Build", style=discord.ButtonStyle.success)
    async def build (self, interaction: discord.Interaction, button: discord.ui.Button):
        view = Build(interaction, [], 0)
        await interaction.response.send_message(f"Build up to {self.p1["build_apt"]} ships.", view=view)


    @discord.ui.button(label="Research", style=discord.ButtonStyle.primary)
    async def research(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Research")


    @discord.ui.button(label="Upgrade", style=discord.ButtonStyle.success)
    async def upgrade(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Upgrade")

