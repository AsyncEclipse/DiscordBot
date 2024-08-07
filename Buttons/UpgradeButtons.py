import discord
from discord import Interaction
from discord._types import ClientT
from discord.ext import commands
from discord.ui import Button
import Buttons.TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper

class UpgradeShip(discord.ui.View):
    def __init__(self, interaction: discord.Interaction, author):
        super().__init__()
        self.author = author

    @discord.ui.button(label="Interceptor", style=discord.ButtonStyle.primary)
    async def interceptor(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("interceptor")

    @discord.ui.button(label="Cruiser", style=discord.ButtonStyle.primary)
    async def cruiser(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("cruise")

    @discord.ui.button(label="Dreadnought", style=discord.ButtonStyle.primary)
    async def dreadnought(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("dreadnought")

    @discord.ui.button(label="Starbase", style=discord.ButtonStyle.primary)
    async def starbase(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("starbase")

    async def interaction_check(self, interaction: discord.Interaction):
        if str(interaction.user.id) != str(self.author):
           await interaction.response.send_message("These buttons are not for you.")
        else:
            return True