import discord
import config
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from helpers.PlayerHelper import PlayerHelper
import helpers.game_state_helper as game_state_helper

class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="player_show_all_stats")
    async def player_show_all_stats(self, interaction: discord.Interaction, discord_player1: discord.Member):
        player1 = PlayerHelper(interaction.channel, discord_player1.id)
        try:
            await interaction.response.send_message(player1.get_player_stats())
        except KeyError:
            await interaction.response.send_message("That player is not in this game.")

    @app_commands.command(name="player_adjust_materials")
    async def player_adjust_materials(self, interaction: discord.Interaction, discord_player1: discord.Member, adjustment: "int"):
        player1 = PlayerHelper(interaction.channel, discord_player1.id)
        await interaction.response.send_message(player1.adjust_materials(adjustment))