import asyncio
import json
import random
import time

import discord
from discord.ui import View, Button
from Buttons.Influence import InfluenceButtons
from Buttons.Population import PopulationButtons
from Buttons.Reputation import ReputationButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import AI_Ship, PlayerShip
from jproperties import Properties

class Combat:

    @staticmethod
    def exile_orbital_exists(game:GamestateHelper, pos, color):
        if (game.find_player_faction_name_from_color(color) == "The Exiles" and "orbital_pop" in
                game.gamestate["board"][pos] and (game.gamestate["board"][pos]["orbital_pop"][0] == 1)):
            return True
        else:
            return False

    @staticmethod
    def findPlayersInTile(game:GamestateHelper,pos:str):
        tile_map = game.get_gamestate()["board"]
        if "player_ships" not in tile_map[pos]:
            return []
        player_ships = tile_map[pos]["player_ships"][:]
        players = []
        for ship in player_ships:
            color = ship.split("-")[0]
            if ("orb" in ship and not Combat.exile_orbital_exists(game, pos, color)) or "mon" in ship:
                continue
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
            if (game.find_player_faction_name_from_color(tile_map[pos]["owner"]) == "The Exiles" and "orb" in ship and "orbital_pop" in
                    tile_map[pos] and (tile_map[pos]["orbital_pop"][0]==1)):
                pass
            elif "orb" in ship or "mon" in ship:
                continue

            shipType = ship.split("-")[1]
            if "anc" in ship:
                ship = "anc"
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
                if(len(Combat.findPlayersInTile(game,tile)) == 2 and "anc" in Combat.findShipTypesInTile(game,tile)):
                    if "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game,tile)[1]) or "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game,tile)[0]):
                        continue
                tiles.append((int(tile_map[tile]["sector"]),tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)  
        return sorted_tiles

    @staticmethod
    def findTilesInContention(game:GamestateHelper):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if len(Combat.findPlayersInTile(game,tile)) == 1 and tile_map[tile]["owner"] != 0 and tile_map[tile]["owner"] != Combat.findPlayersInTile(game,tile)[0] and Combat.findPlayersInTile(game,tile)[0] != "ai":
                tiles.append((int(tile_map[tile]["sector"]),tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)  
        return sorted_tiles
    
    @staticmethod
    def findUnownedTilesToTakeOver(game:GamestateHelper):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if len(Combat.findPlayersInTile(game,tile)) == 1 and tile_map[tile]["owner"] == 0 and Combat.findPlayersInTile(game,tile)[0] != "ai":
                tiles.append((int(tile_map[tile]["sector"]),tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)  
        return sorted_tiles
    
    @staticmethod
    async def startCombat(game:GamestateHelper, channel, pos):
        drawing = DrawHelper(game.gamestate)
        players = Combat.findPlayersInTile(game, pos)[-2:]  
        game.setAttackerAndDefender(players[1], players[0],pos)
        game.setCurrentRoller(None, pos)
        game.setCurrentRoller(None, pos)
        for player in players:
            if player != "ai":
                image = await asyncio.to_thread(drawing.player_area,game.getPlayerObjectFromColor(player))
                file=await asyncio.to_thread(drawing.show_player_ship_area, image)
                await channel.send(game.getPlayerObjectFromColor(player)["player_name"]+" ships look like this",file=file)
            else:
                file = await asyncio.to_thread(drawing.show_AI_stats)
                await channel.send("AI stats look like this",file=file)
        await Combat.promptNextSpeed(game, pos, channel, False)

    @staticmethod
    async def startCombatThreads(game:GamestateHelper, interaction:discord.Interaction):
        channel = interaction.channel
        role = discord.utils.get(interaction.guild.roles, name=game.get_gamestate()["game_id"])  
        tiles = Combat.findTilesInConflict(game)
        game.createRoundNum()
        game.initilizeKey("activePlayerColor")
        if "wa_ai" not in game.get_gamestate():
            game.initilizeKey("wa_ai")
        if "tilesToResolve" not in game.get_gamestate():
            game.initilizeKey("tilesToResolve")
            game.initilizeKey("queuedQuestions")
            game.initilizeKey("queuedDraws")
            
        for tile in tiles:
            game.setCombatants(Combat.findPlayersInTile(game, tile[1]), tile[1])
            message_to_send = "Combat will occur in system "+str(tile[0])+", position "+tile[1]  
            message = await channel.send(message_to_send) 
            threadName = game.get_gamestate()["game_id"]+"-Round "+str(game.get_gamestate()["roundNum"])+", Tile "+tile[1]+", Combat"
            thread = await message.create_thread(name=threadName)
            drawing = DrawHelper(game.gamestate)
            await thread.send(role.mention +"Combat will occur in this tile",view = Combat.getCombatButtons(game, tile[1]),file=await asyncio.to_thread(drawing.board_tile_image_file,tile[1]))
            await Combat.startCombat(game, thread, tile[1])
            game.addToKey("tilesToResolve",tile[0])
        for tile2 in Combat.findTilesInContention(game):
            message_to_send = "Bombing may occur in system "+str(tile2[0])+", position "+tile2[1]  
            message = await channel.send(message_to_send) 
            threadName = game.get_gamestate()["game_id"]+"-Round "+str(game.get_gamestate()["roundNum"])+", Tile "+tile2[1]+", Bombing"
            thread2 = await message.create_thread(name=threadName)
            drawing = DrawHelper(game.gamestate)
            await thread2.send(role.mention +" population bombing may occur in this tile",file=await asyncio.to_thread(drawing.board_tile_image_file,tile2[1]))
            owner = game.get_gamestate()["board"][tile2[1]]["owner"]
            playerColor = Combat.findPlayersInTile(game, tile2[1])[0]
            winner = playerColor
            pos = tile2[1]
            player = game.getPlayerObjectFromColor(playerColor)
            p2 = game.getPlayerObjectFromColor(owner)
            player_helper = PlayerHelper(game.get_player_from_color(playerColor),player)
            player_helper2 = PlayerHelper(game.get_player_from_color(p2["color"]),p2)
            if p2["name"]=="Planta" or ("neb" in player_helper.getTechs() and "nea" not in player_helper2.getTechs()):
                view = View()
                view.add_item(Button(label="Destroy All Population", style=discord.ButtonStyle.green, custom_id="FCID"+winner+"_removeInfluenceFinish_"+pos+"_graveYard"))
                asyncio.create_task(thread2.send(player["player_name"]+" you can destroy all enemy population automatically",view=view))
                view2 = View()
                view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{winner}_addInfluenceFinish_"+pos))
                asyncio.create_task(thread2.send(player["player_name"]+" you can place your influence on the tile after destroying the enemy population",view=view2))
                view3 = View()
                view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
                asyncio.create_task(thread2.send(player["player_name"]+" if you have enough colony ships, you can use this to drop population after taking control of the sector",view=view3))
            else:
                view = View()
                view.add_item(Button(label="Roll to Destroy Population", style=discord.ButtonStyle.green, custom_id=f"FCID{winner}_rollDice_{pos}_{winner}_1000"))
                await thread2.send(player["player_name"]+" you can roll to attempt to kill enemy population",view=view)
        for tile3 in Combat.findUnownedTilesToTakeOver(game):
            message_to_send = "An influence disc may be placed in system "+str(tile3[0])+", position "+tile3[1]  
            message = await channel.send(message_to_send) 
            threadName = game.get_gamestate()["game_id"]+"-Round "+str(game.get_gamestate()["roundNum"])+", Tile "+tile3[1]+", Influence"
            thread3 = await message.create_thread(name=threadName)
            playerColor = Combat.findPlayersInTile(game, tile3[1])[0]
            winner = playerColor
            pos = tile3[1]
            player = game.getPlayerObjectFromColor(playerColor)
            view2 = View()
            view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{winner}_addInfluenceFinish_"+pos))
            await thread3.send(player["player_name"]+" you can place your influence on the tile after destroying the enemy population",view=view2)
            view3 = View()
            view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
            await thread3.send(player["player_name"]+" if you have enough colony ships, you can use this to drop population after taking control of the sector",view=view3)
        asyncio.create_task(channel.send("Resolve the combats simultaneously if you wish -- any reputation draws will be queued to resolve correctly"))
    @staticmethod
    def getCombatantShipsBySpeed(game:GamestateHelper, colorOrAI:str, playerShipsList, pos):
        ships = []
        for unit in playerShipsList:
            type = unit.split("-")[1]
            owner = unit.split('-')[0]

            if (game.find_player_faction_name_from_color(owner) == "The Exiles" and "orb" in unit and "orbital_pop" in
                    game.gamestate["board"][pos] and (game.gamestate["board"][pos]["orbital_pop"][0] == 1)):
                pass
            elif "orb" in unit or "mon" in unit:
                continue
            if colorOrAI == owner:
                if colorOrAI == "ai":
                    ship = AI_Ship(unit, game.gamestate["advanced_ai"], game.gamestate["wa_ai"])
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
    def getBothCombatantShipsBySpeed(game:GamestateHelper, defender:str,attacker:str, playerShipsList, pos):
        ships = []
        if Combat.doesCombatantHaveMissiles(game, defender, playerShipsList):
            ships.append((99, defender))
        if Combat.doesCombatantHaveMissiles(game, attacker, playerShipsList):
            ships.append((99, attacker))
        for unit in playerShipsList:
            type = unit.split("-")[1]
            owner = unit.split('-')[0]
            if (game.find_player_faction_name_from_color(owner) == "The Exiles" and "orb" in unit and "orbital_pop" in
                    game.gamestate["board"][pos] and (game.gamestate["board"][pos]["orbital_pop"][0] == 1)):
                pass
            elif "orb" in unit or "mon" in unit:
                continue
            if defender == owner or attacker == owner:
                if owner == "ai":
                    ship = AI_Ship(unit, game.gamestate["advanced_ai"], game.gamestate["wa_ai"])
                    if (ship.speed,owner) not in ships:
                        ships.append((ship.speed, owner))
                else:
                    player = game.get_player_from_color(owner)
                    ship = PlayerShip(game.gamestate["players"][player], type)
                    if (ship.speed,owner) not in ships:
                        ships.append((ship.speed, owner))
        sorted_ships = sorted(ships, key=lambda x: (x[0], x[1] == defender), reverse=True)    
        return sorted_ships
    

    
    @staticmethod
    def getOpponentUnitsThatCanBeHit(game:GamestateHelper, colorOrAI:str,playerShipsList, dieVal:int, computerVal:int, pos:str, speed:int):
        players = Combat.findPlayersInTile(game, pos)
        opponent = ""
        hittableShips = []
        if dieVal == 1 or dieVal + computerVal < 6:
            return hittableShips
        if len(players) < 2:
            if speed == 1000:
                if dieVal == 6 or dieVal + computerVal > 5:
                    for pop in PopulationButtons.findFullPopulation(game, pos):
                        hittableShips.append(pop)
            return hittableShips
        if colorOrAI == players[len(players)-1]:
            opponent = players[len(players)-2]
        else:
            opponent = players[len(players)-1]
        
        opponentShips = Combat.getCombatantShipsBySpeed(game, opponent, playerShipsList, pos)
        for ship in opponentShips:
            if opponent == "ai":
                shipModel = AI_Ship(ship[1], game.gamestate["advanced_ai"], game.gamestate["wa_ai"])
            else:
                player = game.get_player_from_color(opponent)
                shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
            shieldVal = shipModel.shield
            if dieVal == 6 or dieVal + computerVal - shieldVal > 5:
                ship_type = ship[1]
                if "-" in ship_type:
                    temp = ship_type.split("-")
                    ship_type = temp[1]
                hittableShips.append(opponent+"-"+ship_type.replace("adv",""))
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
                    ship = AI_Ship(unit, game.gamestate["advanced_ai"], game.gamestate["wa_ai"])
                    if len(ship.missile) > 0:
                        return True
                else:
                    player = game.get_player_from_color(colorOrAI)
                    ship = PlayerShip(game.gamestate["players"][player], type)
                    if len(ship.missile) > 0:
                        return True
        return False

    @staticmethod
    def getCombatantSpeeds(game:GamestateHelper, colorOrAI:str, playerShipsList, pos):
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, playerShipsList, pos)
        speeds =[]
        for ship in ships:
            if ship[0] not in speeds:
                speeds.append(ship[0])
        return speeds
    
    @staticmethod
    def getCombatButtons(game:GamestateHelper, pos:str):
        view = View()
        players = Combat.findPlayersInTile(game, pos)[-2:]  
        game.setAttackerAndDefender(players[1], players[0],pos)
        if len(players) > 1:
            attacker = game.get_gamestate()["board"][pos]["attacker"]
            defender = game.get_gamestate()["board"][pos]["defender"]
            tile_map = game.get_gamestate()["board"]
            player_ships = tile_map[pos]["player_ships"][:]
            defenderSpeeds = Combat.getCombatantSpeeds(game, defender, player_ships, pos)
            attackerSpeeds = Combat.getCombatantSpeeds(game, attacker, player_ships, pos)
            if Combat.doesCombatantHaveMissiles(game, defender, player_ships):
                view.add_item(Button(label="(Defender) Roll Missiles", style=discord.ButtonStyle.green, custom_id=f"rollDice_{pos}_{defender}_99_defender"))
            if Combat.doesCombatantHaveMissiles(game, attacker, player_ships):
                view.add_item(Button(label="(Attacker) Roll Missiles", style=discord.ButtonStyle.red, custom_id=f"rollDice_{pos}_{attacker}_99_attacker"))
            for i in range(20,-1,-1):
                if i in defenderSpeeds:
                    checker = ""
                    if defender != "ai":
                        checker="FCID"+defender+"_"
                    view.add_item(Button(label="(Defender) Roll Initative "+str(i)+" Ships", style=discord.ButtonStyle.green, custom_id=f"{checker}rollDice_{pos}_{defender}_{str(i)}_defender"))
                if i in attackerSpeeds:
                    checker = ""
                    if attacker != "ai":
                        checker="FCID"+attacker+"_"
                    view.add_item(Button(label="(Attacker) Roll Initative "+str(i)+" Ships", style=discord.ButtonStyle.red, custom_id=f"{checker}rollDice_{pos}_{attacker}_{str(i)}_attacker"))
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
        await interaction.channel.send(player['player_name']+" use buttons to remove units",view=view)
    
    @staticmethod
    async def removeThisUnit(game:GamestateHelper, customID:str, player, interaction:discord.Interaction):
        pos = customID.split("_")[1]
        unit =  customID.split("_")[2]
        oldLength = len(Combat.findPlayersInTile(game, pos))
        owner = unit.split("-")[0]
        game.remove_units([unit],pos)
        if owner == "ai":
            owner = "AI"
        await interaction.channel.send(player['player_name']+" removed 1 "+owner+" "+Combat.translateShipAbrToName(unit))
        view = Combat.getRemovalButtons(game, pos, player)
        await interaction.message.edit(view=view)
        if len(Combat.findPlayersInTile(game, pos)) < 2 and len(Combat.findPlayersInTile(game, pos)) != oldLength:
            actions_channel = discord.utils.get(interaction.guild.channels, name=game.game_id+"-actions") 
            if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
                await actions_channel.send("Combat in tile "+pos+" has concluded. There are "+str(len(Combat.findTilesInConflict(game)))+" tiles left in conflict")


    @staticmethod
    def getShipToSelfHitWithRiftCannon(game:GamestateHelper, colorOrAI, player_ships, pos):
        hittableShips = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        ship = hittableShips[0]
        oldShipVal = 0
        dieDam = 1
        ableToKillSomething = False
        for optionStuff in hittableShips:
            optionType = optionStuff[1]
            option = colorOrAI + "-"+optionType
            damageOnShip = game.add_damage(option, pos, 0)
            shipType = option.split("-")[1]
            shipOwner = option.split("-")[0]
            player = game.get_player_from_color(shipOwner)
            shipModel = PlayerShip(game.gamestate["players"][player], shipType)
            if "pink" not in shipModel.dice:
                continue
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
        return ship
    
    #Not currently in use, will be built to improve AI targetting in future
    @staticmethod
    async def rollDiceAI(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = int(buttonID.split("_")[3])
        oldLength = len(Combat.findPlayersInTile(game, pos))
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        game.setCurrentRoller(colorOrAI,pos)
        game.setCurrentSpeed(speed,pos)
        player = None
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        update = False
        for ship in ships:
            if ship[0] == speed or speed == 99:
                shipModel = AI_Ship(ship[1], game.gamestate["advanced_ai"], game.gamestate["wa_ai"])
                name = "The AI"
                dice = shipModel.dice
                missiles = ""
                nonMissiles = " on initiative "+str(speed)
                if speed == 99:
                    dice = shipModel.missile
                    missiles = "missiles "
                    nonMissiles =""
                msg = name + " rolled the following "+missiles+"with their "+str(ship[2])+" "+Combat.translateShipAbrToName(ship[1])+"(s)"+nonMissiles+":\n"
                dieNums = []
                msg2 = "\n"
                for x in range(ship[2]):
                    for die in dice:
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1","Miss").replace("6",":boom:")
                        emojiName = "dice_"+Combat.translateColorToName(die)+"_"+str(random_number)
                        guild_emojis = interaction.guild.emojis  
                        matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
                        msg +=str(num)+" "
                        if len(matching_emojis) > 0:
                            msg2 +=str(matching_emojis[0])+" "
                        dieNums.append([random_number,Combat.translateColorToDamage(die, random_number), die])
                if shipModel.computer > 0:
                    msg = msg + "\nThis ship type has a +"+str(shipModel.computer)+" computer"
                await interaction.channel.send(msg+msg2)
                oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                for die in dieNums:
                    tile_map = game.get_gamestate()["board"]
                    player_ships = tile_map[pos]["player_ships"][:]
                    dieNum = die[0]
                    dieDam = die[1]
                    dieColor = die[2]
                    hittableShips = []
                    hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships, dieNum, shipModel.computer, pos, speed)
                    if dieNum + shipModel.computer > 5 and len(hittableShips) == 0 and oldNumPeeps == len(Combat.findPlayersInTile(game, pos)):
                        await interaction.channel.send("The computer bonus for a die that rolled a "+str(dieNum)+" was cancelled by the shields on each of the opponents ships.")
                    if len(hittableShips) > 0:
                        update = True
                        if len(hittableShips) > 1:
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
        hitsToAssign = 0
        if "unresolvedHits" in game.get_gamestate()["board"][pos]:
            hitsToAssign = game.get_gamestate()["board"][pos]["unresolvedHits"]
        if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
            await Combat.promptNextSpeed(game, pos, interaction.channel, update)


    @staticmethod
    async def rollDice(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        if colorOrAI == "ai":
            await Combat.rollDiceAI(game, buttonID, interaction)
            return
        speed = int(buttonID.split("_")[3])
        oldLength = len(Combat.findPlayersInTile(game, pos))
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        game.setCurrentRoller(colorOrAI,pos)
        game.setCurrentSpeed(speed,pos)
        player = None
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        update = False
        for ship in ships:
            if ship[0] == speed or speed == 99 or speed == 1000:
                name = interaction.user.mention
                player = game.get_player_from_color(colorOrAI)
                shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
                dice = shipModel.dice
                missiles = ""
                nonMissiles = " on initiative "+str(speed)
                if speed == 99:
                    dice = shipModel.missile
                    missiles = "missiles "
                    nonMissiles =""
                if speed == 1000:
                    nonMissiles = " against the population"
                msg = name + " rolled the following "+missiles+"with their "+str(ship[2])+" "+Combat.translateShipAbrToName(ship[1])+"(s)"+nonMissiles+":\n"
                dieFiles = []
                dieNums = []
                msg2 = "\n"
                for x in range(ship[2]):
                    for die in dice:
                        split = False
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1","Miss").replace("6",":boom:")
                        emojiName = "dice_"+Combat.translateColorToName(die)+"_"+str(random_number)
                        guild_emojis = interaction.guild.emojis  
                        matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
                        msg +=str(num)+" "
                        if len(matching_emojis) > 0:
                            msg2 +=str(matching_emojis[0])+" "
                        #dieFiles.append(drawing.use_image("images/resources/components/dice_faces/dice_"+Combat.translateColorToName(die)+"_"+str(random_number)+".png"))
                        if missiles == "" and Combat.translateColorToDamage(die, random_number) == 4 and colorOrAI != "ai":
                            player = game.get_player_from_color(colorOrAI)
                            playerObj = game.getPlayerObjectFromColor(colorOrAI)
                            player_helper = PlayerHelper(player, playerObj)
                            researchedTechs = player_helper.getTechs()
                            if "ans" in researchedTechs:
                                split = True
                        if speed == 1000:
                            split = True
                        if not split:
                            dieNums.append([random_number,Combat.translateColorToDamage(die, random_number), die])
                        else:
                            for i in range(Combat.translateColorToDamage(die, random_number)):
                                dieNums.append([random_number,1,die])
                if shipModel.computer > 0:
                    msg = msg + "\nThis ship type has a +"+str(shipModel.computer)+" computer"
                
                if(len(dice) > 0):
                    #await interaction.channel.send(msg,file=drawing.append_images(dieFiles))
                    await interaction.channel.send(msg+msg2)
                    oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                    for die in dieNums:
                        tile_map = game.get_gamestate()["board"]
                        player_ships = tile_map[pos]["player_ships"][:]
                        dieNum = die[0]
                        dieDam = die[1]
                        dieColor = die[2]
                        hittableShips = []
                        if dieColor != "pink":
                            hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships, dieNum, shipModel.computer, pos, speed)
                            if dieNum + shipModel.computer > 5 and len(hittableShips) == 0 and oldNumPeeps == len(Combat.findPlayersInTile(game, pos)):
                                await interaction.channel.send("The computer bonus for a die that rolled a "+str(dieNum)+" was cancelled by the shields on each of the opponents ships.")
                            if len(hittableShips) == 0 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                                if player != None and "Lyra" in game.gamestate["players"][player]["name"] and game.gamestate["players"][player]["colony_ships"] > 0 and oldNumPeeps == len(Combat.findPlayersInTile(game, pos)):
                                    viewLyr = View()
                                    label = "Reroll Die"
                                    buttonID = "FCID"+colorOrAI+"_rerollDie_"+pos+"_"+colorOrAI+"_"+str(shipModel.computer)+"_"+dieColor
                                    viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green, custom_id=buttonID))
                                    viewLyr.add_item(Button(label="Decline", style=discord.ButtonStyle.red, custom_id="FCID"+colorOrAI+"_deleteMsg"))
                                    asyncio.create_task(interaction.channel.send(game.gamestate["players"][player]["player_name"]+" You can reroll a "+dieColor+" die that missed using one of your colony ships.", view=viewLyr))
                                continue
                        else:
                            if dieNum == 2 or dieNum == 3:
                                continue
                            if dieNum == 1 or dieNum == 6:
                                ship = Combat.getShipToSelfHitWithRiftCannon(game, colorOrAI,player_ships, pos)
                                buttonID = "assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(1)
                                await Combat.assignHitTo(game, buttonID, interaction, False)
                            if dieNum > 3:
                                hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships, 6, shipModel.computer, pos, speed)
                        if len(hittableShips) > 0:
                            if speed == 1000:
                                msg = interaction.user.name + " choose what pop to hit with the die that rolled a "+str(dieNum)+"."

                                view = View()
                                for count,cube in enumerate(hittableShips):
                                    advanced = ""
                                    if "adv" in cube:
                                        advanced = "advanced "
                                    label = "Hit "+advanced+cube.replace("adv","") + " population"
                                    buttonID = "FCID"+colorOrAI+"_killPop_"+pos+"_"+cube+"_"+str(count)
                                    view.add_item(Button(label=label, style=discord.ButtonStyle.gray, custom_id=buttonID))
                                await interaction.channel.send(msg,view=view)
                            else:
                                update = True
                                if len(hittableShips) > 1:
                                    msg = interaction.user.mention + " choose what ship to hit with the die that rolled a "+str(dieNum)+". You will deal "+str(dieDam)+" damage. The bot has calculated that you can hit these ships"
                                    view = View()
                                    for ship in hittableShips:
                                        shipType = ship.split("-")[1]
                                        shipOwner = ship.split("-")[0]
                                        label = "Hit "+Combat.translateShipAbrToName(shipType)
                                        buttonID = "FCID"+colorOrAI+"_assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                                        view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
                                    await interaction.channel.send(msg,view=view)
                                    hitsToAssign = 1
                                    if "unresolvedHits" in game.get_gamestate()["board"][pos]:
                                        hitsToAssign = game.get_gamestate()["board"][pos]["unresolvedHits"]+1
                                    game.setUnresolvedHits(hitsToAssign,pos)
                                else:
                                    ship = hittableShips[0]
                                    buttonID = "assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                                    await Combat.assignHitTo(game, buttonID, interaction, False)

        hitsToAssign = 0
        if speed != 1000:
            if "unresolvedHits" in game.get_gamestate()["board"][pos]:
                hitsToAssign = game.get_gamestate()["board"][pos]["unresolvedHits"]
            if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
                await Combat.promptNextSpeed(game, pos, interaction.channel, update)
    
    @staticmethod
    async def rerollDie(game:GamestateHelper, buttonID:str, interaction:discord.Interaction, player, player_helper:PlayerHelper):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        colorDie = buttonID.split("_")[4]
        computerVal = int(buttonID.split("_")[3])
        tile_map = game.get_gamestate()["board"]
        player_helper.adjust_colony_ships(1)
        player_ships = tile_map[pos]["player_ships"][:]
        name = interaction.user.mention  
        game.update_player(player_helper)
        msg = name + " rerolled a "+colorDie+" die with their ability. They have "+str(player_helper.stats["colony_ships"])+" colony ships left\n"
        dice = [colorDie]
        dieNums = []
        msg2 = "\n"
                
        for die in dice:
            random_number = random.randint(1, 6)
            num = str(random_number).replace("1","Miss").replace("6",":boom:")
            emojiName = "dice_"+Combat.translateColorToName(die)+"_"+str(random_number)
            guild_emojis = interaction.guild.emojis  
            matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
            msg +=str(num)+" "
            if len(matching_emojis) > 0:
                msg2 +=str(matching_emojis[0])+" "
            dieNums.append([random_number,Combat.translateColorToDamage(die, random_number), die])

        if computerVal > 0:
            msg = msg + "\nThis ship type has a +"+str(computerVal)+" computer"
                
        await interaction.channel.send(msg+msg2)
        oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
        for die in dieNums:
            tile_map = game.get_gamestate()["board"]
            player_ships = tile_map[pos]["player_ships"][:]
            dieNum = die[0]
            dieDam = die[1]
            dieColor = die[2]
            hittableShips = []
            if dieColor != "pink":
                hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships, dieNum, computerVal, pos, 3)
                if dieNum + computerVal > 5 and len(hittableShips) == 0:
                    await interaction.channel.send("The computer bonus for a die that rolled a "+str(dieNum)+" was cancelled by the shields on each of the opponents ships.")
                if len(hittableShips) == 0 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                    if "Lyra" in player["name"] and player["colony_ships"] > 0 and oldNumPeeps == len(Combat.findPlayersInTile(game, pos)):
                        viewLyr = View()
                        label = "Reroll Die"
                        buttonID = "FCID"+colorOrAI+"_rerollDie_"+pos+"_"+colorOrAI+"_"+str(computerVal)+"_"+dieColor
                        viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green, custom_id=buttonID))
                        viewLyr.add_item(Button(label="Decline", style=discord.ButtonStyle.red, custom_id="FCID"+colorOrAI+"_deleteMsg"))
                        await interaction.channel.send(player["player_name"]+" You can reroll a "+dieColor+" die that missed using one of your colony ships.", view=viewLyr)
                    continue
            else:
                if dieNum == 2 or dieNum == 3:
                    continue
                if dieNum == 1 or dieNum == 6:
                    ship = Combat.getShipToSelfHitWithRiftCannon(game, colorOrAI,player_ships, pos)
                    buttonID = "assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(1)
                    await Combat.assignHitTo(game, buttonID, interaction, False)
                if dieNum > 3:
                    hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships, 6, computerVal, pos, 3)
            if len(hittableShips) > 0:
                if len(hittableShips) > 1:
                    if colorOrAI != "ai":
                        msg = interaction.user.mention + " choose what ship to hit with the die that rolled a "+str(dieNum)+". You will deal "+str(dieDam)+" damage. The bot has calculated that you can hit these ships"
                        view = View()
                        for ship in hittableShips:
                            shipType = ship.split("-")[1]
                            shipOwner = ship.split("-")[0]
                            label = "Hit "+Combat.translateShipAbrToName(shipType)
                            buttonID = "FCID"+colorOrAI+"_assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                            view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
                        asyncio.create_task(interaction.channel.send(msg,view=view))
                        hitsToAssign = 1
                        if "unresolvedHits" in game.get_gamestate()["board"][pos]:
                            hitsToAssign = game.get_gamestate()["board"][pos]["unresolvedHits"]+1
                        game.setUnresolvedHits(hitsToAssign,pos)
                else:
                    ship = hittableShips[0]
                    buttonID = "assignHitTo_"+pos+"_"+colorOrAI+"_"+ship+"_"+str(dieNum)+"_"+str(dieDam)
                    await Combat.assignHitTo(game, buttonID, interaction, False)
        await interaction.message.delete()


    @staticmethod
    async def killPop(game:GamestateHelper, buttonID:str, interaction:discord.Interaction, player):
        pos = buttonID.split("_")[1]
        cube = buttonID.split("_")[2]
        owner = game.get_gamestate()["board"][pos]["owner"]
        advanced = ""
        if "adv" in cube:
            advanced = "advanced "
        msg = player["username"]+" hit "+advanced+cube.replace("adv","") + " population"
        await interaction.channel.send(msg)
        game.remove_pop([cube+"_pop"],pos,game.get_player_from_color(owner), True)
        await interaction.message.delete()
        if len(PopulationButtons.findFullPopulation(game, pos))==0:
            game.remove_control(owner,pos)
            view2 = View()
            view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_addInfluenceFinish_"+pos))
            await interaction.channel.send(player["player_name"]+" you can place your influence on the tile now that you have destroyed all the enemy population",view=view2)
            view3 = View()
            view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
            await interaction.channel.send(player["player_name"]+" if you have enough colony ships, you can use this to drop population after taking control of the sector",view=view3)
            

    @staticmethod
    async def checkForMorphShield(game:GamestateHelper, pos:str, channel, ships, players):
        for playerColor in players:
            if playerColor != "ai":
                for ship in Combat.getCombatantShipsBySpeed(game, playerColor, ships, pos):
                    player = game.get_player_from_color(playerColor)
                    shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
                    shipName = playerColor+"-"+ship[1]
                    if shipModel.repair > 0 and "damage_tracker" in game.gamestate["board"][pos] and shipName in game.gamestate["board"][pos]["damage_tracker"]:
                        if game.gamestate["board"][pos]["damage_tracker"][shipName] > 0:
                            damage = game.repair_damage(shipName, pos)
                            await channel.send(game.gamestate["players"][player]["player_name"] + " repaired 1 damage on their "+Combat.translateShipAbrToName(ship[1]) + " using a morph shield")
                            break

    @staticmethod
    async def promptNextSpeed(game:GamestateHelper, pos:str, channel, update:bool):
        currentSpeed = None
        if "currentSpeed" in game.get_gamestate()["board"][pos]:
            currentSpeed = game.get_gamestate()["board"][pos]["currentSpeed"]
        currentRoller = None
        if "currentRoller" in game.get_gamestate()["board"][pos]:
            currentRoller = game.get_gamestate()["board"][pos]["currentRoller"]
        attacker = game.get_gamestate()["board"][pos]["attacker"]
        defender = game.get_gamestate()["board"][pos]["defender"]
        ships = game.get_gamestate()["board"][pos]["player_ships"]
        sortedSpeeds = Combat.getBothCombatantShipsBySpeed(game, defender, attacker, ships, pos)

        found = False
        nextSpeed = -1
        nextOwner = ""
        for speed,owner in sortedSpeeds:
            if found or currentSpeed == None or currentRoller == None or (currentSpeed != None and speed < currentSpeed):
                nextSpeed = speed
                nextOwner = owner
                break
            if speed == currentSpeed and currentRoller == owner:
                found = True
        if nextSpeed == -1:
            await Combat.checkForMorphShield(game, pos, channel, ships, [attacker, defender])
            for speed,owner in sortedSpeeds:
                if speed != 99:
                    nextSpeed = speed
                    nextOwner = owner
                    break
        view = View()
        checker = ""
        if update:
            drawing = DrawHelper(game.gamestate)
            asyncio.create_task(channel.send("Updated view",file=await asyncio.to_thread(drawing.board_tile_image_file,pos)))
        game.setCurrentRoller(nextOwner,pos)
        game.setCurrentSpeed(nextSpeed,pos)
        initiative = "Initiative "+str(nextSpeed)
        if nextSpeed == 99:
            initiative = "missiles"



        if [nextSpeed,nextOwner] in game.getRetreatingUnits(pos):
            checker="FCID"+nextOwner+"_"
            playerObj = game.getPlayerObjectFromColor(nextOwner)
            viewedTiles = []
            msg = playerObj["player_name"] + " announced a retreat for ships with "+initiative +" and should now choose a controlled sector adjacent that does not contain enemy ships"
            for tile in Combat.getRetreatTiles(game, pos, nextOwner):
                if tile not in viewedTiles:
                    viewedTiles.append(tile)
                    view.add_item(Button(label=tile, style=discord.ButtonStyle.red, custom_id=f"{checker}finishRetreatingUnits_{pos}_{nextOwner}_{str(nextSpeed)}_{tile}"))
        else:
            if nextOwner != "ai" and nextOwner != "":
                checker="FCID"+nextOwner+"_"
                playerObj = game.getPlayerObjectFromColor(nextOwner)
                msg = playerObj["player_name"] + " it is your turn to roll your ships with "+initiative
                
                view.add_item(Button(label="Roll "+initiative+" Ships", style=discord.ButtonStyle.green, custom_id=f"{checker}rollDice_{pos}_{nextOwner}_{str(nextSpeed)}_deleteMsg"))
                if nextSpeed != 99 and len(Combat.getRetreatTiles(game, pos, nextOwner)) > 0:
                    msg += ". You can also alternatively choose to start to retreat them."
                    shipsSpeeds = Combat.getCombatantShipsBySpeed(game, nextOwner, ships, pos)
                    newSpeeds = 0
                    for ship in shipsSpeeds:
                        speed2 = ship[0]
                        if speed2 != 99 and speed2 != int(speed):
                            newSpeeds += 1
                            break
                    if newSpeeds < 1:
                        msg +=" You would lose out on the default 1 reputation for battling if you choose to retreat here."
                    view.add_item(Button(label="Retreat "+initiative+" Ships", style=discord.ButtonStyle.red, custom_id=f"{checker}startToRetreatUnits_{pos}_{nextOwner}_{str(nextSpeed)}"))
            else:
                view.add_item(Button(label="Roll "+initiative+" Ships For AI", style=discord.ButtonStyle.green, custom_id=f"{checker}rollDice_{pos}_{nextOwner}_{str(nextSpeed)}_deleteMsg"))
                if attacker != "ai":
                    playerObj = game.getPlayerObjectFromColor(attacker)
                else:
                    playerObj = game.getPlayerObjectFromColor(defender)
                msg = playerObj["player_name"] + " please roll the dice for the AI ships with "+initiative
        await channel.send(msg, view = view)
        
    @staticmethod
    async def finishRetreatingUnits(game:GamestateHelper, buttonID:str, interaction:discord.Interaction, playerObj):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = buttonID.split("_")[3]
        destination = buttonID.split("_")[4]
        oldLength = len(Combat.findPlayersInTile(game, pos))
        game.removeCertainRetreatingUnits((int(speed),colorOrAI), pos)
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        for ship in player_ships:
            if colorOrAI in ship and "orb" not in ship and "mon" not in ship and "sb" not in ship:
                type = ship.split("-")[1]
                player = game.get_player_from_color(colorOrAI)
                shipM = PlayerShip(game.gamestate["players"][player], type)
                if shipM.speed == int(speed):
                    game.remove_units([ship],pos)
                    game.add_units([ship],destination)
        await interaction.message.delete()
        await interaction.channel.send(playerObj['player_name'] + " has retreated all ships with initiative "+speed+" to "+destination+".")
        dracoNAnc = len(Combat.findPlayersInTile(game,pos)) == 2 and "anc" in Combat.findShipTypesInTile(game,pos) and "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game,pos)[1])
        if len(Combat.findPlayersInTile(game, pos)) < 2 or dracoNAnc:
                await Combat.declareAWinner(game, interaction, pos)
        elif oldLength != len(Combat.findPlayersInTile(game, pos)):
            drawing = DrawHelper(game.gamestate)
            await interaction.channel.send("Updated view",view = Combat.getCombatButtons(game, pos),file=drawing.board_tile_image_file(pos))
            await Combat.startCombat(game, interaction.channel, pos)
        else:
            await Combat.promptNextSpeed(game, pos, interaction.channel, True)


    @staticmethod
    def getRetreatTiles(game:GamestateHelper, pos:str, color:str):
        from Buttons.Influence import InfluenceButtons
        playerObj = game.getPlayerObjectFromColor(color)
        player_helper = PlayerHelper(game.get_player_from_color(color),playerObj)
        techsResearched = player_helper.getTechs()
        configs = Properties()
        if "5playerhyperlane" in game.gamestate and game.gamestate["5playerhyperlane"]:
            with open("data/tileAdjacencies_5p.properties", "rb") as f:
                configs.load(f)
        else:
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
        wormHoleGen = "wog" in techsResearched
        validTiles = []
        for tile in playerObj["owned_tiles"]:
            players = Combat.findPlayersInTile(game, tile)
            if InfluenceButtons.areTwoTilesAdjacent(game, pos, tile, configs, wormHoleGen) and len(players) < 2:
                if len(players) == 1 and players[0] != color:
                    continue
                validTiles.append(tile)
        return validTiles

    @staticmethod
    async def startToRetreatUnits(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = buttonID.split("_")[3]
        game.setRetreatingUnits((int(speed),colorOrAI), pos)
        tile_map = game.get_gamestate()["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        player = game.getPlayerObjectFromColor(colorOrAI)
        await interaction.message.delete()
        await interaction.channel.send(player['player_name'] + " has chosen to start to retreat the ships with initiative "+speed+". They will be prompted to retreat when their turn comes around again")
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        newSpeeds = 0
        for ship in ships:
            speed2 = ship[0]
            if speed2 != 99 and speed2 != int(speed):
                newSpeeds += 1
                break
        if newSpeeds < 1:
            game.setRetreatingPenalty(colorOrAI,pos)
            await interaction.channel.send(interaction.user.mention + " is attempting to retreat all their remaining ships and will thus not receive the default 1 reputation tile draw at the end of combat")
        
        

        await Combat.promptNextSpeed(game, pos, interaction.channel, False)


    @staticmethod
    async def declareAWinner(game:GamestateHelper, interaction:discord.Interaction, pos:str):
        game.updateSaveFile()
        
        actions_channel = discord.utils.get(interaction.guild.channels, name=game.game_id+"-actions") 
        if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
            await actions_channel.send("Combat in tile "+pos+" has concluded. There are "+str(len(Combat.findTilesInConflict(game)))+" tiles left in conflict")
            if len(Combat.findTilesInConflict(game)) == 0:
                role = discord.utils.get(interaction.guild.roles, name=game.game_id)
                view = View()
                view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"startPopDrop"))
                await actions_channel.send(role.mention+" Please run upkeep after all post combat events are resolved. You can use this button to drop pop after taking control of a tile", view = view)
        if "combatants" in game.gamestate["board"][pos]:
            players = game.gamestate["board"][pos]["combatants"]
        else:
            players = Combat.findPlayersInTile(game,pos)
        countDraw = 1
        game.removeFromKey("tilesToResolve",int(game.gamestate["board"][pos]["sector"]))
        for playerColor in players:
            if playerColor == "ai":
                continue
            player = game.getPlayerObjectFromColor(playerColor)
            count = str(game.getReputationTilesToDraw(pos, playerColor))
            view = View()
            label = "Draw "+count+" Reputation"
            buttonID = "FCID"+playerColor+"_drawReputation_"+count + "_"+game.gamestate["board"][pos]["sector"]+ "_"+str(countDraw)+"_" +playerColor
            view.add_item(Button(label=label, style=discord.ButtonStyle.green, custom_id=buttonID))
            label = "Decline"
            buttonID = "FCID"+playerColor+"_deleteMsg"
            view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
            msg = player["player_name"] + " the bot believes you should draw "+count+" reputation tiles here. Click to do so or press decline if the bot messed up. If other battles/players need to resolve first, your draw will be queued after you click this button"
            if int(count) > 0:
                if "tilesToResolve" in game.get_gamestate():
                    game.addToKey("queuedQuestions", [int(game.gamestate["board"][pos]["sector"]), countDraw, playerColor])
                    countDraw +=1
                asyncio.create_task(interaction.channel.send(msg, view=view))
        winner = Combat.findPlayersInTile(game, pos)[0]
        owner = game.gamestate["board"][pos]["owner"]
        
        if winner != "ai" and owner != winner:
            player = game.getPlayerObjectFromColor(winner)
            if game.gamestate["board"][pos]["disctile"]!=0:
                view = View()
                view.add_item(Button(label="Explore Discovery Tile", style=discord.ButtonStyle.green, custom_id="FCID"+winner+"_exploreDiscoveryTile_"+pos+"_deleteMsg"))
                asyncio.create_task(interaction.channel.send(player["player_name"]+" you can explore the discovery tile",view=view))
            if owner==0:
                view2 = View()
                view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{winner}_addInfluenceFinish_"+pos))
                asyncio.create_task(interaction.channel.send(player["player_name"]+" you can place your influence on the tile",view=view2))
                view3 = View()
                view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
                asyncio.create_task(interaction.channel.send(player["player_name"]+" if you have enough colony ships, you can use this to drop population after taking control of the sector",view=view3))
            else:
                p2 = game.getPlayerObjectFromColor(owner)
                player_helper = PlayerHelper(game.get_player_from_color(player["color"]),player)
                player_helper2 = PlayerHelper(game.get_player_from_color(p2["color"]),p2)
                if p2["name"]=="Planta" or ("neb" in player_helper.getTechs() and "nea" not in player_helper2.getTechs()):
                    view = View()
                    view.add_item(Button(label="Destroy All Population", style=discord.ButtonStyle.green, custom_id="FCID"+winner+"_removeInfluenceFinish_"+pos+"_graveYard"))
                    asyncio.create_task(interaction.channel.send(player["player_name"]+" you can destroy all enemy population automatically",view=view))
                    view2 = View()
                    view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{winner}_addInfluenceFinish_"+pos))
                    asyncio.create_task(interaction.channel.send(player["player_name"]+" you can place your influence on the tile after destroying the enemy population",view=view2))
                    view3 = View()
                    view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
                    asyncio.create_task(interaction.channel.send(player["player_name"]+" if you have enough colony ships, you can use this to drop population after taking control of the sector",view=view3))
                else:
                    view = View()
                    view.add_item(Button(label="Roll to Destroy Population", style=discord.ButtonStyle.green, custom_id=f"FCID{winner}_rollDice_{pos}_{winner}_1000"))
                    asyncio.create_task(interaction.channel.send(player["player_name"]+" you can roll to attempt to kill enemy population",view=view)) 
        
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
            shipModel = AI_Ship(shipType, game.gamestate["advanced_ai"], game.gamestate["wa_ai"])
            if "ai-" in ship and "adv" not in "ship" and game.gamestate["advanced_ai"]:
                ship = ship +"adv"
        else:
            player = game.get_player_from_color(shipOwner)
            shipModel = PlayerShip(game.gamestate["players"][player], shipType)
        damage = game.add_damage(ship, pos, int(dieDam))
        if colorOrAI != "ai":
            msg = interaction.user.mention + " dealt "+dieDam+" damage to a "+Combat.translateShipAbrToName(shipType)+" with a die that rolled a "+str(dieNum)
        else:
            msg = "The AI dealt "+dieDam+" damage to a "+Combat.translateShipAbrToName(shipType)+" with a die that rolled a "+str(dieNum)
        msg = msg + ". The damaged ship has "+str((shipModel.hull-damage+1))+"/"+str(shipModel.hull+1)+" hp left. "
        oldLength = len(Combat.findPlayersInTile(game, pos))
        if shipModel.hull < damage:
            game.destroy_ship(ship, pos, colorOrAI)
            if colorOrAI != "ai":
                msg += interaction.user.name + " destroyed the "+Combat.translateShipAbrToName(shipType)+" due to the damage exceeding the ships hull"
            else:
                msg += "The AI destroyed the "+Combat.translateShipAbrToName(shipType)+" due to the damage exceeding the ships hull"
            await interaction.channel.send(msg)
            dracoNAnc = len(Combat.findPlayersInTile(game,pos)) == 2 and "anc" in Combat.findShipTypesInTile(game,pos) and "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game,pos)[1])
            if len(Combat.findPlayersInTile(game, pos)) < 2 or dracoNAnc:
                await Combat.declareAWinner(game, interaction, pos)
            elif oldLength != len(Combat.findPlayersInTile(game, pos)):
                drawing = DrawHelper(game.gamestate)
                await interaction.channel.send("Updated view",view = Combat.getCombatButtons(game, pos),file=await asyncio.to_thread(drawing.board_tile_image_file,pos))
                await Combat.startCombat(game, interaction.channel, pos)
        else:
            await interaction.channel.send(msg)
        if button:
            await interaction.message.delete()
            hitsToAssign = 0
            if "unresolvedHits" in game.get_gamestate()["board"][pos]:
                hitsToAssign = max(game.get_gamestate()["board"][pos]["unresolvedHits"]-1,0)
            game.setUnresolvedHits(hitsToAssign, pos)
            if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
                await Combat.promptNextSpeed(game, pos, interaction.channel, True)


    @staticmethod
    async def resolveQueue(game:GamestateHelper, interaction:discord.Interaction):
        foundNoSuccess = False
        success = 1
        while not foundNoSuccess and success < 20:
            foundNoSuccess = True
            queuedDraws = game.get_gamestate()["queuedDraws"][:]
            for system, drawOrder, color, num_options in queuedDraws:
                systemAheadNeedsToResolve = False
                for system2 in game.get_gamestate()["tilesToResolve"]:
                    if system2 > system:
                        systemAheadNeedsToResolve = True
                if not systemAheadNeedsToResolve:
                    goodToResolve = True
                    for system2, drawOrder2, color2, num_options2 in game.get_gamestate()["queuedDraws"]:
                        if int(system2) > int(system) or (int(system2) == int(system) and drawOrder > drawOrder2):
                            goodToResolve = False
                    for system2, drawOrder2, color2 in game.get_gamestate()["queuedQuestions"]:
                        if int(system2) > int(system) or (int(system2) == int(system) and drawOrder > drawOrder2):
                            goodToResolve = False
                    if goodToResolve:
                        foundNoSuccess = False
                        player_helper = PlayerHelper(game.get_player_from_color(color),game.getPlayerObjectFromColor(color))
                        await ReputationButtons.resolveGainingReputation(game, num_options,interaction, player_helper, True)
                        game.removeFromKey("queuedDraws", [system, drawOrder, color, num_options])
                        success += 1
    


    @staticmethod
    async def drawReputation(game:GamestateHelper, buttonID:str, interaction:discord.Interaction, player_helper):
        num_options = int(buttonID.split("_")[1])
        system = int(buttonID.split("_")[2])
        drawOrder = int(buttonID.split("_")[3])
        color = buttonID.split("_")[4]
        if "tilesToResolve" in game.gamestate:
            game.removeFromKey("queuedQuestions",[system, drawOrder, color])
            game.addToKey("queuedDraws", [system, drawOrder, color, num_options])
            await Combat.resolveQueue(game, interaction)
            if [system, drawOrder, color, num_options] in game.gamestate["queuedDraws"]:
                await interaction.channel.send(interaction.user.name + " your reputation draw has been queued")
            else:
                await interaction.channel.send(interaction.user.name + " drew "+ str(num_options)+ " reputation tiles")
        else:
            await ReputationButtons.resolveGainingReputation(game, num_options,interaction, player_helper, False)
            await interaction.channel.send(interaction.user.name + " drew "+ str(num_options)+ " reputation tiles")
        await interaction.message.delete()

    @staticmethod
    async def refreshImage(game:GamestateHelper, buttonID:str, interaction:discord.Interaction):
        pos = buttonID.split("_")[1]
        drawing = DrawHelper(game.gamestate)
        view = View()
        if len(Combat.findPlayersInTile(game, pos)) > 1:
            view = Combat.getCombatButtons(game, pos)
        await interaction.channel.send("Updated view",view = view,file=await asyncio.to_thread(drawing.board_tile_image_file,pos))

    @staticmethod
    def translateColorToName(dieColor:str):
        if dieColor == "red":
            return "antimatter"
        if dieColor == "pink":
            return "rift"
        if dieColor == "orange":
            return "plasma"
        if dieColor == "blue":
            return "soliton"
        return "ion"
    @staticmethod
    def translateColorToDamage(dieColor:str, dieValue:int):
        if dieColor == "red":
            return 4
        if dieColor == "orange":
            return 2
        if dieColor == "blue":
            return 3
        if dieColor == "pink":
            if dieValue == 6:
                return 3
            if dieValue == 5:
                return 2
            if dieValue == 4:
                return 1
            return 0
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