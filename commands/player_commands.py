import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional
from Buttons.Turn import TurnButtons
from helpers.PlayerHelper import PlayerHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from Buttons.TurnButtonsOld import Turn

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
                    influence: Optional[int]):
        """

        :param materials: Materials resource count - can use +1/-1 to add/subtract
        :param science: Science resource count - can use +1/-1 to add/subtract
        :param money: Money resource count - can use +1/-1 to add/subtract
        :param influence: Influence disc count - can use +1/-1 to add/subtract
        :param material_cubes: Material cube count - can use +1/-1 to add/subtract
        :param science_cubes: Science cube count - can use +1/-1 to add/subtract
        :param money_cubes: Money cube count - can use +1/-1 to add/subtract
        :param influence: Influence disc count - can use +1/-1 to add/subtract
        :return:
        """
        gamestate = GamestateHelper(interaction.channel)
        p1 = PlayerHelper(player.id, gamestate.get_player(player.id))
        options = [materials, science, money, material_cubes, science_cubes, money_cubes, influence]

        if all(x is None for x in options):
            top_response = (f"{p1.name} player stats:")
            response=(f"\n> Faction: {p1.stats['name']}"
                        f"\n> Materials: {p1.stats['materials']}"
                        f"\n> Material income: {p1.materials_income()}"
                        f"\n> Science: {p1.stats['science']}"
                        f"\n> Science income: {p1.science_income()}"
                        f"\n> Money: {p1.stats['money']}"
                        f"\n> Money income: {p1.money_income()}"
                        f"\n> Influence dics: {p1.stats['influence_discs']}"
                        f"\n> Upkeep: {p1.upkeep()}"
                        f"\n> Colony Ships: {p1.stats['colony_ships']}")
            await interaction.response.send_message(top_response)
            await interaction.channel.send(response)
            return
        else:
            pass

        top_response = f"{p1.name} made the following changes:"
        response = ""


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
        if influence:
            response += (p1.adjust_influence(influence))

        gamestate.update_player(p1)
        await interaction.response.send_message(top_response)
        await interaction.channel.send(response)

    @app_commands.command(name="show_player_area")
    async def show_player_area(self, interaction: discord.Interaction, player: discord.Member):
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(p1)
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(file=drawing.show_player_area(image))

    @app_commands.command(name="show_player_ships")
    async def show_player_ships(self, interaction: discord.Interaction, player: discord.Member):
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(p1)
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(file=drawing.show_player_ship_area(image))

    @app_commands.command(name="start_turn")
    async def start_turn(self, interaction: discord.Interaction, player: Optional[discord.Member]=None):
        if player == None:
            player = interaction.user
        #view = Turn(interaction, player.id)
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id)
        view = TurnButtons.getStartTurnButtons(game,p1)

        await interaction.response.send_message((f"{player.mention} use these buttons to do your turn. The "
                                                        "number of activations you have for each action is listed in ("
                                                  ")"), view=view)
    
    
