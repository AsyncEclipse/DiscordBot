from asyncio.log import logger
import json
import discord
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Influence import InfluenceButtons
import config
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional, List
from setup.GameInit import GameInit
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import random


class TileCommands(commands.GroupCog, name="tile"):
    def __init__(self, bot):
        self.bot = bot
    

 


    color_choices = [
        app_commands.Choice(name="Blue", value="blue"),
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Yellow", value="yellow"),
        app_commands.Choice(name="Purple", value="purple"),
        app_commands.Choice(name="Green", value="green"),
        app_commands.Choice(name="White", value="white")
    ]

    unit_choices = [
        app_commands.Choice(name="interceptor", value="int"),
        app_commands.Choice(name="cruiser", value="cru"),
        app_commands.Choice(name="dreadnought", value="drd"),
        app_commands.Choice(name="starbase", value="sb"),
        app_commands.Choice(name="guardian", value="grd"),
        app_commands.Choice(name="ancient", value="anc"),
        app_commands.Choice(name="gcds", value="gcds")
    ]

    @app_commands.command(name="manage_damage", description="add or remove damage from units")
    @app_commands.choices(color=color_choices, unit=unit_choices)
    async def manage_damage(self, interaction: discord.Interaction, tile_position: str,
                        damage_change: int,
                        unit : app_commands.Choice[str],
                        color: Optional[app_commands.Choice[str]]=None):
        game = GamestateHelper(interaction.channel)  
        type = unit.value
        if unit.value == "grd" or unit.value == "anc" or unit.value == "gcds":
            colorOrAI = "ai"
            if game.gamestate["advanced_ai"]:
                type += "adv"
        else:
            colorOrAI = color.value if color else game.get_player(str(interaction.user.id))["color"]
        option = colorOrAI + "-"+type
        damageOnShip = game.add_damage(option, tile_position, 0)
        if damage_change > 0:
            game.add_damage(option, tile_position, damage_change)
        else:
            for x in range(-1*damage_change):
                game.repair_damage(option, tile_position)
        await interaction.response.defer(thinking=True)  
        drawing = DrawHelper(game.gamestate)  
        image = drawing.board_tile_image(tile_position)  
        await interaction.followup.send(file=drawing.show_single_tile(image)) 
        
    @app_commands.command(name="manage_units", description="add or remove units from a tile")
    @app_commands.choices(color=color_choices)
    async def manage_units(self, interaction: discord.Interaction, tile_position: str,
                        interceptors: Optional[int],
                        cruisers: Optional[int],
                        dreadnoughts: Optional[int],
                        starbase: Optional[int],
                        orbitals: Optional[int],
                        monoliths: Optional[int],
                        guardians: Optional[int],
                        ancients: Optional[int],
                        gcds: Optional[int],
                        influence: Optional[bool],
                        color: Optional[app_commands.Choice[str]]=None):
        """

        :param interceptors: Use +1/-1 to add/subtract interceptors
        :param cruisers: Use +1/-1 to add/subtract cruisers
        :param dreadnoughts: Use +1/-1 to add/subtract dreadnoughts
        :param starbase: Use +1/-1 to add/subtract starbases
        :param influence: Use True/False to add or remove your influence disc from this tile
        :param color: Choose player color. Default is your own color
        :return:
        """
        game = GamestateHelper(interaction.channel)  
        player_color = color.value if color else game.get_player(str(interaction.user.id))["color"]  
        
        added_units, removed_units = [], []  
        
        def process_units(unit_type, count):  
            if unit_type in ["gcds", "gcdsadv", "anc", "ancadv", "grd", "grdadv"]:
                unit_code = f"ai-{unit_type}"  
            else:
                unit_code = f"{player_color}-{unit_type}"  
            if count:  
                units_list = added_units if count > 0 else removed_units  
                for x in range(abs(count)):  
                    units_list.append(unit_code)  

        process_units("int", interceptors)  
        process_units("cru", cruisers)  
        process_units("drd", dreadnoughts)  
        process_units("sb", starbase)  
        process_units("orb", orbitals)  
        process_units("mon", monoliths)  
        adv = ""
        if game.gamestate["advanced_ai"]:
            adv = "adv"
        process_units("gcds"+adv, gcds)  
        process_units("anc"+adv, ancients)  
        process_units("grd"+adv, guardians)  

        if added_units:  
            game.add_units(added_units, tile_position)  
        if removed_units:  
            game.remove_units(removed_units, tile_position)  
        
        if influence != None:
            if influence:
                if game.gamestate["board"][tile_position]["owner"] != 0:
                    game.remove_control(game.gamestate["board"][tile_position]["owner"], tile_position)
                game.add_control(player_color, tile_position)
            else:
                game.remove_control(player_color, tile_position)

        await interaction.response.defer(thinking=True)  
        drawing = DrawHelper(game.gamestate)  
        image = drawing.board_tile_image(tile_position)  
        await interaction.followup.send(file=drawing.show_single_tile(image)) 




    @app_commands.command(name="manage_population", description="add or remove population cubes (using positive or negative numbers) from a tile")
    @app_commands.choices(color=color_choices)
    async def manage_population(self, interaction: discord.Interaction, tile_position: str,
                        money: Optional[int],
                        science: Optional[int],
                        material: Optional[int],
                        neutral: Optional[int],
                        orbital: Optional[int],
                        advanced_money: Optional[int],
                        advanced_science: Optional[int],
                        advanced_material: Optional[int],
                        advanced_neutral: Optional[int],
                        influence: Optional[bool],
                        color: Optional[app_commands.Choice[str]]=None):
        """
        :param influence: Use True/False to add or remove your influence disc from this tile
        :param color: Choose player color. Default is your own color
        :return:
        """
        game = GamestateHelper(interaction.channel)  
        player_color = color.value if color else game.get_player(str(interaction.user.id))["color"]  
        playerID = game.get_player_from_color(player_color)
        playerObj = game.getPlayerObjectFromColor(player_color)
        added_pop, removed_pop = [], []  
        
        def process_pop(pop_type, count):  
            pop_code = f"{pop_type}_{'pop'}"
            if count:  
                count = min(count, 2)
                pop_list = added_pop if count > 0 else removed_pop  
                for x in range(abs(count)):  
                    pop_list.append(pop_code)  

        process_pop("money", money)  
        process_pop("science", science)  
        process_pop("neutral", neutral)  
        process_pop("material", material)
        process_pop("moneyadv", advanced_money)  
        process_pop("scienceadv", advanced_science)  
        process_pop("neutraladv", advanced_neutral)
        process_pop("materialadv", advanced_material)  
        process_pop("orbital", orbital)  

        if added_pop:  
            neutralPop = game.add_pop(added_pop, tile_position,playerID)  
            for x in range(neutralPop):
                view = View()
                view.add_item(Button(label="Material", style=discord.ButtonStyle.gray, custom_id=f"FCID{player_color}_reducePopFor_material"))
                view.add_item(Button(label="Science", style=discord.ButtonStyle.gray, custom_id=f"FCID{player_color}_reducePopFor_science"))
                view.add_item(Button(label="Money", style=discord.ButtonStyle.gray, custom_id=f"FCID{player_color}_reducePopFor_money"))
                await interaction.channel.send( f"{playerObj['player_name']} Choose what type of cube to put on the neutral/orbital planet", view=view)
        if removed_pop:  
            neutralPop = game.remove_pop(removed_pop, tile_position,playerID, False)  
            if neutralPop > 0:
                for x in range(neutralPop):
                    view=View()
                    planetTypes = ["money","science","material"]
                    for planetT in planetTypes:
                        if playerObj[planetT+"_pop_cubes"] < 12:
                            view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player_color}_addCubeToTrack_"+planetT))
                    await interaction.channel.send( f"A cube with no set track was removed, please tell the bot what track you want it to go on", view=view)

        if influence != None:
            if influence:
                if game.gamestate["board"][tile_position]["owner"] != 0:
                    game.remove_control(game.gamestate["board"][tile_position]["owner"], tile_position)
                game.add_control(player_color, tile_position)
            else:
                game.remove_control(player_color, tile_position)

        await interaction.response.defer(thinking=True)  
        drawing = DrawHelper(game.gamestate)  
        image = drawing.board_tile_image(tile_position)  
        await interaction.followup.send(file=drawing.show_single_tile(image)) 

    @app_commands.command(name="add_influence")
    @app_commands.choices(color=color_choices)
    async def add_influence(self, interaction: discord.Interaction, tile_position: str, color : Optional[app_commands.Choice[str]]=None):
        game = GamestateHelper(interaction.channel)
        player_color = color.value if color else game.get_player(str(interaction.user.id))["color"]
        if game.gamestate["board"][tile_position]["owner"] != 0:
            await interaction.response.send_message("Please remove the current influence disc first")
            return
        game.add_control(player_color, tile_position)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        image = drawing.board_tile_image(tile_position)
        await interaction.followup.send(file=drawing.show_single_tile(image))
    @app_commands.command(name="remove_influence")
    @app_commands.choices(color=color_choices)
    async def remove_influence(self, interaction: discord.Interaction, tile_position: str, color: app_commands.Choice[
        str]):
        game = GamestateHelper(interaction.channel)
        if game.gamestate["board"][tile_position]["owner"] == 0:
            await interaction.response.send_message("This tile already has no influence.")
            return
        await interaction.response.defer(thinking=True)
        await InfluenceButtons.removeInfluenceFinish(game, interaction, f"dummy_{tile_position}_Normal",False)
        drawing = DrawHelper(game.gamestate)
        image = drawing.board_tile_image(tile_position)
        await interaction.followup.send(file=drawing.show_single_tile(image))

    @app_commands.command(name="explore_specific_system_tile")
    async def explore_specific_system_tile(self, interaction: discord.Interaction, tile_position: str, system_num:str):
        game = GamestateHelper(interaction.channel)
        tile = game.tile_draw_specific(tile_position,system_num)
        drawing = DrawHelper(game.gamestate)
        orientation = 0
        await interaction.response.defer(thinking=True)
        image = drawing.base_tile_image(tile)
        await interaction.followup.send(file=drawing.show_single_tile(image))
        view = View()
        button = Button(label="Place Tile",style=discord.ButtonStyle.green, custom_id=f"placeTile_"
                                                                                        f"{tile_position}_{tile}_{orientation}")
        button2 = Button(label="Discard Tile",style=discord.ButtonStyle.red, custom_id=f"discardTile_{tile}")
        view.add_item(button)
        view.add_item(button2)
        await interaction.channel.send(view=view)

    @app_commands.command(name="add_discovery_tile")
    async def add_discovery_tile(self, interaction: discord.Interaction, tile_position: str):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking = False)
        game.addDiscTile(tile_position)
        await interaction.followup.send("Added a discovery tile to tile "+tile_position)
    
    @app_commands.command(name="resolve_specific_discovery_tile")
    async def resolve_specific_discovery_tile(self, interaction: discord.Interaction, tile_position: str, discovery_id:str):
        game = GamestateHelper(interaction.channel)
        disc = discovery_id
        tile = tile_position
        await interaction.response.defer(thinking = False)
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        if disc not in discTile_data:
            await interaction.followup.send(discovery_id+" is not a valid ID. Ping someone who knows the code to find the correct ID")
            return
        discName = discTile_data[disc]["name"]
        drawing = DrawHelper(game.gamestate)
        file = drawing.show_disc_tile(discName)
        msg = f"{interaction.user.mention} you explored a discovery tile and found a "+discName+". You can keep it for 2 points at the end of the game or use it for its ability"
        
        view = View()
        view.add_item(Button(label="Use it for its ability", style=discord.ButtonStyle.green, custom_id=f"usedDiscForAbility_"+disc+"_"+tile))  
        view.add_item(Button(label="Get 2 Points", style=discord.ButtonStyle.red, custom_id="keepDiscForPoints"))  
        await interaction.followup.send(msg, view=view,file=file)



    @app_commands.command(name="explore_discovery_tile")
    async def explore_discovery_tile(self, interaction: discord.Interaction, tile_position: str):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking = False)
        await DiscoveryTileButtons.exploreDiscoveryTile(game, tile_position, interaction,game.get_player(interaction.user.id))

    @app_commands.command(name="show")
    async def show(self, interaction: discord.Interaction, tile_position: str):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        try:
            await interaction.followup.send(file=drawing.board_tile_image_file(tile_position))
        except KeyError:
            await interaction.followup.send("This tile does not exist!")
    
    @app_commands.command(name="rotate")
    async def rotate(self, interaction: discord.Interaction, tile_position: str, degrees_to_rotate: int):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        if degrees_to_rotate % 60 != 0:
            await interaction.followup.send("Degrees to rotate should be in increments of 60")
            return
        game.rotate_tile(tile_position,degrees_to_rotate)
        drawing = DrawHelper(game.gamestate)
        try:
            await interaction.followup.send(file=drawing.board_tile_image_file(tile_position))
        except KeyError:
            await interaction.followup.send("This tile does not exist!")

    @app_commands.command(name="show_base_tile")
    async def show_base_tile(self, interaction: discord.Interaction, sector: str):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        try:
            image = drawing.base_tile_image(sector)
            await interaction.followup.send(file=drawing.show_single_tile(image))
        except ValueError:
            await interaction.followup.send("This tile does not exist!")

   