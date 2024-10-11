
import discord
from discord.ui import View
from Buttons.Turn import TurnButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button


class BuildButtons:
    
    @staticmethod  
    async def startBuild(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str, player_helper:PlayerHelper):  
        tiles = game.get_owned_tiles(player)
        tiles.sort()
        view = View()
        await interaction.channel.send(f"{interaction.user.mention} is using their turn to build")
        if "2" not in buttonID:
            player_helper.spend_influence_on_action("build")
            game.update_player(player_helper)
            await interaction.message.delete()
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_buildIn_{tile}"))
        await interaction.channel.send(f"{interaction.user.mention}, choose which tile you would like to build in.", view=view)

    @staticmethod  
    async def buildIn(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        loc = buttonID.split("_")[1]
        view = View()
        view = BuildButtons.buildBuildButtonsView(interaction,"",0,loc,view,player)
        await interaction.message.delete()
        buildApt = player["build_apt"]
        if player["passed"]== True:
            buildApt = 1
        await interaction.channel.send(f"{interaction.user.mention}, you have {player['materials']} materials to "
                                                f"spend on up to {str(buildApt)} units in this system.", view=view)
        
    @staticmethod  
    async def buildShip(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        build = buttonID.split("_")[1].replace("none","").split(f';')
        if "" in build:
            build.remove("")
        cost = int(buttonID.split("_")[2])
        loc = buttonID.split("_")[3]
        ship = str(buttonID.split("_")[4])
        buildApt = player["build_apt"]
        if player["passed"]== True:
            buildApt = 1
        if len(build) == buildApt:
            await interaction.message.edit(content=f"You cannot build any more units. Current build is:"
                                                            f"\n {build} for {cost} materials.")
            return
        build.append(f"{player['color']}-{GamestateHelper.getShipShortName(ship)}")
        key = f"cost_{ship.lower()}"
        if ship.lower() == "dreadnought":
            key = f"cost_dread"
        cost += player[key]
        view = View()
        view = BuildButtons.buildBuildButtonsView(interaction,";".join(build),cost,loc,view,player)
        await interaction.message.edit(content=f"Total cost so far of {cost}", view=view)

    @staticmethod
    def buildBuildButtonsView(interaction: discord.Interaction, build: str, cost, build_loc, view: View,player):
        ships = ["Interceptor","Cruiser","Dreadnought","Starbase","Orbital","Monolith"]
        if build == "":
            build = "none"
        game = GamestateHelper(interaction.channel)
        shipsShort = ["int","cru","drd","sb"]
        ultimateC = 0
                
        if "stb" not in player["military_tech"]:
            ships.remove("Starbase")
        if "orb" not in player["nano_tech"]or "orb" in build:
            ships.remove("Orbital")
        if "mon" not in player["nano_tech"] or "mon" in build:
            ships.remove("Monolith")
        for counter,ship in enumerate(ships):
            key = f"cost_{ship.lower()}"
            remaining = 10
            if counter < len(player["ship_stock"]):
                remaining = player["ship_stock"][counter]
                if shipsShort[counter] in build:
                    remaining -= build.count(shipsShort[counter])
            if ship.lower() == "dreadnought":
                key = f"cost_dread"
            buttonElements = [f"FCID{player['color']}","buildShip", build, str(cost), build_loc, ship]
            if remaining > 0:
                view.add_item(Button(label=f"{ship} ({player[f'{key}']})", style=discord.ButtonStyle.blurple, custom_id="_".join(buttonElements))) 
        buttonElements = [f"FCID{player['color']}","finishBuild", build, str(cost), build_loc]
        view.add_item(Button(label="Finished In This System", style=discord.ButtonStyle.red, custom_id="_".join(buttonElements))) 
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
        await interaction.channel.send(f"Total cost: {cost}"
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
        await interaction.message.edit(content=f"Total cost: {cost}"
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
        await interaction.message.edit(content=f"Total cost: {cost}"
                    f"\nAvailable resources: Materials-{material} Science-{science} Money-{money}"
                    f"\nResources spent: {spent}", view=view)

    @staticmethod
    def buildBuildSpendButtonsView(game: GamestateHelper, interaction: discord.Interaction,player, build: str, cost:str, build_loc:str, view: View, material:str, science:str, money:str, spent:str):
        num = min(int(cost),int(material))
        buttonElements = [f"FCID{player['color']}","spendMaterial", build, str(cost), build_loc, material, science, money, spent, str(num)]
        if num > 0 and int(spent) < int(cost):
            view.add_item(Button(label=f"Materials ({str(num)})", style=discord.ButtonStyle.blurple, custom_id="_".join(buttonElements))) 

        elements = ["Science","Money"]
        tradeVal = player['trade_value']
        for resource in elements:
            buttonElements = [f"FCID{player['color']}","convertResource", build, str(cost), build_loc, material, science, money, spent, resource]
            if resource == "Science":
                if int(science) >= tradeVal and int(spent) < int(cost):
                    view.add_item(Button(label=f"{resource} ({str(tradeVal)}:1)", style=discord.ButtonStyle.gray, custom_id="_".join(buttonElements))) 
            if resource == "Money":
                if int(money) >= tradeVal and int(spent) < int(cost):
                    view.add_item(Button(label=f"{resource} ({str(tradeVal)}:1)", style=discord.ButtonStyle.gray, custom_id="_".join(buttonElements))) 

        buttonElements = [f"FCID{player['color']}","finishSpendForBuild", build, build_loc, material, science, money]
        if int(spent) >= int(cost):
            view.add_item(Button(label="Finish Build In This System", style=discord.ButtonStyle.red, custom_id="_".join(buttonElements))) 
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_restartTurn"))
        return view

    @staticmethod  
    async def finishSpendForBuild(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str, player_helper : PlayerHelper):
        build = buttonID.split("_")[1].replace("none","").split(f';')
        loc = buttonID.split("_")[2]
        material = int(buttonID.split("_")[3])
        science = int(buttonID.split("_")[4])
        money = int(buttonID.split("_")[5])
        game.add_units(build, loc)
        summary = ""
        for ship in build:
            shortName = ship.split("-")[1]
            summary += " "+game.getShipFullName(shortName)
        player_helper.specifyDetailsOfAction("Built "+summary+" in "+loc+".")
        player_helper.stats["science"], player_helper.stats["materials"], player_helper.stats["money"] = science, material, money
        game.update_player(player_helper)
        drawing = DrawHelper(game.gamestate)
        buildApt = player["build_apt"]
        await interaction.channel.send(f"This is what the tile looks like after the build. ",file=drawing.board_tile_image_file(loc))
        if player["passed"]== True:
            buildApt = 1
        view2 = View()
        if len(build) < buildApt:
            view2.add_item(Button(label="Build Somewhere Else", style=discord.ButtonStyle.red, custom_id="startBuild2"))  
        view2.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.channel.send(f"{interaction.user.mention} use buttons to finish turn or potentially build somewhere else.", view=view2)
        await interaction.message.delete()
        