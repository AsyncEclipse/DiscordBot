import json
import discord
from discord.ui import View
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties

class DiscoveryTileButtons:
    @staticmethod 
    async def exploreDiscoveryTile(game: GamestateHelper, tile:str, interaction: discord.Interaction):
        if "discTiles" not in game.get_gamestate():
            game.fillInDiscTiles()

        disc = game.getNextDiscTile(tile)
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        discName = discTile_data[disc]["name"]
        drawing = DrawHelper(game.gamestate)
        file = drawing.show_disc_tile(discName)
        msg = f"{interaction.user.mention} you explored a discorvery tile and found a "+discName+". You can keep it for 2 points at the end of the game or use it for its ability"
        
        view = View()
        view.add_item(Button(label="Use it for its ability", style=discord.ButtonStyle.green, custom_id="usedDiscForAbility_"+disc+"_"+tile))  
        view.add_item(Button(label="Get 2 Points", style=discord.ButtonStyle.red, custom_id="keepDiscForPoints"))  
        await interaction.channel.send(msg, view=view,file=file)

    @staticmethod 
    async def keepDiscForPoints(game: GamestateHelper, player_helper:PlayerHelper, interaction: discord.Interaction):
        player_helper.acquire_disc_tile_for_points()
        game.update_player(player_helper)
        await interaction.message.delete()
        await interaction.response.send_message( f"{interaction.user.mention} chose to keep the tile for 2 points")
    
    @staticmethod 
    async def usedDiscForAbility(game: GamestateHelper, player_helper:PlayerHelper, interaction: discord.Interaction, buttonID:str,player):
        disc = buttonID.split("_")[1]
        tile = buttonID.split("_")[2]
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        discName = discTile_data[disc]["name"]
        await interaction.message.delete()
        await interaction.response.send_message( f"{interaction.user.mention} chose to keep use '"+discName+"' for its ability")

        if discTile_data[disc]["part"] != "":
            await interaction.channel.send( "Adding Parts is not yet implemented")
        elif discTile_data[disc]["gain1"] != 0:
            await interaction.channel.send( "Gaining the cheapest tech is not yet implemented")
        elif discTile_data[disc]["spawn"] != 0:
            if discTile_data[disc]["spawn"] == "cruiser":
                game.add_units([player["color"]+"-"+"cru"],tile)
            if discTile_data[disc]["spawn"] == "orbital":
                game.add_units([player["color"]+"-"+"orb"],tile)
            if discTile_data[disc]["spawn"] == "monolith":
                game.add_units([player["color"]+"-"+"mon"],tile)
            if discTile_data[disc]["spawn"] == "warp":
                game.add_warp(tile)
            await interaction.channel.send( f"{interaction.user.mention} added a "+discTile_data[disc]["spawn"]+ " to tile "+tile)
            if discTile_data[disc]["material"] != 0:
                await interaction.channel.send( player_helper.adjust_materials(discTile_data[disc]["material"]))
        else:
            if discTile_data[disc]["material"] != 0:
                await interaction.channel.send( player_helper.adjust_materials(discTile_data[disc]["material"]))
            if discTile_data[disc]["science"] != 0:
                await interaction.channel.send( player_helper.adjust_materials(discTile_data[disc]["science"]))
            if discTile_data[disc]["money"] != 0:
                await interaction.channel.send( player_helper.adjust_materials(discTile_data[disc]["money"]))


        game.update_player(player_helper)
    