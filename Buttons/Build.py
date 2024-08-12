import json
import discord
from discord.ext import commands
from discord.ui import View
from Buttons.Turn import TurnButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from discord.ext import commands
from commands import tile_commands
from commands.setup_commands import SetupCommands
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties

class BuildButtons:
    
    @staticmethod  
    async def startBuild(game: GamestateHelper, player, interaction: discord.Interaction):  
        tiles = game.get_owned_tiles(player)
        tiles.sort()
        view = View()
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.primary, custom_id=f"FCID{player["color"]}_buildIn_{tile}"))
        await interaction.response.send_message(f"{interaction.user.mention}, choose which tile you would like to build in.", view=view)

    @staticmethod  
    async def buildIn(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        loc = buttonID.split("_")[1]
        view = View()
        view = BuildButtons.buildBuildButtonsView(interaction,"",0,loc,view,player)
        await interaction.message.delete()
        await interaction.response.send_message(f"{interaction.user.mention}, you have {player['materials']} materials to "
                                                f"spend on up to {player['build_apt']} units in this system.", view=view)
        
    @staticmethod  
    async def buildShip(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1].replace("none","").split(f';')
        if "" in build:
            build.remove("")
        cost = int(buttonID.split("_")[2])
        loc = buttonID.split("_")[3]
        ship = str(buttonID.split("_")[4])
        if len(build) == player["build_apt"]:
            await interaction.response.edit_message(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {build} for {cost} materials.")
            return
        build.append(f"{player['color']}-{GamestateHelper.getShipShortName(ship)}")
        key = f"cost_{ship.lower()}"
        if ship.lower() == "dreadnought":
            key = f"cost_dread"
        cost += player[key]
        view = View()
        view = BuildButtons.buildBuildButtonsView(interaction,";".join(build),cost,loc,view,player)
        await interaction.response.edit_message(content=f"Total cost so far of {cost}", view=view)

    @staticmethod
    def buildBuildButtonsView(interaction: discord.Interaction, build: str, cost, build_loc, view: View,player):
        ships = ["Interceptor","Cruiser","Dreadnought","Starbase","Orbital","Monolith"]
        if build == "":
            build = "none"
        game = GamestateHelper(interaction.channel)
        if "stb" not in player["military_tech"]:
            ships.remove("Starbase")
        if "orb" not in player["nano_tech"]:
            ships.remove("Orbital")
        if "mon" not in player["nano_tech"]:
            ships.remove("Monolith")
        for ship in ships:
            key = f"cost_{ship.lower()}"
            if ship.lower() == "dreadnought":
                key = f"cost_dread"
            buttonElements = [f"FCID{player["color"]}","buildShip", build, str(cost), build_loc, ship]
            view.add_item(Button(label=f"{ship} ({player[f'{key}']})", style=discord.ButtonStyle.primary, custom_id="_".join(buttonElements))) 
        buttonElements = [f"FCID{player["color"]}","finishBuild", build, str(cost), build_loc]
        view.add_item(Button(label="Finished", style=discord.ButtonStyle.red, custom_id="_".join(buttonElements))) 
        view.add_item(Button(label="Reset", style=discord.ButtonStyle.gray, custom_id=f"buildIn_{build_loc}")) 
        return view
    

    @staticmethod  
    async def finishBuild(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1].replace("none","").split(f';')
        cost = buttonID.split("_")[2]
        loc = buttonID.split("_")[3]
        view = View()
        view = BuildButtons.buildBuildSpendButtonsView(game, interaction,player, ";".join(build),cost,loc,view,str(player['materials']),str(player['science']),str(player['money']),"0" )
        await interaction.message.delete()
        await interaction.response.send_message(f"Total cost: {cost}"
                    f"\nAvailable resources: Materials-{player['materials']} Science-{player['science']} Money-{player['money']}", view=view)

    @staticmethod  
    async def spendMaterial(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1]
        cost = buttonID.split("_")[2]
        loc = buttonID.split("_")[3]
        material = int(buttonID.split("_")[4])
        science = buttonID.split("_")[5]
        money = buttonID.split("_")[6]
        spent = int(buttonID.split("_")[7])
        matSpent = int(buttonID.split("_")[8])
        material -=matSpent
        spent += matSpent
        material = str(material)
        spent = str(spent)
        view = View()
        view = BuildButtons.buildBuildSpendButtonsView(game, interaction,player,build,cost,loc,view, material, science, money, spent)
        await interaction.response.edit_message(content=f"Total cost: {cost}"
                    f"\nAvailable resources: Materials-{material} Science-{science} Money-{money}"
                    f"\nResources spent: {spent}", view=view)
    async def convertResource(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1]
        cost = buttonID.split("_")[2]
        loc = buttonID.split("_")[3]
        material = buttonID.split("_")[4]
        science = int(buttonID.split("_")[5])
        money = int(buttonID.split("_")[6])
        spent = int(buttonID.split("_")[7])
        resource = buttonID.split("_")[8]
        spent += 1
        if resource == "Science":
            science -= player["trade_value"]
        else:
            money -= player["trade_value"]
        science = str(science)
        money = str(money)
        spent = str(spent)
        view = View()
        view = BuildButtons.buildBuildSpendButtonsView(game, interaction,player,build,cost,loc,view, material, science, money, spent)
        await interaction.response.edit_message(content=f"Total cost: {cost}"
                    f"\nAvailable resources: Materials-{material} Science-{science} Money-{money}"
                    f"\nResources spent: {spent}", view=view)

    @staticmethod
    def buildBuildSpendButtonsView(game: GamestateHelper, interaction: discord.Interaction,player, build: str, cost:str, build_loc:str, view: View, material:str, science:str, money:str, spent:str):
        for i in range(2):
            x = i+1
            buttonElements = [f"FCID{player["color"]}","spendMaterial", build, str(cost), build_loc, material, science, money, spent, str(x)]
            if player['materials'] >= x:
                view.add_item(Button(label=f"Materials ({str(x)})", style=discord.ButtonStyle.blurple, custom_id="_".join(buttonElements))) 

        elements = ["Science","Money"]
        tradeVal = player['trade_value']
        for resource in elements:
            buttonElements = [f"FCID{player["color"]}","convertResource", build, str(cost), build_loc, material, science, money, spent, resource]
            if resource == "Science":
                if int(science) >= tradeVal:
                    view.add_item(Button(label=f"{resource} ({str(tradeVal)}:1)", style=discord.ButtonStyle.gray, custom_id="_".join(buttonElements))) 
            if resource == "Money":
                if int(money) >= tradeVal:
                    view.add_item(Button(label=f"{resource} ({str(tradeVal)}:1)", style=discord.ButtonStyle.gray, custom_id="_".join(buttonElements))) 

        buttonElements = [f"FCID{player["color"]}","finishSpendForBuild", build, build_loc, material, science, money]
        if int(spent) >= int(cost):
            view.add_item(Button(label="Finish Build", style=discord.ButtonStyle.red, custom_id="_".join(buttonElements))) 
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player["color"]}_restartTurn")) 
        return view

    @staticmethod  
    async def finishSpendForBuild(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str, player_helper : PlayerHelper):
        build = buttonID.split("_")[1].replace("none","").split(f';')
        loc = buttonID.split("_")[2]
        material = int(buttonID.split("_")[3])
        science = int(buttonID.split("_")[4])
        money = int(buttonID.split("_")[5])
        game.add_units(build, loc)
        player_helper.stats["science"], player_helper.stats["materials"], player_helper.stats["money"] = science, material, money
        player_helper.spend_influence_on_action("build")
        game.update_player(player_helper)
        next_player = game.get_next_player(player)
        view = TurnButtons.getStartTurnButtons(game, game.get_player(next_player))
        await interaction.message.delete()
        await interaction.response.send_message(f"<@{next_player}> use these buttons to do your turn. ",view=view)
        