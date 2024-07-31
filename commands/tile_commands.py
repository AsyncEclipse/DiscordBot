import discord
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

    @app_commands.command(name="manage_units", description="add or remove units from a tile")
    @app_commands.choices(color=color_choices)
    async def manage_units(self, interaction: discord.Interaction, tile_position: str,
                        interceptors: Optional[int],
                        cruisers: Optional[int],
                        dreadnoughts: Optional[int],
                        starbase: Optional[int],
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
        added_units = []
        removed_units = []
        if color == None:
            player_color = game.get_player(str(interaction.user.id))["color"]
        else:
            player_color = color.value

        if interceptors:
            if interceptors > 0:
                while interceptors > 0:
                    added_units.append(f"{player_color}-int")
                    interceptors -= 1
            else:
                while interceptors < 0:
                    removed_units.append(f"{player_color}-int")
                    interceptors += 1
        if cruisers:
            if cruisers > 0:
                while cruisers > 0:
                    added_units.append(f"{player_color}-cru")
                    cruisers -= 1
            else:
                while cruisers < 0:
                    removed_units.append(f"{player_color}-cru")
                    cruisers += 1
        if dreadnoughts:
            if dreadnoughts > 0:
                while dreadnoughts > 0:
                    added_units.append(f"{player_color}-drd")
                    dreadnoughts -= 1
            else:
                while dreadnoughts < 0:
                    removed_units.append(f"{player_color}-drd")
                    dreadnoughts += 1
        if starbase:
            if starbase > 0:
                while starbase > 0:
                    added_units.append(f"{player_color}-sb")
                    starbase -= 1
            else:
                while starbase < 0:
                    removed_units.append(f"{player_color}-sb")
                    starbase += 1
        if len(added_units) > 0:
            game.add_units(added_units, tile_position)
        if len(removed_units) > 0:
            game.remove_units(removed_units, tile_position)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        image = drawing.board_tile_image(tile_position)
        await interaction.followup.send(file=drawing.show_single_tile(image))

    @app_commands.command(name="add_influence")
    @app_commands.choices(color=color_choices)
    async def add_influence(self, interaction: discord.Interaction, tile_position: str, color: app_commands.Choice[
        str]):
        game = GamestateHelper(interaction.channel)
        if game.gamestate["board"][tile_position]["owner"] != 0:
            await interaction.response.send_message("Please remove the current influence disc first")
            return
        game.add_control(color.value, tile_position)
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
        game.remove_control(color.value, tile_position)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        image = drawing.board_tile_image(tile_position)
        await interaction.followup.send(file=drawing.show_single_tile(image))
    #@app_commands.command(name="add_units")
    #async def add_units(self, interaction: discord.Interaction, tileposition: int, unit_list: str, color: Optional[
    # str]="none"):
    #    game = GamestateHelper(interaction.channel)
    #    if(color == "none"):
    #        color = game.get_player(str(interaction.user.id))["color"]
    #    game.addUnits(color,unit_list,str(tileposition))
    #    await interaction.response.defer(thinking=True)
    #    tileMap = game.get_gamestate()["board"]
    #    context = Image.new("RGBA",(345, 299),(255,255,255,0))
    #    tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(
    #    tileposition)]["orientation"])
    #    context.paste(tileImage,(0,0),mask=tileImage)
    #    bytes = BytesIO()
    #    context.save(bytes,format="PNG")
    #    bytes.seek(0)
    #    file = discord.File(bytes,filename="tileImage.png")
    #    await interaction.followup.send(file=file)
    
    #@app_commands.command(name="add_influence")
    #async def add_influence(self, interaction: discord.Interaction, tileposition: int, color: Optional[str]="none"):
    #    game = GamestateHelper(interaction.channel)
    #    if(color == "none"):
    #        color = game.get_player(str(interaction.user.id))["color"]
    #    game.addControl(color,str(tileposition))
    #    await interaction.response.defer(thinking=True)
    #    tileMap = game.get_gamestate()["board"]
    #    context = Image.new("RGBA",(345, 299),(255,255,255,0))
    #    tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(
    #    #    tileposition)]["orientation"])
    #    context.paste(tileImage,(0,0),mask=tileImage)
    #    bytes = BytesIO()
    #    context.save(bytes,format="PNG")
    #    bytes.seek(0)
    #    file = discord.File(bytes,filename="tileImage.png")
    #    await interaction.followup.send(file=file)

    #@app_commands.command(name="remove_influence")
    #async def remove_influence(self, interaction: discord.Interaction, tileposition: int):
    #    game = GamestateHelper(interaction.channel)
    #    game.removeControl(str(tileposition))
    #    await interaction.response.defer(thinking=True)
    #    tileMap = game.get_gamestate()["board"]
    #    context = Image.new("RGBA",(345, 299),(255,255,255,0))
    #    tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(
    #    #    tileposition)]["orientation"])
    #    context.paste(tileImage,(0,0),mask=tileImage)
    #    bytes = BytesIO()
    #    context.save(bytes,format="PNG")
    #    bytes.seek(0)
    #    file = discord.File(bytes,filename="tileImage.png")
    #   await interaction.followup.send(file=file)

    #@app_commands.command(name="remove_units")
    #async def remove_units(self, interaction: discord.Interaction, tileposition: int, unit_list: str,
    #    # color: Optional[str]="none"):
    #    game = GamestateHelper(interaction.channel)
    #    if(color == "none"):
    #        color = game.get_player(str(interaction.user.id))["color"]
    #    game.removeUnits(color,unit_list,str(tileposition))
    #    await interaction.response.defer(thinking=True)
    #    tileMap = game.get_gamestate()["board"]
    #    context = Image.new("RGBA",(345, 299),(255,255,255,0))
    #    tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(
    #    #    tileposition)]["orientation"])
    #    context.paste(tileImage,(0,0),mask=tileImage)
    #    bytes = BytesIO()
    #    context.save(bytes,format="PNG")
    #    bytes.seek(0)
    #    file = discord.File(bytes,filename="tileImage.png")
    #    await interaction.followup.send(file=file)
    
    @app_commands.command(name="explore_tile")
    async def explore_tile(self, interaction: discord.Interaction, tileposition: int):
        game = GamestateHelper(interaction.channel)
        ring = int(tileposition/100)
        tileName = game.retrieveTileFromList(ring)
        await interaction.response.defer(thinking=True)  
        context = Image.new("RGBA",(345, 299),(255,255,255,0))
        tileImage = game.showTile(tileName)
        context.paste(tileImage,(0,0),mask=tileImage)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="tileImage.png")
        await interaction.followup.send(file=file)
        view = View()
        button = Button(label="Place Tile",style=discord.ButtonStyle.success, custom_id="placeTile_"+str(tileposition)+"_"+tileName)
        button2 = Button(label="Discard Tile",style=discord.ButtonStyle.danger, custom_id="discardTile")
        view.add_item(button)
        view.add_item(button2)
        await interaction.channel.send(view=view)

    @app_commands.command(name="show_tile")
    async def show_tile(self, interaction: discord.Interaction, tile_position: str):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        try:
            image = drawing.board_tile_image(tile_position)
            await interaction.followup.send(file=drawing.show_single_tile(image))
        except KeyError:
            await interaction.followup.send("This tile does not exist!")

    @app_commands.command(name="show_sector")
    async def show_sector(self, interaction: discord.Interaction, sector: str):
        game = GamestateHelper(interaction.channel)
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        try:
            image = drawing.base_tile_image(sector)
            await interaction.followup.send(file=drawing.show_single_tile(image))
        except ValueError:
            await interaction.followup.send("This tile does not exist!")