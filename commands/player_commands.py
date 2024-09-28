import discord
import json
from discord.ext import commands
from discord import app_commands
from typing import Optional
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.Move import MoveButtons
from Buttons.Reputation import ReputationButtons
from Buttons.Research import ResearchButtons
from Buttons.Turn import TurnButtons
from Buttons.Upgrade import UpgradeButtons
from helpers.PlayerHelper import PlayerHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper

class PlayerCommands(commands.GroupCog, name="player"):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="stats", description="Anything to do with player stats")
    async def stats(self, interaction: discord.Interaction,
                    materials: Optional[int],
                    science: Optional[int],
                    money: Optional[int],
                    material_cubes: Optional[int],
                    science_cubes: Optional[int],
                    money_cubes: Optional[int],
                    discovery_tiles_kept: Optional[int],
                    influence: Optional[int],
                    colony_ships: Optional[int], player: Optional[discord.Member]=None):
        """

        :param materials: Materials resource count - can use +1/-1 to add/subtract
        :param science: Science resource count - can use +1/-1 to add/subtract
        :param money: Money resource count - can use +1/-1 to add/subtract
        :param influence: Influence disc count - can use +1/-1 to add/subtract
        :param material_cubes: Material cube count - can use +1/-1 to add/subtract
        :param science_cubes: Science cube count - can use +1/-1 to add/subtract
        :param money_cubes: Money cube count - can use +1/-1 to add/subtract
        :param influence: Influence disc count - can use +1/-1 to add/subtract
        :param colony_ships: Ready colony ship count - can use +1/-1 to add/subtract
        :return:
        """
        if player == None:
            player = interaction.user
        gamestate = GamestateHelper(interaction.channel)
        p1 = PlayerHelper(player.id, gamestate.get_player(player.id))
        options = [materials, science, money, material_cubes, science_cubes, money_cubes, influence, colony_ships, discovery_tiles_kept]

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
                        f"\n> Colony Ships: {p1.stats['colony_ships']}"
                        f"\n> Discovert Tiles Kept For Points: {p1.stats['disc_tiles_for_points']}")
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
        if colony_ships:
            before = p1.stats['colony_ships']
            p1.adjust_colony_ships(-colony_ships)
            response += f"\n> Adjusted colony ships from {str(before)} to {str(p1.stats['colony_ships'])}"
        if discovery_tiles_kept:
            before = p1.stats['disc_tiles_for_points']
            p1.modify_disc_tile_for_points(discovery_tiles_kept)
            response += f"\n> Adjusted the number of discovery tiles kept for points from {str(before)} to {str(p1.stats['disc_tiles_for_points'])}"

        gamestate.update_player(p1)
        await interaction.response.send_message(top_response)
        await interaction.channel.send(response)

    @app_commands.command(name="remove_tech")
    async def remove_tech(self, interaction: discord.Interaction, tech:str):
        """:param tech: The ID of the tech to be removed. Type help to get a list of your tech IDs"""
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)
        with open("data/techs.json", "r") as f:  
            tech_data = json.load(f)  
        tech_details = tech_data.get(tech)
        if tech_details == None:
            msg = "Your tech ids are the following: \n"
            for tech2 in player_helper.getTechs():
                msg = msg + tech2 +" = "+ tech_data.get(tech2)["name"] +"\n"
            await interaction.response.send_message(msg)
            return
        else:
            game.playerReturnTech(str(interaction.user.id),tech,player_helper.getTechType(tech))
            await interaction.response.send_message("Successfully returned "+tech_details["name"])
        
    
    actionChoices = [
        app_commands.Choice(name="Explore", value="explore"),
        app_commands.Choice(name="Build", value="build"),
        app_commands.Choice(name="Upgrade", value="upgrade"),
        app_commands.Choice(name="Influence", value="influence"),
        app_commands.Choice(name="Research", value="research"),
        app_commands.Choice(name="Move", value="move"),
    ]
    @app_commands.command(name="adjust_actions")
    @app_commands.choices(action=actionChoices)
    async def adjust_actions(self, interaction: discord.Interaction, amount_to_change:int, action:app_commands.Choice[str]):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)
        player_helper.adjust_influence_on_action(action.value, amount_to_change)
        game.update_player(player_helper)
        await interaction.response.send_message(f"{interaction.user.mention} adjusted action disks for "+action.value+" by "+str(amount_to_change))

    @app_commands.command(name="research")
    async def research(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)
        await interaction.response.defer(thinking=False)
        await ResearchButtons.startResearch(game, player, player_helper,interaction,False)
    @app_commands.command(name="upgrade")
    async def upgrade(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        await interaction.response.defer(thinking=False)
        await UpgradeButtons.startUpgrade(game, player, interaction, False,"dummy")
    @app_commands.command(name="move")
    async def move(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)
        await interaction.response.defer(thinking=False)
        await MoveButtons.startMove(game, player, interaction,"startMove_8", True)


    color_choices = [
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Yellow", value="yellow"),
        app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="White", value="white")
    ]

    @app_commands.command(name="break_relations")
    @app_commands.choices(color=color_choices)
    async def break_relations(self, interaction: discord.Interaction, color:app_commands.Choice[str]):
        player = interaction.user
        await interaction.response.defer()
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id)
        p2 = game.get_player_from_color(color.value)
        await DiplomaticRelationsButtons.breakRelationsWith(game, p1, game.get_gamestate()['players'][p2], interaction)



    @app_commands.command(name="show_player_area")
    async def show_player_area(self, interaction: discord.Interaction, player: Optional[discord.Member]=None):
        if player == None:
            player = interaction.user
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id)
        drawing = DrawHelper(game.gamestate)
        image = drawing.player_area(p1)
        await interaction.response.defer(thinking=True)
        await interaction.followup.send(file=drawing.show_player_area(image))
    
    @app_commands.command(name="set_passed")
    async def set_passed(self, interaction: discord.Interaction, passed:bool, permanent: Optional[bool]=None, player: Optional[discord.Member]=None):
        if player == None:
            player = interaction.user
        if permanent == None:
            permanent = passed
        game = GamestateHelper(interaction.channel)
        p1 = game.get_player(player.id)
        player_helper = PlayerHelper(player.id, p1)
        player_helper.permanentlyPassTurn(permanent)
        player_helper.passTurn(passed)
        game.update_player(player_helper)
        await interaction.response.send_message(f"{player.mention} set passed status to "+str(passed))
        
    
    @app_commands.command(name="draw_reputation")
    async def draw_reputation(self, interaction: discord.Interaction, num_options: int):
        game = GamestateHelper(interaction.channel)
        player = game.get_player(interaction.user.id)  
        player_helper = PlayerHelper(interaction.user.id, player)
        await interaction.response.defer(thinking=True, ephemeral=True)
        await ReputationButtons.resolveGainingReputation(game, num_options,interaction, player_helper)

    @app_commands.command(name="show_player_ships")
    async def show_player_ships(self, interaction: discord.Interaction, player: Optional[discord.Member]=None):
        if player == None:
            player = interaction.user
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
                                                        "number of activations you have for each action is listed in ()"+game.displayPlayerStats(p1)), view=view)
    
    
    @app_commands.command(name="show_upgrade_reference")
    async def show_upgrade_reference(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        image = DrawHelper.show_ref("upgrade")
        await interaction.followup.send(file=image, ephemeral=True)

