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
                    money: Optional[int],
                    material_cubes: Optional[int],
                    science_cubes: Optional[int],
                    money_cubes: Optional[int],
                    influence: Optional[int],
                    colony_ships: Optional[int]):
        """

        :param materials: Materials resource count - can use +1/-1 to add/subtract
        :param science: Science resource count - can use +1/-1 to add/subtract
        :param money: Money resource count - can use +1/-1 to add/subtract
        :param influence: Influence disc count - can use +1/-1 to add/subtract
        :param material_cubes: Material cube count - can use +1/-1 to add/subtract
        :param science_cubes: Science cube count - can use +1/-1 to add/subtract
        :param money_cubes: Money cube count - can use +1/-1 to add/subtract
        :return:
        """
        gamestate = GamestateHelper(interaction.channel)
        p1 = PlayerHelper(player.id, gamestate.get_player(player.id))
        response = f"{p1.name} made the following changes:"


        if materials:
            response += (p1.adjust_materials(materials))
        if science:
            response += (p1.adjust_science(science))
        if money:
            response += (p1.adjust_money(money))
        if material_cubes:
            response += (p1.adjust_material_cube(material_cubes))
        if science_cubes:
            response += (p1.adjust_science_cube(science_cubes))
        if money_cubes:
            response += (p1.adjust_money_cube(money_cubes))

        gamestate.update_player(p1)
        await interaction.response.send_message(response)


