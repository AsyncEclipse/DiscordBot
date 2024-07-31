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
    

    @app_commands.command(name="add_units")
    async def add_units(self, interaction: discord.Interaction, tileposition: int, unit_list: str, color: Optional[str]="none"):
        game = GamestateHelper(interaction.channel)
        if(color == "none"):
            color = game.get_player(str(interaction.user.id))["color"]
        game.addUnits(color,unit_list,str(tileposition))
        await interaction.response.defer(thinking=True)  
        tileMap = game.get_gamestate()["board"]
        context = Image.new("RGBA",(345, 299),(255,255,255,0))
        tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(tileposition)]["orientation"])
        context.paste(tileImage,(0,0),mask=tileImage)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="tileImage.png")
        await interaction.followup.send(file=file)
    
    @app_commands.command(name="add_influence")
    async def add_influence(self, interaction: discord.Interaction, tileposition: int, color: Optional[str]="none"):
        game = GamestateHelper(interaction.channel)
        if(color == "none"):
            color = game.get_player(str(interaction.user.id))["color"]
        game.addControl(color,str(tileposition))
        await interaction.response.defer(thinking=True)  
        tileMap = game.get_gamestate()["board"]
        context = Image.new("RGBA",(345, 299),(255,255,255,0))
        tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(tileposition)]["orientation"])
        context.paste(tileImage,(0,0),mask=tileImage)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="tileImage.png")
        await interaction.followup.send(file=file)

    @app_commands.command(name="remove_influence")
    async def remove_influence(self, interaction: discord.Interaction, tileposition: int):
        game = GamestateHelper(interaction.channel)
        game.removeControl(str(tileposition))
        await interaction.response.defer(thinking=True)  
        tileMap = game.get_gamestate()["board"]
        context = Image.new("RGBA",(345, 299),(255,255,255,0))
        tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(tileposition)]["orientation"])
        context.paste(tileImage,(0,0),mask=tileImage)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="tileImage.png")
        await interaction.followup.send(file=file)

    @app_commands.command(name="remove_units")
    async def remove_units(self, interaction: discord.Interaction, tileposition: int, unit_list: str, color: Optional[str]="none"):
        game = GamestateHelper(interaction.channel)
        if(color == "none"):
            color = game.get_player(str(interaction.user.id))["color"]
        game.removeUnits(color,unit_list,str(tileposition))
        await interaction.response.defer(thinking=True)  
        tileMap = game.get_gamestate()["board"]
        context = Image.new("RGBA",(345, 299),(255,255,255,0))
        tileImage = game.drawTile(context, str(tileposition),tileMap[str(tileposition)]["sector"], tileMap[str(tileposition)]["orientation"])
        context.paste(tileImage,(0,0),mask=tileImage)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="tileImage.png")
        await interaction.followup.send(file=file)
    
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

    @app_commands.command(name="tile_test")
    async def tile_test(self, interaction: discord.Interaction, tile_position: str):
        game = GamestateHelper(interaction.channel)
        #await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        try:
            image = drawing.board_tile_image(tile_position)
            await interaction.response.send_message(file=drawing.show_single_tile(image))
        except KeyError:
            await interaction.response.send_message("This tile does not exist!")

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