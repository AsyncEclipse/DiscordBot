import discord
import config
from discord.ext import commands
from discord import app_commands
from typing import Optional, List
from setup.GameInit import GameInit
from helpers.GamestateHelper import GamestateHelper
from PIL import Image, ImageDraw, ImageFont
from io import  BytesIO
import random


class SetupCommands(commands.GroupCog, name="setup"):
    def __init__(self, bot):
        self.bot = bot

    
    async def showGame(self, interaction, tileMap, game):
        context = Image.new("RGBA",(4160,5100),(255,255,255,0))
        for key,value in tileMap.items():
            context = game.drawTile(context,key, value)
        bytes = BytesIO()
        context.save(bytes,format="PNG")
        bytes.seek(0)
        file = discord.File(bytes,filename="context.png")
        await interaction.channel.send(file=file)


    @app_commands.command(name="setup_initial_tiles")
    async def setup_initial_tiles(self, interaction: discord.Interaction, player1: discord.Member, player2: Optional[discord.Member]=None, player3: Optional[discord.Member]=None, player4: Optional[discord.Member]=None, player5: Optional[discord.Member]=None, player6: Optional[discord.Member]=None):
        temp_player_list = [player1, player2, player3, player4, player5, player6]
        game = GamestateHelper(interaction.channel)
        count = 0
        for i in temp_player_list:
            if i != None:
                count = count + 1
        
        listOfTilesPos = ["201", "207","205","211","203","209"]
        if count == 3:
            listOfTilesPos = [ "201","205", "209","211","203","207",]
        listPlayerHomes = ["222","224","226","228","230","232"]
        random.shuffle(listPlayerHomes)
        listDefended = ["271","272","273","274"]
        random.shuffle(listDefended)
        mappedSectorsToPos = {}
        mappedSectorsToPos["000"] = "sector001"
        for i in range(count):
            mappedSectorsToPos[listOfTilesPos[i]]="sector"+listPlayerHomes[i]

        for i in range(6-count):
            mappedSectorsToPos[listOfTilesPos[5-i]]="sector"+listDefended[i]

        await SetupCommands.showGame(self,interaction, mappedSectorsToPos, game)


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

        await interaction.guild.create_text_channel(f'aeb.{config.game_number}')
        await interaction.response.send_message('New game created!')

    @app_commands.command(name="add_player")
    @app_commands.choices(faction=[
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
    ])
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