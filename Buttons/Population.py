import json
import discord
from discord.ui import View
from helpers.GamestateHelper import GamestateHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button


class PopulationButtons:

    @staticmethod
    def findEmptyPopulation(game: GamestateHelper, player):
        tiles = game.get_owned_tiles(player)
        tiles.sort()
        emptyPlanets = []
        for tile in tiles:
            tileState = game.get_gamestate()["board"][tile]
            planetTypes = ["money","science","material","neutral","moneyadv","scienceadv","materialadv","neutraladv"]
            for planetT in planetTypes:
                if f"{planetT}_pop" in tileState:
                    for i,val in enumerate(tileState[f"{planetT}_pop"]):
                        if val == 0:
                            emptyPlanets.append(f"{tile}_{planetT}_{str(i)}")
            if player["color"]+"-orb" in tileState["player_ships"]:
                if "orbital_pop" not in tileState or tileState["orbital_pop"]==0:
                    emptyPlanets.append(f"{tile}_orbital_0")
        allPlayerTechs =  player["military_tech"] + player["grid_tech"] + player["nano_tech"]
        if "met" not in allPlayerTechs:
            if "adl" not in allPlayerTechs:
                emptyPlanets = [s for s in emptyPlanets if "scienceadv" not in s]
            if "adm" not in allPlayerTechs:
                emptyPlanets = [s for s in emptyPlanets if "materialadv" not in s]
            if "ade" not in allPlayerTechs:
                emptyPlanets = [s for s in emptyPlanets if "moneyadv" not in s]
            if "adl" not in allPlayerTechs and "adm" not in allPlayerTechs and "ade" not in allPlayerTechs:
                emptyPlanets = [s for s in emptyPlanets if "neutraladv" not in s]
        return emptyPlanets

    @staticmethod
    def findFullPopulation(game: GamestateHelper, player, tile :str):
        fullPlanets = []
        tileState = game.get_gamestate()["board"][tile]
        planetTypes = ["money","science","material","neutral","moneyadv","scienceadv","materialadv","neutraladv","orbital"]
        for planetT in planetTypes:
            if f"{planetT}_pop" in tileState:
                for i,val in enumerate(tileState[f"{planetT}_pop"]):
                    if val > 0:
                        fullPlanets.append(f"{planetT}")
        return fullPlanets
    @staticmethod
    async def startPopDrop(game: GamestateHelper, player, interaction: discord.Interaction):
        view = View()
        for pop in PopulationButtons.findEmptyPopulation(game, player):
            tile = pop.split("_")[0]
            planetT = pop.split("_")[1]
            buttonID = f"FCID{player['color']}_fillPopulation_"+pop
            adv = "adv" in planetT
            planetT = planetT.replace("adv","")
            label = planetT.capitalize()
            if adv:
                label = "Advanced " + label
            label = label + f" (tile {tile})"
            view.add_item(Button(label=label, style=discord.ButtonStyle.blurple, custom_id=buttonID))
        await interaction.channel.send( f"{interaction.user.mention}, choose which planet you would like to put a population cube on.", view=view)
    @staticmethod
    async def fillPopulation(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        tile = buttonID.split("_")[1]
        typeOfPop = buttonID.split("_")[2]
        originalPop = buttonID.split("_")[2]
        num = buttonID.split("_")[3]
        if "neutral" in typeOfPop or "orbital" in typeOfPop:
            if len(buttonID.split("_")) < 5:
                allPlayerTechs =  player["military_tech"] + player["grid_tech"] + player["nano_tech"]
                optionsForPop = ["money","science","material"]
                if "orbital" in typeOfPop:
                    optionsForPop = ["money","science"]
                if "adv" in typeOfPop:
                    if "met" not in allPlayerTechs:
                        if "adl" not in allPlayerTechs:
                            optionsForPop.remove("science")
                        if "adm" not in allPlayerTechs:
                            optionsForPop.remove("material")
                        if "ade" not in allPlayerTechs:
                            optionsForPop.remove("money")
                if len(optionsForPop) > 1:
                    view = View()
                    for typeP in optionsForPop:
                        view.add_item(Button(label=typeP.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_fillPopulation_{tile}_{originalPop}_{num}_{typeP}"))
                    await interaction.message.delete()
                    await interaction.channel.send(f"{interaction.user.mention}, choose which type of resource the population should be.", view=view)
                    return
                else:
                    typeOfPop = optionsForPop[0]
            else:
                typeOfPop = buttonID.split("_")[4]
        if not game.add_pop_specific(originalPop,typeOfPop,int(num),tile,game.get_player_from_color(player["color"])):
            await interaction.channel.send(f"Did not have enough colony ships so failed to add {typeOfPop} pop to tile {tile}")
            return
        await interaction.message.delete()
        drawing = DrawHelper(game.gamestate)
        await interaction.channel.send(f"Successfully added a {typeOfPop.replace('adv','')} population to tile {tile}", file=drawing.board_tile_image_file(tile))




