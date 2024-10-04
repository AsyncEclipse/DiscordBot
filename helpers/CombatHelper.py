import json
import random

import discord
from discord.ui import View, Button
from Buttons.Reputation import ReputationButtons
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
    def findShipTypesInTile(game:GamestateHelper,pos:str):
        tile_map = game.get_gamestate()["board"]
        if "player_ships" not in tile_map[pos]:
            return []
        player_ships = tile_map[pos]["player_ships"][:]
        ships = []
        for ship in player_ships:
            if "orb" in ship or "mon" in ship:
                continue
            shipType = ship.split("-")[1]
            if shipType not in ships:
                ships.append(shipType)
        return ships
    
    @staticmethod
    def findTilesInConflict(game:GamestateHelper):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if len(Combat.findPlayersInTile(game,tile)) > 1:
                #Dont start combat between draco and ancients
                if(len(Combat.findPlayersInTile(game,tile)) == 2 and "anc" in Combat.findShipTypesInTile(game,tile) and "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game,tile)[1])):
                    continue
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
            drawing = DrawHelper(game.gamestate)
            for player in Combat.findPlayersInTile(game, tile[1]):
                if player != "ai":
                    image = drawing.player_area(game.getPlayerObjectFromColor(player))
                    file=drawing.show_player_ship_area(image)
                    await thread.send(game.getPlayerObjectFromColor(player)["player_name"]+" ships look like this",file=file)
                else:
                    file = drawing.show_AI_stats()
                    await thread.send("AI stats look like this",file=file)
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
    def getOpponentUnitsThatCanBeHit(game:GamestateHelper, colorOrAI:str,playerShipsList, dieVal:int, computerVal:int, pos:str):
        players = Combat.findPlayersInTile(game, pos)
        opponent = ""
        hittableShips = []
        if len(players) < 2:
            return hittableShips
        if colorOrAI == players[len(players)-1]:
            opponent = players[len(players)-2]
        else:
            opponent = players[len(players)-1]
        
        opponentShips = Combat.getCombatantShipsBySpeed(game, opponent, playerShipsList)
        for ship in opponentShips:
            if opponent == "ai":
                shipModel = AI_Ship(ship[1], game.gamestate["advanced_ai"])
            else:
                player = game.get_player_from_color(opponent)
                shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
            shieldVal = shipModel.shield
            if dieVal == 6 or dieVal + computerVal - shieldVal > 5:
                ship_type = ship[1]
                if "-" in ship_type:
                    temp = ship_type.split("-")
                    ship = temp[1]
                hittableShips.append(opponent+"-"+ship.replace("adv",""))
        return hittableShips
    
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
                view.add_item(Button(label="(Defender) Roll Missiles", style=discord.ButtonStyle.green, custom_id=f"rollDice_{pos}_{defender}_99"))
            if Combat.doesCombatantHaveMissiles(game, attacker, player_ships):
                view.add_item(Button(label="(Attacker) Roll Missiles", style=discord.ButtonStyle.red, custom_id=f"rollDice_{pos}_{defender}_99"))
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
        oldLength = len(Combat.findPlayersInTile(game, pos))
        owner = unit.split("-")[0]
        game.remove_units([unit],pos)
        if owner == "ai":
            owner = "AI"
        await interaction.channel.send(interaction.user.mention+" removed 1 "+owner+" "+Combat.translateShipAbrToName(unit))
        view = Combat.getRemovalButtons(game, pos, player)
        await interaction.message.edit(view=view)
        if len(Combat.findPlayersInTile(game, pos)) < 2 and len(Combat.findPlayersInTile(game, pos)) != oldLength:
            actions_channel = discord.utils.get(interaction.guild.channels, name=game.game_id+"-actions") 
            if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
                await actions_channel.send("Combat in tile "+pos+" has concluded. There are "+str(len(Combat.findTilesInConflict(game)))+" tiles left in conflict")


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
            if ship[0] == speed or speed == 99:
                name = interaction.user.mention
                if colorOrAI == "ai":
                    shipModel = AI_Ship(ship[1], game.gamestate["advanced_ai"])
                    name = "The AI"
                else:
                    player = game.get_player_from_color(colorOrAI)
                    shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
                dice = shipModel.dice
                missiles = ""
                nonMissiles = " on initiative "+str(speed)
                if speed == 99:
                    dice = shipModel.missile
                    missiles = "missiles "
                    nonMissiles =""
                
                msg = name + " rolled the following "+missiles+"with their "+str(ship[2])+" "+Combat.translateShipAbrToName(ship[1])+"(s)"+nonMissiles+":\n"
                dieFiles = []
                dieNums = []
                for x in range(ship[2]):
                    for die in dice:
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1","Miss").replace("6",":boom:")
                        msg +=num+" "
                        dieFiles.append(drawing.use_image("images/resources/components/dice_faces/dice_"+Combat.translateColorToName(die)+"_"+str(random_number)+".png"))
                        dieNums.append([random_number,Combat.translateColorToDamage(die)])
                if shipModel.computer > 0:
                    msg = msg + "\nThis ship type has a +"+str(shipModel.computer)+" computer"
                if(len(dice) > 0):
                    await interaction.channel.send(msg,file=drawing.append_images(dieFiles))
                    oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                    for die in dieNums:
                        dieNum = die[0]
                        dieDam = die[1]
                        if dieNum == 1 or dieNum + shipModel.computer < 6 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                            continue
                        hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships, dieNum, shipModel.computer, pos)
                        if len(hittableShips) > 0:
                            if len(hittableShips) > 1:
                                if colorOrAI != "ai":
                                    msg = interaction.user.mention + " choose what ship to hit with the die that rolled a "+str(dieNum)+". The bot has calculated that you can hit these ships"
                                    view = View()
                                    for ship in hittableShips:
                                        shipType = ship.split("-")[1]
                                        shipOwner = ship.split("-")[0]
                                        label = "Hit "+Combat.translateShipAbrToName(shipType)
                                        buttonID = "FCID"+colorOrAI+"_assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                                        view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
                                    await interaction.channel.send(msg,view=view)
                                else:
                                    ship = hittableShips[0]
                                    oldShipVal = 0
                                    ableToKillSomething = False
                                    for option in hittableShips:
                                        damageOnShip = game.add_damage(option, pos, 0)
                                        shipType = option.split("-")[1]
                                        shipOwner = option.split("-")[0]
                                        player = game.get_player_from_color(shipOwner)
                                        shipModel = PlayerShip(game.gamestate["players"][player], shipType)
                                        if ableToKillSomething:
                                            if dieDam +damageOnShip> shipModel.hull and shipModel.cost > oldShipVal:
                                                oldShipVal = shipModel.cost
                                                ship = option
                                        else:
                                            if dieDam +damageOnShip> shipModel.hull:
                                                oldShipVal = shipModel.cost
                                                ship = option
                                                ableToKillSomething = True
                                            else:
                                                if shipModel.cost > oldShipVal:
                                                    oldShipVal = shipModel.cost
                                                    ship = option

                                    buttonID = "assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                                    await Combat.assignHitTo(game, buttonID, interaction, False)
                            else:
                                ship = hittableShips[0]
                                buttonID = "assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                                await Combat.assignHitTo(game, buttonID, interaction, False)

    @staticmethod
    async def assignHitTo(game:GamestateHelper, buttonID:str, interaction:discord.Interaction, button:bool):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        ship = buttonID.split("_")[3]
        dieNum = buttonID.split("_")[4]
        dieDam = buttonID.split("_")[5]
        shipType = ship.split("-")[1]
        shipOwner = ship.split("-")[0]
        if shipOwner == "ai":
            shipModel = AI_Ship(shipType, game.gamestate["advanced_ai"])
        else:
            player = game.get_player_from_color(shipOwner)
            shipModel = PlayerShip(game.gamestate["players"][player], shipType)
        damage = game.add_damage(ship, pos, int(dieDam))
        if colorOrAI != "ai":
            msg = interaction.user.mention + " dealt "+dieDam+" damage to a "+Combat.translateShipAbrToName(shipType)+" with a die that rolled a "+str(dieNum)
        else:
            msg = "The AI dealt "+dieDam+" damage to a "+Combat.translateShipAbrToName(shipType)+" with a die that rolled a "+str(dieNum)
        msg = msg + ". The damaged ship has "+str(shipModel.hull)+" hull, and so has "+str((shipModel.hull-damage+1))+" hp left."
        await interaction.channel.send(msg)
        if shipModel.hull < damage:
            oldLength = len(Combat.findPlayersInTile(game, pos))
            player1 = ""
            player2 = ""
            if oldLength > 1:
                player1 = Combat.findPlayersInTile(game, pos)[oldLength-2]
                player2 = Combat.findPlayersInTile(game, pos)[oldLength-1]
            game.destroy_ship(ship, pos, colorOrAI)
            if colorOrAI != "ai":
                msg = interaction.user.mention + " destroyed the "+Combat.translateShipAbrToName(shipType)+" due to the damage exceeding the ships hull"
            else:
                msg = "The AI destroyed the "+Combat.translateShipAbrToName(shipType)+" due to the damage exceeding the ships hull"
            await interaction.channel.send(msg)
            if len(Combat.findPlayersInTile(game, pos)) < 2 and len(Combat.findPlayersInTile(game, pos)) != oldLength:
                actions_channel = discord.utils.get(interaction.guild.channels, name=game.game_id+"-actions") 
                if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
                    await actions_channel.send("Combat in tile "+pos+" has concluded. There are "+str(len(Combat.findTilesInConflict(game)))+" tiles left in conflict")
            if len(Combat.findPlayersInTile(game, pos)) != oldLength:
                players = [player1, player2]
                for playerColor in players:
                    if playerColor == "ai":
                        continue
                    player = game.getPlayerObjectFromColor(playerColor)
                    count = str(game.getReputationTilesToDraw(pos, playerColor))
                    view = View()
                    label = "Draw "+count+" Reputation"
                    buttonID = "FCID"+playerColor+"_drawReputation_"+count
                    view.add_item(Button(label=label, style=discord.ButtonStyle.green, custom_id=buttonID))
                    label = "Decline"
                    buttonID = "FCID"+playerColor+"_deleteMsg"
                    view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
                    msg = player["player_name"] + " the bot believes you should draw "+count+" reputation tiles here. Click to do so or press decline if the bot messed up."
                    await interaction.channel.send(msg, view=view)
                if len(Combat.findPlayersInTile(game, pos)) > 1:
                    drawing = DrawHelper(game.gamestate)
                    await interaction.channel.send("Updated view",view = Combat.getCombatButtons(game, pos),file=drawing.board_tile_image_file(pos))
                
        if button:
            await interaction.message.delete()


    @staticmethod
    async def drawReputation(game:GamestateHelper, buttonID:str, interaction:discord.Interaction, player_helper):
        num_options = int(buttonID.split("_")[1])
        await ReputationButtons.resolveGainingReputation(game, num_options,interaction, player_helper)
        await interaction.channel.send(interaction.user.name + " drew "+ str(num_options)+ " reputation tiles")
        await interaction.message.delete()

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
    def translateColorToDamage(dieColor:str):
        if dieColor == "red":
            return 4
        if dieColor == "orange":
            return 2
        if dieColor == "blue":
            return 3
        return 1
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