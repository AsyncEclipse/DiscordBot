import discord
from Buttons.Turn import TurnButtons
import config
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Button
from typing import Optional, List
from setup.GameInit import GameInit
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from PIL import Image, ImageDraw, ImageFont
from io import  BytesIO
from jproperties import Properties
import random


class SetupCommands(commands.GroupCog, name="setup"):
    def __init__(self, bot):
        self.bot = bot
    

    factionChoices = [
        app_commands.Choice(name="Hydran Progress", value="hyd"),
        app_commands.Choice(name="Eridian Empire", value="eri"),
        app_commands.Choice(name="Orion Hegemony", value="ori"),
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

    



    @app_commands.command(name="game")
    @app_commands.choices(faction1=factionChoices,faction2=factionChoices,faction3=factionChoices,faction4=factionChoices,faction5=factionChoices,faction6=factionChoices)
    async def game(self, interaction: discord.Interaction, 
                                player1: discord.Member, faction1: app_commands.Choice[str], 
                                player2: discord.Member,faction2: app_commands.Choice[str], 
                                player3: Optional[discord.Member]=None,faction3: Optional[app_commands.Choice[str]]=None, 
                                player4: Optional[discord.Member]=None, faction4: Optional[app_commands.Choice[str]]=None,
                                player5: Optional[discord.Member]=None, faction5: Optional[app_commands.Choice[str]]=None,
                                player6: Optional[discord.Member]=None, faction6: Optional[app_commands.Choice[str]]=None):
        temp_player_list = [player1, player2, player3, player4, player5, player6]
        temp_faction_list = [faction1, faction2, faction3, faction4, faction5, faction6]
        colors = ["blue", "red", "green", "yellow", "purple", "white"]
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
        random.shuffle(listPlayerHomes)
        listDefended = ["271","272","273","274"]
        random.shuffle(listDefended)
        game.add_tile("000", 0, "001")
        for i in range(count):
            rotDet = ((180 - (int(listOfTilesPos[i])-201)/2 * 60) + 360)%360
            game.add_tile(listOfTilesPos[i], rotDet, listPlayerHomes[i][0], listPlayerHomes[i][1])
        for i in range(6-count):
            rotDet = ((180 - (int(listOfTilesPos[5-i])-201)/2 * 60) + 360)%360
            game.add_tile(listOfTilesPos[5-i], rotDet, listDefended[i])
        for i in range(101, 107):
            game.add_tile(str(i), 0, "sector1back")
        for i in range(201, 213):
            if str(i) not in listOfTilesPos:
                game.add_tile(str(i), 0, "sector2back")
        for i in range(301, 319):
            game.add_tile(str(i), 0, "sector3back")
        game.setup_finished()
        game.fillInDiscTiles()
        await interaction.response.send_message("Done With Setup!")
        
        await game.showUpdate("Start of Game",interaction)
        view = TurnButtons.getStartTurnButtons(game, game.get_player(player1.id))
        await interaction.response.send_message(f"<@{player1.id}> use these buttons to do your turn. ",view=view)
        await game.displayPlayerStats(game.get_player(player1.id), interaction)

    @app_commands.command(name="cleanup")
    async def cleanup(self,interaction: discord.Interaction):
        game = GamestateHelper(interaction.channel)
        await TurnButtons.runCleanup(game, interaction)

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
        MAX_CHANNELS_PER_CATEGORY = 20  # Number of channels allowed in each category  
        async def get_or_create_category(guild:discord.Guild, category_name):  
            """Get an existing category or create a new one."""  
            for category in guild.categories:  
                if category.name == category_name:  
                    return category  
            # If category doesn't exist, create it  
            overwrites = {  
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),  # Deny access to everyone else  
            }  
            return await guild.create_category(category_name, overwrites=overwrites)  
        
        async def get_or_create_role(guild:discord.Guild, role_name):  
            for role in guild.roles:  
                if role.name == role_name:  
                    return role   
            return await guild.create_role(name=role_name)
        
        if config.game_number <= 10:  
            category_name = "Games #1-10"  
        else:  
            start = 10 * ((config.game_number - 1) // 10) + 1  
            end = start + 9  
            category_name = f"Games #{start}-{end}" 
        category = await get_or_create_category(interaction.guild, category_name)  

        role_name = f"aeb{config.game_number}"  
        role = await get_or_create_role(interaction.guild, role_name)  
        overwrites = {  
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),  
            role: discord.PermissionOverwrite(read_messages=True, manage_messages=True)
        }  
        

        for player_id in player_list:  
            member = interaction.guild.get_member(player_id[0])  
            if member:  
                await member.add_roles(role) 
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, manage_messages=True)  # Grant access to the player  

        # Create the text channels for the game  
        tabletalk = await interaction.guild.create_text_channel(f'aeb{config.game_number}-{game_name}', category=category, overwrites=overwrites)  
        actions = await interaction.guild.create_text_channel(f'aeb{config.game_number}-actions', category=category, overwrites=overwrites)  
        thread_name = f'aeb{config.game_number}-bot-map-updates'  # Choose a name for your thread  
        thread = await actions.create_thread(name=thread_name, auto_archive_duration=10080)  # Duration set to 60 minutes 
        new_game.update_num() 
        await thread.send(role.mention + " pinging you here")
        actions.send("Draft factions and turn position in the manner of your choice, then setup the game with /setup game. Enter the players in the order they should take turns in (i.e. enter first player first)")
        await interaction.response.send_message('New game created! Here are the channels: \n'+tabletalk.jump_url +"\n"+actions.jump_url)

    
    

   