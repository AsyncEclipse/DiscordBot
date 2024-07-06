import discord
import config
from discord.ext import commands
from discord import app_commands
from typing import Optional
from setup.GameSetup import GameSetup

class SetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="game_start_new")
    async def game_start_new(self, interaction: discord.Interaction, fun_game_name: str, player1: discord.Member, player2: Optional[discord.Member]=None, player3: Optional[discord.Member]=None, player4: Optional[discord.Member]=None, player5: Optional[discord.Member]=None, player6: Optional[discord.Member]=None):
        temp_player_list = [player1, player2, player3, player4, player5, player6]
        player_list = []

        for i in temp_player_list:
            if i != None:
                player_list.append([i.id, i.name])

        new_game = GameSetup(fun_game_name, player_list)
        new_game.create_game()
        new_game.game_ready()
        new_game.upload()

        await interaction.guild.create_text_channel(f'aeb.{config.game_number}')
        await interaction.response.send_message('New game created!')
