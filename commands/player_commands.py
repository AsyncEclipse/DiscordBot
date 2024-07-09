import discord
import config
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from helpers.PlayerHelper import PlayerHelper
from helpers.GamestateHelper import GamestateHelper

class PlayerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="player_show_all_stats")
    async def player_show_all_stats(self, interaction: discord.Interaction, discord_player1: discord.Member):
        gamestate = GamestateHelper(interaction.channel)
        player1 = PlayerHelper(discord_player1.id, gamestate.get_player_stats(discord_player1.id))

        await interaction.response.send_message(player1.stats)

    @app_commands.command(name="player_adjust_materials")
    async def player_adjust_materials(self, interaction: discord.Interaction, discord_player1: discord.Member, adjustment: "int"):
        gamestate = GamestateHelper(interaction.channel)
        player1 = PlayerHelper(discord_player1.id, gamestate.get_player_stats(discord_player1.id))

        await interaction.response.send_message(player1.adjust_materials(adjustment))
        gamestate.update_player_stats(player1.player_id, player1.stats)