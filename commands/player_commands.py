import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from helpers.PlayerHelper import PlayerHelper
from helpers.GamestateHelper import GamestateHelper


class PlayerCommands(commands.GroupCog, name="player"):
    def __init__(self, bot):
        self.bot = bot



    @app_commands.command(name="stats", description="Anything to do with player stats")
    async def stats(self, interaction: discord.Interaction, player: discord.Member,
                    materials: Optional[int],
                    science: Optional[int],
                    money: Optional[int]):
        """

        :param materials: Materials resource count - can use +1/-1 to add/subtract
        :param science: Science resource count - can use +1/-1 to add/subtract
        :param money: Money resource count - can use +1/-1 to add/subtract
        :return:
        """
        gamestate = GamestateHelper(interaction.channel)
        p1 = PlayerHelper(player.id, gamestate.get_player_stats(player.id))

        if materials:
            await interaction.channel.send("Done")
        if science:
            await interaction.channel.send("Done1")
        if money:
            await interaction.channel.send("Done2")

        return


    #@stats.command(name="show_all")
    #async def show_all(self, interaction: discord.Interaction, discord_player1: discord.Member):
    #    gamestate = GamestateHelper(interaction.channel)
    #    player1 = PlayerHelper(discord_player1.id, gamestate.get_player_stats(discord_player1.id))
#
 #       await interaction.response.send_message(player1.stats)

  #  @stats.command(name="materials")
   # async def materials(self, interaction: discord.Interaction, discord_player1: discord.Member,
    #                                  adjustment: "int"):
    #    gamestate = GamestateHelper(interaction.channel)
     #   player1 = PlayerHelper(discord_player1.id, gamestate.get_player_stats(discord_player1.id))

      #  await interaction.response.send_message(player1.adjust_materials(adjustment))
       # gamestate.update_player_stats(player1)
