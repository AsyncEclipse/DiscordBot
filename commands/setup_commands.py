import discord
import config
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional, List
from setup.GameInit import GameInit
from helpers.GamestateHelper import GamestateHelper
from PIL import Image, ImageDraw, ImageFont
from io import  BytesIO
import random


class SetupCommands(commands.GroupCog, name="setup"):
    def __init__(self, bot):
        self.bot = bot
    

    factionChoices = [
        app_commands.Choice(name="Hydran Progress", value="hyd"),
        app_commands.Choice(name="Eridian Empire", value="eri"),
        app_commands.Choice(name="Orian Hegemony", value="ori"),
        app_commands.Choice(name="Descendants of Draco", value="dra"),
        app_commands.Choice(name="Mechanema", value="mec"),
        app_commands.Choice(name="Planta", value="pla"),
        app_commands.Choice(name="Terran Alliance", value="ter1"),
        app_commands.Choice(name="Terran Conglomerate", value="ter2"),
        app_commands.Choice(name="Terran Directorate", value="ter3"),
        app_commands.Choice(name="Terran Federation", value="ter4"),
        app_commands.Choice(name="Terran Republic", value="ter5"),
        app_commands.Choice(name="Terran Union", value="ter6"),
    ]
   
    async def on_interaction(interaction):
        if interaction.custom_id == "showGame":
            await interaction.response.send_message("Button clicked!")

    @staticmethod 
    async def showGame(interaction, game):
        await interaction.response.defer(thinking=True)  
        context = Image.new("RGBA",(4160,5100),(255,255,255,0))
        tileMap = game.get_gamestate()["board"]
        for i in tileMap:
            context = game.drawTile(context, i, tileMap[i]["sector"], tileMap[i]["orientation"])
        #for key,value in tileMap.items():
        #    tile_image, rotation_value = value
        #    context = game.drawTile(context,key, tile_image, rotation_value)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="mapImage.png")
        await interaction.followup.send(file=file)
        view = View()
        button = Button(label="Show Game",style=discord.ButtonStyle.primary, custom_id="showGame")
        view.add_item(button)
        await interaction.channel.send(view=view)
    



    @app_commands.command(name="setup_game")
    @app_commands.choices(faction1=factionChoices,faction2=factionChoices,faction3=factionChoices,faction4=factionChoices,faction5=factionChoices,faction6=factionChoices)
    async def setup_game(self, interaction: discord.Interaction, 
                                player1: discord.Member, faction1: app_commands.Choice[str], 
                                player2: Optional[discord.Member]=None,faction2: Optional[app_commands.Choice[str]]=None, 
                                player3: Optional[discord.Member]=None,faction3: Optional[app_commands.Choice[str]]=None, 
                                player4: Optional[discord.Member]=None, faction4: Optional[app_commands.Choice[str]]=None,
                                player5: Optional[discord.Member]=None, faction5: Optional[app_commands.Choice[str]]=None,
                                player6: Optional[discord.Member]=None, faction6: Optional[app_commands.Choice[str]]=None):
        temp_player_list = [player1, player2, player3, player4, player5, player6]
        temp_faction_list = [faction1, faction2, faction3, faction4, faction5, faction6]
        colors = ["blue", "red", "green", "yellow", "black", "white"]
        game = GamestateHelper(interaction.channel)
        count = 0
        listPlayerHomes=[]
        x = -1
        for i in temp_player_list:
            x = x+1
            if i != None and temp_faction_list[x] != None:
                player = i
                faction = temp_faction_list[x]
                player_color = colors.pop(0)
                game.player_setup(player.id, faction.value, player_color)
                home = game.get_player(player.id)["home_planet"]
                listPlayerHomes.append([home, player_color])
                count = count + 1
        
        listOfTilesPos = ["201", "207","205","211","203","209"]
        if count == 3:
            listOfTilesPos = [ "201","205", "209","211","203","207",]
       # listPlayerHomes = ["222","224","226","228","230","232"]
        random.shuffle(listPlayerHomes)
        listDefended = ["271","272","273","274"]
        random.shuffle(listDefended)
        game.add_tile("000", 0, "001")
        #mappedSectorsToPos = {}
        #mappedSectorsToPos["000"] = ("001",0)
        for i in range(count):
            rotDet = ((180 - (int(listOfTilesPos[i])-201)/2 * 60) + 360)%360
            game.add_tile(listOfTilesPos[i], rotDet, listPlayerHomes[i][0], listPlayerHomes[i][1])
            #mappedSectorsToPos[listOfTilesPos[i]]=(listPlayerHomes[i],rotDet)
        for i in range(6-count):
            rotDet = ((180 - (int(listOfTilesPos[5-i])-201)/2 * 60) + 360)%360
            game.add_tile(listOfTilesPos[5-i], rotDet, listDefended[i])
            #mappedSectorsToPos[listOfTilesPos[5-i]]=(listDefended[i],rotDet)
        for i in range(101, 107):
            game.add_tile(str(i), 0, "sector1back")
        #    mappedSectorsToPos[str(i)]=("sector1back",0)
        for i in range(201, 213):
            if str(i) not in listOfTilesPos:
                game.add_tile(str(i), 0, "sector2back")
        #     if str(i) not in listOfTilesPos:
        #        mappedSectorsToPos[str(i)]=("sector2back",0)
        for i in range(301, 319):
            game.add_tile(str(i), 0, "sector3back")
        #    mappedSectorsToPos[str(i)]=("sector3back",0)
        #game.updateTileList(mappedSectorsToPos)
        #await interaction.response.send_message("done")
        await SetupCommands.showGame(interaction,game)


    @app_commands.command(name="new_game")
    async def new_game(self, interaction: discord.Interaction, game_name: str,
                            player1: discord.Member,
                            player2: Optional[discord.Member]=None,
                            player3: Optional[discord.Member]=None,
                            player4: Optional[discord.Member]=None,
                            player5: Optional[discord.Member]=None,
                            player6: Optional[discord.Member]=None):
        temp_player_list = [player1, player2, player3, player4, player5, player6]
        player_list = []

        for i in temp_player_list:
            if i != None:
                player_list.append([i.id, i.name])

        new_game = GameInit(game_name, player_list)
        new_game.create_game()

        await interaction.guild.create_text_channel(f'aeb{config.game_number}')
        await interaction.response.send_message('New game created!')

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


    @app_commands.command(name="add_player")
    @app_commands.choices(faction=factionChoices)
    async def add_player(self, interaction: discord.Interaction, player: discord.Member, faction: app_commands.Choice[str]):

        game = GamestateHelper(interaction.channel)
       #try:
        await interaction.response.send_message(game.player_setup(player.id, faction.value))
        #except KeyError:
        #    await interaction.response.send_message("That player is not in this game.")

    @app_commands.command(name="complete")
    async def complete(self, interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await interaction.response.send_message(game.setup_finished())