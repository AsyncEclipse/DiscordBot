import json
import random

import discord
from discord.ui import View, Button
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.ShipHelper import AI_Ship, PlayerShip

class Combat:

    @staticmethod
    def findPlayersInTile(game:GamestateHelper,pos:str):
        tile_map = game.get_gamestate()["board"]
        if "player_ships" not in tile_map[pos]:
            return []
        player_ships = tile_map[pos]["player_ships"][:]
        players = []
        for ship in player_ships:
            if "orb" in ship or "mon" in ship:
                continue
            color = ship.split("-")[0]
            if color not in players:
                players.append(color)
        return players
    
    @staticmethod
    def findTilesInConflict(game:GamestateHelper):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if len(Combat.findPlayersInTile(game,tile)) > 1:
                tiles.append((int(tile_map[tile]["sector"]),tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)  
        return sorted_tiles
    @staticmethod
    async def startCombatThreads(game:GamestateHelper, interaction:discord.Interaction):
        channel = interaction.channel
        role = discord.utils.get(interaction.guild.roles, name=game.get_gamestate()["game_id"])  
        tiles = Combat.findTilesInConflict(game)
        for tile in tiles:
            message_to_send = "Combat will occur in system "+str(tile[0])+", position "+tile[1]  
            message = await channel.send(message_to_send) 
            threadName = game.get_gamestate()["game_id"]+"-Round "+str(game.get_gamestate()["roundNum"])+", Tile "+tile[1]+", Combat"
            thread = await message.create_thread(name=threadName)
            drawing = DrawHelper(game.gamestate)
            await thread.send(role.mention +"Combat will occur in this tile",view = Combat.getCombatButtons(game, tile[1]),file=drawing.board_tile_image_file(tile[1]))
        await channel.send("Please resolve the combats in the order they appeared")
    @staticmethod
    def getCombatantShipsBySpeed(game:GamestateHelper, colorOrAI:str, playerShipsList):
        ships = []
        for unit in playerShipsList:
            type = unit.split("-")[1]
            owner = unit.split('-')[0]
            if type == "orb" or type == "mon":
                continue
            if colorOrAI == owner:
                if colorOrAI == "ai":
                    ship = AI_Ship(unit, game.gamestate["advanced_ai"])
                    ships.append((ship.speed, unit))
                else:
                    player = game.get_player_from_color(colorOrAI)
                    ship = PlayerShip(game.gamestate["players"][player], type)
                    ships.append((ship.speed, type))
        sorted_ships = sorted(ships, key=lambda x: x[0], reverse=True)  
        sorted_ships_grouped = []
        seen_ships = []
        for ship in sorted_ships:
            if ship[1] not in seen_ships:
                seen_ships.append(ship[1])
                amount = 0
                for ship2 in sorted_ships:
                    if ship[1]==ship2[1]:
                        amount += 1
                sorted_ships_grouped.append((ship[0], ship[1], amount))
            
        return sorted_ships_grouped
    
    @staticmethod
    def doesCombatantHaveMissiles(game:GamestateHelper, colorOrAI:str, playerShipsList):
        for unit in playerShipsList:
            type = unit.split("-")[1]
            owner = unit.split('-')[0]
            if type == "orb" or type == "mon":
                continue
            if colorOrAI == owner:
                if colorOrAI == "ai":
                    ship = AI_Ship(unit, game.gamestate["advanced_ai"])
                    if len(ship.missile) > 0:
                        return True
                else:
                    player = game.get_player_from_color(colorOrAI)
                    ship = PlayerShip(game.gamestate["players"][player], type)
                    if len(ship.missile) > 0:
                        return True
        return False

    @staticmethod
    def getCombatantSpeeds(game:GamestateHelper, colorOrAI:str, playerShipsList):
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, playerShipsList)
        speeds =[]
        for ship in ships:
            if ship[0] not in speeds:
                speeds.append(ship[0])
        return speeds
    
    @staticmethod
    def getCombatButtons(game:GamestateHelper, pos:str):
        view = View()
        players = Combat.findPlayersInTile(game, pos)
        if len(players) > 1:
            defender = players[len(players)-2]
            attacker = players[len(players)-1]
            tile_map = game.get_gamestate()["board"]
            player_ships = tile_map[pos]["player_ships"][:]
            defenderSpeeds = Combat.getCombatantSpeeds(game, defender, player_ships)
            attackerSpeeds = Combat.getCombatantSpeeds(game, attacker, player_ships)
            if Combat.doesCombatantHaveMissiles(game, defender, player_ships):
                view.add_item(Button(label="(Defender) Roll Missiles", style=discord.ButtonStyle.green, custom_id=f"rollMissiles_{pos}_{defender}"))
            if Combat.doesCombatantHaveMissiles(game, attacker, player_ships):
                view.add_item(Button(label="(Attacker) Roll Missiles", style=discord.ButtonStyle.red, custom_id=f"rollMissiles_{pos}_{attacker}"))
            for i in range(20,-1,-1):
                if i in defenderSpeeds:
                    checker = ""
                    if defender != "ai":
                        checker="FCID"+defender+"_"
                    view.add_item(Button(label="(Defender) Roll Initative "+str(i)+" Ships", style=discord.ButtonStyle.green, custom_id=f"{checker}rollDice_{pos}_{defender}_{str(i)}"))
                if i in attackerSpeeds:
                    checker="FCID"+attacker+"_"
                    view.add_item(Button(label="(Attacker) Roll Initative "+str(i)+" Ships", style=discord.ButtonStyle.red, custom_id=f"{checker}rollDice_{pos}_{attacker}_{str(i)}"))
        view.add_item(Button(label="Refresh Image", style=discord.ButtonStyle.blurple, custom_id=f"refreshImage_{pos}"))
        view.add_item(Button(label="Remove Units", style=discord.ButtonStyle.gray, custom_id=f"removeUnits_{pos}"))
        return view
    
    @staticmethod
    def getRemovalButtons(game:GamestateHelper, pos:str, player):
        view = View()
        players = Combat.findPlayersInTile(game, pos)
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        shownShips = []
        checker="FCID"+player["color"]+"_"
        for ship in player_ships:
            if ship not in shownShips:
                shownShips.append(ship)
                owner = ship.split("-")[0]
                type = ship.split("-")[1]
                view.add_item(Button(label="Remove "+owner+" "+Combat.translateShipAbrToName(type), style=discord.ButtonStyle.red, custom_id=f"{checker}removeThisUnit_{pos}_{ship}"))
        view.add_item(Button(label="Delete This", style=discord.ButtonStyle.red, custom_id=f"deleteMsg"))
        return view
    
    @staticmethod
    async def removeUnits(game:GamestateHelper, customID:str, player, interaction:discord.Interaction):
        pos = customID.split("_")[1]
        view = Combat.getRemovalButtons(game, pos, player)
        await interaction.channel.send(interaction.user.mention+" use buttons to remove units",view=view)
    
    @staticmethod
    async def removeThisUnit(game:GamestateHelper, customID:str, player, interaction:discord.Interaction):
        pos = customID.split("_")[1]
        unit =  customID.split("_")[2]
        owner = unit.split("-")[0]
        game.remove_units([unit],pos)
        await interaction.channel.send(interaction.user.mention+" removed 1 "+owner+" "+Combat.translateShipAbrToName(unit))
        view = Combat.getRemovalButtons(game, pos, player)
        await interaction.message.edit(view=view)


    @staticmethod
    async def rollDice(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = int(buttonID.split("_")[3])
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships)
        drawing = DrawHelper(game.gamestate)
        for ship in ships:
            if ship[0] == speed:
                name = interaction.user.mention
                if colorOrAI == "ai":
                    shipModel = AI_Ship(ship[1], game.gamestate["advanced_ai"])
                    name = "The AI"
                else:
                    player = game.get_player_from_color(colorOrAI)
                    shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
                dice = shipModel.dice
                msg = name + " rolled the following with their "+str(ship[2])+" "+Combat.translateShipAbrToName(ship[1])+"(s):\n"
                dieFiles = []
                for x in range(ship[2]):
                    for die in dice:
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1","Miss").replace("6",":boom:")
                        msg +=num+" "
                        dieFiles.append(drawing.get_file("images/resources/components/dice_faces/dice_"+Combat.translateColorToName(die)+"_"+str(random_number)+".png"))
                if shipModel.computer > 0:
                    msg = msg + "\nThis ship type has a +"+str(shipModel.computer)+" computer"
                await interaction.channel.send(msg,files=dieFiles)
    @staticmethod
    async def rollMissiles(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships)
        drawing = DrawHelper(game.gamestate)
        for ship in ships:
            name = interaction.user.mention
            if colorOrAI == "ai":
                shipModel = AI_Ship(ship[1], game.gamestate["advanced_ai"])
                name = "The AI"
            else:
                player = game.get_player_from_color(colorOrAI)
                shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
            dice = shipModel.missile
            if(len(dice) > 0):
                msg = name + " rolled the following missiles with their "+Combat.translateShipAbrToName(ship[1])+":\n"
                dieFiles = []
                for die in dice:
                    random_number = random.randint(1, 6)
                    msg +=str(random_number)+" "
                    dieFiles.append(drawing.get_file("images/resources/components/dice_faces/dice_"+Combat.translateColorToName(die)+"_"+str(random_number)+".png"))
                if shipModel.computer > 0:
                    msg = msg + "\nThe ship has a +"+str(shipModel.computer)+" computer"
                await interaction.channel.send(msg,files=dieFiles)
    @staticmethod
    async def refreshImage(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        drawing = DrawHelper(game.gamestate)
        await interaction.channel.send("Updated view",view = Combat.getCombatButtons(game, pos),file=drawing.board_tile_image_file(pos))

    @staticmethod
    def translateColorToName(dieColor:str):
        if dieColor == "red":
            return "antimatter"
        if dieColor == "orange":
            return "plasma"
        if dieColor == "blue":
            return "soliton"
        return "ion"
    @staticmethod
    def translateShipAbrToName(ship:str):
        if "-" in ship:
            ship = ship.split("-")[1]
        ship = ship.replace("adv","").replace("ai-","")
        if ship == "int":
            return "interceptor"
        elif ship == "cru":
            return "cruiser"
        elif ship == "drd" or ship == "dreadnought":
            return "dread"
        elif ship == "sb":
            return "starbase"
        elif ship == "anc":
             return "Ancient"
        elif ship == "gcds":
             return "GCDS"
        elif ship == "grd":
             return "Guardian"
        return ship