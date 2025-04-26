import asyncio
import random

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
    def exile_orbital_exists(game: GamestateHelper, pos):
        return all([game.find_player_faction_name_from_color(game.gamestate["board"][pos]["owner"]) == "The Exiles",
                    game.gamestate["board"][pos].get("orbital_pop", [0])[0] == 1])

    @staticmethod
    def findPlayersInTile(game: GamestateHelper, pos: str):
        tile_map = game.gamestate["board"]
        if "player_ships" not in tile_map[pos]:
            return []
        player_ships = tile_map[pos]["player_ships"][:]
        players = []
        for ship in player_ships:
            color = ship.split("-")[0]
            if ("orb" in ship and not Combat.exile_orbital_exists(game, pos)) or "mon" in ship:
                continue
            else:
                if "orb" in ship:
                    color = game.gamestate["board"][pos]["owner"]
            if color not in players:
                players.append(color)
        return players

    @staticmethod
    def findShipTypesInTile(game: GamestateHelper, pos: str):
        tile_map = game.gamestate["board"]
        if "player_ships" not in tile_map[pos]:
            return []
        player_ships = tile_map[pos]["player_ships"][:]
        ships = []
        for ship in player_ships:
            if all([game.find_player_faction_name_from_color(tile_map[pos]["owner"]) == "The Exiles",
                    tile_map[pos].get("orbital_pop", [0])[0] == 1]):
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
    def findTilesInConflict(game: GamestateHelper):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            if len(Combat.findPlayersInTile(game, tile)) > 1:
                game.fixshipsOrder(tile)
                # Don't start combat between draco and ancients
                if len(Combat.findPlayersInTile(game, tile)) == 2 and "anc" in Combat.findShipTypesInTile(game, tile):
                    playerInTile = Combat.findPlayersInTile(game, tile)
                    if any(["Draco" in game.find_player_faction_name_from_color(playerInTile[1]),
                            "Draco" in game.find_player_faction_name_from_color(playerInTile[0])]):
                        continue
                tiles.append((int(tile_map[tile]["sector"]), tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)
        return sorted_tiles

    @staticmethod
    def findTilesInContention(game: GamestateHelper):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            playersInTile = Combat.findPlayersInTile(game, tile)
            if len(playersInTile) != 1:
                continue
            if all([tile_map[tile]["owner"] != 0,
                    tile_map[tile]["owner"] != playersInTile[0],
                    playersInTile[0] != "ai"]):
                tiles.append((int(tile_map[tile]["sector"]), tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)
        return sorted_tiles

    @staticmethod
    def findUnownedTilesToTakeOver(game: GamestateHelper):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            playersInTile = Combat.findPlayersInTile(game, tile)
            if len(playersInTile) == 2:
                if "anc" in Combat.findShipTypesInTile(game, tile):
                    if any(["Draco" in game.find_player_faction_name_from_color(playersInTile[1]),
                            "Draco" in game.find_player_faction_name_from_color(playersInTile[0])]):
                        if "owner" in tile_map[tile]:
                            if tile_map[tile]["owner"] == 0:
                                tiles.append((int(tile_map[tile]["sector"]), tile))
            else:
                if len(playersInTile) != 1:
                    continue
                if "owner" in tile_map[tile]:
                    if tile_map[tile]["owner"] == 0 and playersInTile[0] != "ai":
                        tiles.append((int(tile_map[tile]["sector"]), tile))
        return sorted(tiles, key=lambda x: x[0], reverse=True)

    @staticmethod
    async def startCombat(game: GamestateHelper, channel, pos):
        drawing = DrawHelper(game.gamestate)
        players = Combat.findPlayersInTile(game, pos)[-2:]
        game.setAttackerAndDefender(players[1], players[0], pos)
        game.setCurrentRoller(None, pos)
        game.setCurrentRoller(None, pos)
        for player in players:
            if player != "ai":
                image = await asyncio.to_thread(drawing.player_area, game.getPlayerObjectFromColor(player))
                file = await asyncio.to_thread(drawing.show_player_ship_area, image)
                await channel.send(game.getPlayerObjectFromColor(player)["player_name"] + " ships look like this",
                                   file=file)
            else:
                file = await asyncio.to_thread(drawing.show_AI_stats)
                await channel.send("AI stats look like this", file=file)
        await Combat.promptNextSpeed(game, pos, channel, False)

    @staticmethod
    async def startCombatThreads(game: GamestateHelper, interaction: discord.Interaction):
        channel = interaction.channel
        role = discord.utils.get(interaction.guild.roles, name=game.gamestate["game_id"])
        tiles = Combat.findTilesInConflict(game)
        game.createRoundNum()
        game.initilizeKey("activePlayerColor")
        if "wa_ai" not in game.gamestate:
            game.initilizeKey("wa_ai")
        game.initilizeKey("tilesToResolve")
        game.initilizeKey("queuedQuestions")
        game.initilizeKey("queuedDraws")
        game.initilizeKey("peopleToCheckWith")

        for tile in tiles:

            game.setCombatants(Combat.findPlayersInTile(game, tile[1]), tile[1])
            message_to_send = f"Combat will occur in system {tile[0]}, position {tile[1]}."
            message = await channel.send(message_to_send)
            threadName = (f"{game.gamestate['game_id']}-Round {game.gamestate['roundNum']}, "
                          f"Tile {tile[1]}, Combat")
            thread = await message.create_thread(name=threadName)
            drawing = DrawHelper(game.gamestate)
            asyncio.create_task(thread.send(role.mention + "Combat will occur in this tile",
                              view=Combat.getCombatButtons(game, tile[1]),
                              file=await asyncio.to_thread(drawing.board_tile_image_file, tile[1])))
            await Combat.startCombat(game, thread, tile[1])
            game.addToKey("tilesToResolve", tile[0])
            for combatatant in Combat.findPlayersInTile(game, tile[1]):
                if combatatant not in game.gamestate["peopleToCheckWith"] and combatatant != "ai":
                    game.addToKey("peopleToCheckWith", combatatant)
        for tile2 in Combat.findTilesInContention(game):
            message_to_send = f"Bombing may occur in system {tile2[0]}, position {tile2[1]}."
            message = await channel.send(message_to_send)
            threadName = (f"{game.gamestate['game_id']}-Round {game.gamestate['roundNum']}, "
                          f"Tile {tile2[1]}, Bombing")
            thread2 = await message.create_thread(name=threadName)
            drawing = DrawHelper(game.gamestate)
            asyncio.create_task(thread2.send(role.mention + " population bombing may occur in this tile",
                               file=await asyncio.to_thread(drawing.board_tile_image_file, tile2[1])))
            owner = game.gamestate["board"][tile2[1]]["owner"]
            playerColor = Combat.findPlayersInTile(game, tile2[1])[0]
            winner = playerColor
            pos = tile2[1]
            player = game.getPlayerObjectFromColor(playerColor)
            playerName = player['player_name']
            p2 = game.getPlayerObjectFromColor(owner)
            player_helper = PlayerHelper(game.get_player_from_color(playerColor), player)
            player_helper2 = PlayerHelper(game.get_player_from_color(p2["color"]), p2)
            if any([p2["name"] == "Planta",
                    game.is_population_gone(pos),
                    "neb" in player_helper.getTechs() and "nea" not in player_helper2.getTechs()]):
                view = View()
                view.add_item(Button(label="Destroy All Population", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{winner}_removeInfluenceFinish_{pos}_graveYard"))
                message = f"{playerName}, you may destroy all enemy influence and population automatically."
                asyncio.create_task(thread2.send(message, view=view))
                view2 = View()
                view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple,
                                      custom_id=f"FCID{winner}_addInfluenceFinish_{pos}"))
                message = (f"{playerName}, you may place your influence on the tile"
                           " after destroying the enemy population.")
                asyncio.create_task(thread2.send(message, view=view2))
                view3 = View()
                view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                      custom_id=f"FCID{player['color']}_startPopDrop"))
                message = (f"{playerName}, if you have enough colony ships, "
                           "you may use this to drop population after taking control of the sector.")
                asyncio.create_task(thread2.send(message, view=view3))
            else:
                view = View()
                view.add_item(Button(label="Roll to Destroy Population", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{winner}_rollDice_{pos}_{winner}_1000_deleteMsg"))
                message = f"{playerName}, you may roll to attempt to kill enemy population."
                asyncio.create_task(thread2.send(message, view=view))
            for combatatant in Combat.findPlayersInTile(game, tile2[1]):
                if combatatant not in game.gamestate["peopleToCheckWith"] and combatatant != "ai":
                    game.addToKey("peopleToCheckWith", combatatant)
        for tile3 in Combat.findUnownedTilesToTakeOver(game):
            message_to_send = f"An influence disc may be placed in system {tile3[0]}, position {tile3[1]}."
            message = await channel.send(message_to_send)
            threadName = (f"{game.gamestate['game_id']}-Round {game.gamestate['roundNum']},"
                          f" Tile {tile3[1]} Influence")
            thread3 = await message.create_thread(name=threadName)
            playerColor = Combat.findPlayersInTile(game, tile3[1])[0]
            if playerColor == "ai":
                playerColor = Combat.findPlayersInTile(game, tile3[1])[1]
            winner = playerColor
            pos = tile3[1]
            player = game.getPlayerObjectFromColor(playerColor)
            playerName = player['player_name']
            view2 = View()
            view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple,
                                  custom_id=f"FCID{winner}_addInfluenceFinish_{pos}"))
            message = (f"{playerName}, you may place your influence on the tile after destroying the enemy population.")
            asyncio.create_task(thread3.send(message, view=view2))
            view3 = View()
            view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                  custom_id=f"FCID{player['color']}_startPopDrop"))
            message = (f"{playerName}, if you have enough colony ships, "
                       "you may use this to drop population after taking control of the sector.")
            asyncio.create_task(thread3.send(message, view=view3))
            for combatatant in Combat.findPlayersInTile(game, tile3[1]):
                if combatatant not in game.gamestate["peopleToCheckWith"] and combatatant != "ai":
                    game.addToKey("peopleToCheckWith", combatatant)
        message = ("Resolve the combats simultaneously if you wish"
                   " -- any reputation draws will be queued to resolve correctly.")
        asyncio.create_task(channel.send(message))
        if len(game.gamestate["peopleToCheckWith"]) > 0:
            view4 = View()
            view4.add_item(Button(label="Ready for Upkeep", style=discord.ButtonStyle.green,
                                  custom_id="readyForUpkeep"))
            message = (f"The game will require everyone"
                       f" ({str(len(game.gamestate['peopleToCheckWith']))} players)"
                       f" involved in an end of round thread to hit this button before upkeep can be run. "
                       f"The players who will need to press are: \n")
            for color2 in game.gamestate['peopleToCheckWith']:
                p2 = game.getPlayerObjectFromColor(color2)
                message += p2["player_name"] + "\n"
            asyncio.create_task(interaction.channel.send(message, view=view4))

    @staticmethod
    def getCombatantShipsBySpeed(game: GamestateHelper, colorOrAI: str, playerShipsList, pos):
        ships = []
        for unit in playerShipsList:
            unitType = unit.split("-")[1]
            owner = unit.split('-')[0]

            if all([game.find_player_faction_name_from_color(owner) == "The Exiles",
                    "orb" in unit,
                    game.gamestate["board"][pos].get("orbital_pop", [0])[0] == 1]):
                pass
            elif "orb" in unit or "mon" in unit:
                continue
            if colorOrAI == owner:
                if colorOrAI == "ai":
                    advanced = game.gamestate["advanced_ai"]
                    worldsafar = game.gamestate["wa_ai"]
                    if unitType+"_type" in game.gamestate:
                        advanced = "adv" in game.gamestate[unitType+"_type"]
                        worldsafar ="wa" in game.gamestate[unitType+"_type"]
                    ship = AI_Ship(unit, advanced, worldsafar)
                    ships.append((ship.speed, unit))
                else:
                    player = game.get_player_from_color(colorOrAI)
                    ship = PlayerShip(game.gamestate["players"][player], unitType)
                    ships.append((ship.speed, unitType))
        sorted_ships = sorted(ships, key=lambda x: x[0], reverse=True)
        sorted_ships_grouped = []
        seen_ships = []
        for ship in sorted_ships:
            if ship[1] not in seen_ships:
                seen_ships.append(ship[1])
                amount = 0
                for ship2 in sorted_ships:
                    if ship[1] == ship2[1]:
                        amount += 1
                sorted_ships_grouped.append((ship[0], ship[1], amount))

        return sorted_ships_grouped

    @staticmethod
    def getBothCombatantShipsBySpeed(game: GamestateHelper, defender: str, attacker: str, playerShipsList, pos):
        ships = []
        # if Combat.doesCombatantHaveMissiles(game, defender, playerShipsList):
        #     ships.append((99, defender))
        # if Combat.doesCombatantHaveMissiles(game, attacker, playerShipsList):
        #     ships.append((99, attacker))
        for unit in playerShipsList:
            unitType = unit.split("-")[1]
            owner = unit.split('-')[0]
            if all([game.find_player_faction_name_from_color(owner) == "The Exiles",
                    "orb" in unit,
                    game.gamestate["board"][pos].get("orbital_pop", [0])[0] == 1]):
                pass
            elif "orb" in unit or "mon" in unit:
                continue
            if defender == owner or attacker == owner:
                if owner == "ai":
                    advanced = game.gamestate["advanced_ai"]
                    worldsafar = game.gamestate["wa_ai"]
                    if unitType+"_type" in game.gamestate:
                        advanced = "adv" in game.gamestate[unitType+"_type"]
                        worldsafar ="wa" in game.gamestate[unitType+"_type"]
                    ship = AI_Ship(unit, advanced, worldsafar)
                    if (ship.speed, owner) not in ships:
                        ships.append((ship.speed, owner))
                    if len(ship.missile) > 0:
                        if (ship.speed+99, owner) not in ships:
                            ships.append((ship.speed+99, owner))
                else:
                    player = game.get_player_from_color(owner)
                    ship = PlayerShip(game.gamestate["players"][player], unitType)
                    if (ship.speed, owner) not in ships:
                        ships.append((ship.speed, owner))
                    if len(ship.missile) > 0:
                        if (ship.speed+99, owner) not in ships:
                            ships.append((ship.speed+99, owner))
        sorted_ships = sorted(ships, key=lambda x: (x[0], x[1] == defender), reverse=True)
        return sorted_ships

    @staticmethod
    def getOpponentUnitsThatCanBeHit(game: GamestateHelper, colorOrAI: str, playerShipsList,
                                     dieVal: int, computerVal: int, pos: str, speed: int):
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
        if colorOrAI == players[len(players) - 1]:
            opponent = players[len(players) - 2]
        else:
            opponent = players[len(players) - 1]

        opponentShips = Combat.getCombatantShipsBySpeed(game, opponent, playerShipsList, pos)
        for ship in opponentShips:
            if opponent == "ai":
                unitType = ship[1].split("-")[1]
                advanced = game.gamestate["advanced_ai"]
                worldsafar = game.gamestate["wa_ai"]
                if unitType+"_type" in game.gamestate:
                    advanced = "adv" in game.gamestate[unitType+"_type"]
                    worldsafar ="wa" in game.gamestate[unitType+"_type"]
                shipModel = AI_Ship(unitType, advanced, worldsafar)
            else:
                player = game.get_player_from_color(opponent)
                shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
            shieldVal = shipModel.shield
            if dieVal == 6 or dieVal + computerVal - shieldVal > 5:
                ship_type = ship[1]
                if "-" in ship_type:
                    temp = ship_type.split("-")
                    ship_type = temp[1]
                hittableShips.append(opponent + "-" + ship_type.replace("adv", ""))
        return hittableShips

    @staticmethod
    def doesCombatantHaveMissiles(game: GamestateHelper, colorOrAI: str, playerShipsList):
        for unit in playerShipsList:
            unitType = unit.split("-")[1]
            owner = unit.split('-')[0]
            if unitType == "orb" or unitType == "mon":
                continue
            if colorOrAI == owner:
                if colorOrAI == "ai":
                    advanced = game.gamestate["advanced_ai"]
                    worldsafar = game.gamestate["wa_ai"]
                    if unitType+"_type" in game.gamestate:
                        advanced = "adv" in game.gamestate[unitType+"_type"]
                        worldsafar ="wa" in game.gamestate[unitType+"_type"]
                    ship = AI_Ship(unit, advanced, worldsafar)
                    if len(ship.missile) > 0:
                        return True
                else:
                    player = game.get_player_from_color(colorOrAI)
                    ship = PlayerShip(game.gamestate["players"][player], unitType)
                    if len(ship.missile) > 0:
                        return True
        return False

    @staticmethod
    def getCombatantSpeeds(game: GamestateHelper, colorOrAI: str, playerShipsList, pos):
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, playerShipsList, pos)
        speeds = []
        for ship in ships:
            if ship[0] not in speeds:
                speeds.append(ship[0])
        return speeds

    @staticmethod
    def getCombatButtons(game: GamestateHelper, pos: str):
        view = View()
        players = Combat.findPlayersInTile(game, pos)[-2:]
        game.setAttackerAndDefender(players[1], players[0], pos)
        if len(players) > 1:
            attacker = game.gamestate["board"][pos]["attacker"]
            defender = game.gamestate["board"][pos]["defender"]
            tile_map = game.gamestate["board"]
            player_ships = tile_map[pos]["player_ships"][:]
            defenderSpeeds = Combat.getCombatantSpeeds(game, defender, player_ships, pos)
            attackerSpeeds = Combat.getCombatantSpeeds(game, attacker, player_ships, pos)
            # if Combat.doesCombatantHaveMissiles(game, defender, player_ships):
            #     view.add_item(Button(label="(Defender) Roll Missiles",
            #                          style=discord.ButtonStyle.green,
            #                          custom_id=f"rollDice_{pos}_{defender}_99_defender"))
            # if Combat.doesCombatantHaveMissiles(game, attacker, player_ships):
            #     view.add_item(Button(label="(Attacker) Roll Missiles",
            #                          style=discord.ButtonStyle.red,
            #                          custom_id=f"rollDice_{pos}_{attacker}_99_attacker"))

            ships = game.gamestate["board"][pos]["player_ships"][:]
            sortedSpeeds = Combat.getBothCombatantShipsBySpeed(game, defender, attacker, ships, pos)
            for speed, owner in sortedSpeeds:
                if owner == defender:
                    checker = ""
                    if defender != "ai":
                        checker = "FCID" + defender + "_"
                    if speed < 90:
                        view.add_item(Button(label="(Defender) Roll Initative " + str(speed) + " Ships",
                                            style=discord.ButtonStyle.green,
                                            custom_id=f"{checker}rollDice_{pos}_{defender}_{str(speed)}_defender"))
                    else:
                        view.add_item(Button(label="(Defender) Roll Initative " + str(speed-99) + " Missiles",
                                            style=discord.ButtonStyle.green,
                                            custom_id=f"{checker}rollDice_{pos}_{defender}_{str(speed)}_defender"))
                else:
                    checker = "" if attacker == "ai" else f"FCID{attacker}_"
                    if speed < 90:
                        view.add_item(Button(label="(Attacker) Roll Initative " + str(speed) + " Ships",
                                            style=discord.ButtonStyle.red,
                                            custom_id=f"{checker}rollDice_{pos}_{attacker}_{str(speed)}_attacker"))
                    else:
                        view.add_item(Button(label="Attacker) Roll Initative " + str(speed-99) + " Missiles",
                                            style=discord.ButtonStyle.red,
                                            custom_id=f"{checker}rollDice_{pos}_{attacker}_{str(speed)}_attacker"))
            # for i in range(20, -20, -1):
            #     if i in defenderSpeeds:
            #         checker = ""
            #         if defender != "ai":
            #             checker = "FCID" + defender + "_"
            #         view.add_item(Button(label="(Defender) Roll Initative " + str(i) + " Ships",
            #                              style=discord.ButtonStyle.green,
            #                              custom_id=f"{checker}rollDice_{pos}_{defender}_{str(i)}_defender"))
            #     if i in attackerSpeeds:
            #         checker = "" if attacker == "ai" else f"FCID{attacker}_"
            #         view.add_item(Button(label="(Attacker) Roll Initative " + str(i) + " Ships",
            #                              style=discord.ButtonStyle.red,
            #                              custom_id=f"{checker}rollDice_{pos}_{attacker}_{i}_attacker"))
        view.add_item(Button(label="Refresh Image", style=discord.ButtonStyle.blurple, custom_id=f"refreshImage_{pos}"))
        view.add_item(Button(label="Remove Units", style=discord.ButtonStyle.gray, custom_id=f"removeUnits_{pos}"))
        return view

    @staticmethod
    def getRemovalButtons(game: GamestateHelper, pos: str, player):
        view = View()
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        shownShips = []
        checker = "FCID" + player["color"] + "_"
        for ship in player_ships:
            if ship not in shownShips:
                shownShips.append(ship)
                owner = ship.split("-")[0]
                shipType = ship.split("-")[1]
                view.add_item(Button(label=f"Remove {owner} {Combat.translateShipAbrToName(shipType)}",
                                     style=discord.ButtonStyle.red, custom_id=f"{checker}removeThisUnit_{pos}_{ship}"))
        view.add_item(Button(label="Delete This", style=discord.ButtonStyle.red, custom_id="deleteMsg"))
        return view

    @staticmethod
    async def removeUnits(game: GamestateHelper, customID: str, player, interaction: discord.Interaction):
        pos = customID.split("_")[1]
        view = Combat.getRemovalButtons(game, pos, player)
        await interaction.channel.send(player['player_name'] + " use buttons to remove units", view=view)

    @staticmethod
    async def removeThisUnit(game: GamestateHelper, customID: str, player, interaction: discord.Interaction):
        pos = customID.split("_")[1]
        unit = customID.split("_")[2]
        oldLength = len(Combat.findPlayersInTile(game, pos))
        owner = unit.split("-")[0]
        game.remove_units([unit], pos)
        if owner == "ai":
            owner = "AI"
        message = f"{player['player_name']} removed 1 {owner} {Combat.translateShipAbrToName(unit)}."
        await interaction.channel.send(message)
        view = Combat.getRemovalButtons(game, pos, player)
        await interaction.message.edit(view=view)
        if len(Combat.findPlayersInTile(game, pos)) < 2 and len(Combat.findPlayersInTile(game, pos)) != oldLength:
            actions_channel = discord.utils.get(interaction.guild.channels, name=game.game_id + "-actions")
            if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
                message = (f"Combat in tile {pos} has concluded. "
                           f"There are {len(Combat.findTilesInConflict(game))} tiles left in conflict.")
                await actions_channel.send(message)

    @staticmethod
    def getShipToSelfHitWithRiftCannon(game: GamestateHelper, colorOrAI, player_ships, pos):
        hittableShips = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        ship = hittableShips[0]
        oldShipVal = 0
        dieDam = 1
        ableToKillSomething = False
        for optionStuff in hittableShips:
            optionType = optionStuff[1]
            option = colorOrAI + "-" + optionType
            damageOnShip = game.add_damage(option, pos, 0)
            shipType = option.split("-")[1]
            shipOwner = option.split("-")[0]
            player = game.get_player_from_color(shipOwner)
            shipModel = PlayerShip(game.gamestate["players"][player], shipType)
            if "pink" not in shipModel.dice:
                continue
            if ableToKillSomething:
                if dieDam + damageOnShip > shipModel.hull and shipModel.cost > oldShipVal:
                    oldShipVal = shipModel.cost
                    ship = option
            else:
                if dieDam + damageOnShip > shipModel.hull:
                    oldShipVal = shipModel.cost
                    ship = option
                    ableToKillSomething = True
                else:
                    if shipModel.cost > oldShipVal:
                        oldShipVal = shipModel.cost
                        ship = option
        return ship

    @staticmethod
    async def rollDiceAI(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = int(buttonID.split("_")[3])
        oldLength = len(Combat.findPlayersInTile(game, pos))
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        game.setCurrentRoller(colorOrAI, pos)
        game.setCurrentSpeed(speed, pos)
        player = None
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        update = False
        for ship in ships:
            if ship[0] == speed or int(ship[0]+99) == speed:
                unitType = ship[1].split("-")[1]
                advanced = game.gamestate["advanced_ai"]
                worldsafar = game.gamestate["wa_ai"]
                if unitType+"_type" in game.gamestate:
                    advanced = "adv" in game.gamestate[unitType+"_type"]
                    worldsafar ="wa" in game.gamestate[unitType+"_type"]
                shipModel = AI_Ship(unitType, advanced, worldsafar)
                name = "The AI"
                dice = shipModel.dice
                missiles = ""
                nonMissiles = " on initiative " + str(speed)
                if speed > 98 and speed < 1000:
                    dice = shipModel.missile
                    if len(shipModel.missile) < 1 and speed > 98 and speed < 1000:
                        await interaction.channel.send("Something went wrong and no missiles were found for this AI")
                        continue
                    missiles = "missiles on initiative " + str(speed-99)+" "
                    nonMissiles = ""
                msg = (f"{name} rolled the following {missiles}with their {ship[2]}"
                       f" {Combat.translateShipAbrToName(ship[1])}{'' if ship[2] == 1 else 's'}{nonMissiles}:\n")
                dieNums = []
                msg2 = "\n"
                for x in range(ship[2]):
                    for die in dice:
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1", "Miss").replace("6", ":boom:")
                        emojiName = f"dice_{Combat.translateColorToName(die)}_{random_number}"
                        guild_emojis = interaction.guild.emojis
                        matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
                        msg += str(num) + " "
                        if len(matching_emojis) > 0:
                            msg2 += str(matching_emojis[0]) + " "
                        dieNums.append([random_number, Combat.translateColorToDamage(die, random_number), die])
                if shipModel.computer > 0:
                    msg += f"\nThis ship type has a +{shipModel.computer} computer."
                await interaction.channel.send(msg + msg2)
                oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                for die in dieNums:
                    tile_map = game.gamestate["board"]
                    player_ships = tile_map[pos]["player_ships"][:]
                    dieNum = die[0]
                    dieDam = die[1]
                    hittableShips = []
                    hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                        dieNum, shipModel.computer, pos, speed)
                    if all([dieNum + shipModel.computer > 5, len(hittableShips) == 0, oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                        message = (f"The computer bonus for a die that rolled a {dieNum}"
                                   " was cancelled by the shields on each of the opponents ships.")
                        await interaction.channel.send(message)
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
                                shipModel2 = PlayerShip(game.gamestate["players"][player], shipType)
                                if ableToKillSomething:
                                    if dieDam + damageOnShip > shipModel2.hull and shipModel2.cost > oldShipVal:
                                        oldShipVal = shipModel2.cost
                                        ship = option
                                else:
                                    if dieDam + damageOnShip > shipModel2.hull:
                                        oldShipVal = shipModel2.cost
                                        ship = option
                                        ableToKillSomething = True
                                    else:
                                        if shipModel2.cost > oldShipVal:
                                            oldShipVal = shipModel2.cost
                                            ship = option
                            buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                            await Combat.assignHitTo(game, buttonID, interaction, False)
                        else:
                            ship = hittableShips[0]
                            buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                            await Combat.assignHitTo(game, buttonID, interaction, False)
        hitsToAssign = 0
        if "unresolvedHits" in game.gamestate["board"][pos]:
            hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"]
        if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
            await Combat.promptNextSpeed(game, pos, interaction.channel, update)


    @staticmethod
    async def resolveLyraRiftRoll(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        dieNum = int(buttonID.split("_")[3])
        speed = int(buttonID.split("_")[4])
        dieDam = int(buttonID.split("_")[5])
        counter = int(buttonID.split("_")[6])
        oldLength = len(Combat.findPlayersInTile(game, pos))
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        hittableShips = []
        hitsToAssign = 0
        if "unresolvedHits" in game.gamestate["board"][pos]:
            hitsToAssign = max(game.gamestate["board"][pos]["unresolvedHits"] - 1, 0)
        game.setUnresolvedHits(hitsToAssign, pos)
        if dieNum == 1 or dieNum == 6:
            ship = Combat.getShipToSelfHitWithRiftCannon(game, colorOrAI, player_ships, pos)
            buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_1"
            await Combat.assignHitTo(game, buttonID, interaction, False)
        update = False
        if dieNum > 3:
            hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                6, 0, pos, speed)
        if len(hittableShips) > 0:
            if speed == 1000:
                msg = (f"{interaction.user.name}, choose what population to hit"
                        f" with the die that rolled a {dieNum}.")

                view = View()
                for count, cube in enumerate(hittableShips):
                    advanced = "advanced " if "adv" in cube else ""
                    label = f"Hit {advanced}{cube.replace('adv', '')} population"
                    buttonID = f"FCID{colorOrAI}_killPop_{pos}_{cube}_{count}"
                    view.add_item(Button(label=label, style=discord.ButtonStyle.gray,
                                            custom_id=buttonID))
                asyncio.create_task(interaction.channel.send(msg, view=view))
            else:
                update = True
                if len(hittableShips) > 1:
                    msg = (f"{interaction.user.mention}, choose what ship to hit"
                            f" with the die that rolled a {dieNum}. You will deal {dieDam} damage. "
                            "The bot has calculated that you can hit these ships.")
                    view = View()
                    for ship in hittableShips:
                        shipType = ship.split("-")[1]
                        # shipOwner = ship.split("-")[0]
                        label = "Hit " + Combat.translateShipAbrToName(shipType)
                        buttonID = (f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}"
                                    f"_{ship}_{dieNum}_{dieDam}_{counter}")
                        view.add_item(Button(label=label, style=discord.ButtonStyle.red,
                                                custom_id=buttonID))
                    await interaction.channel.send(msg, view=view)
                    hitsToAssign = 1
                    if "unresolvedHits" in game.gamestate["board"][pos]:
                        hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                    game.setUnresolvedHits(hitsToAssign, pos)
                else:
                    ship = hittableShips[0]
                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                    await Combat.assignHitTo(game, buttonID, interaction, False)

            hitsToAssign = 0
        if speed != 1000:
            if "unresolvedHits" in game.gamestate["board"][pos]:
                hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"]
            if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
                await Combat.promptNextSpeed(game, pos, interaction.channel, update)
        await interaction.message.delete()
    @staticmethod
    async def rollDice(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        if colorOrAI == "ai":
            await Combat.rollDiceAI(game, buttonID, interaction)
            return
        speed = int(buttonID.split("_")[3])
        oldLength = len(Combat.findPlayersInTile(game, pos))
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        game.setCurrentRoller(colorOrAI, pos)
        game.setCurrentSpeed(speed, pos)
        player = None
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        update = False
        popRiftProtector = True
        for ship in ships:
            if ship[0] == speed or speed == (ship[0]+99) or speed == 1000:
                name = interaction.user.mention
                player = game.get_player_from_color(colorOrAI)
                shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
                dice = shipModel.dice
                missiles = ""
                nonMissiles = " on initiative " + str(speed)
                if speed > 90 and speed < 1000:
                    dice = shipModel.missile
                    if len(shipModel.missile) <1 and speed > 90 and speed < 1000:
                        continue
                    missiles = "missiles on initiative " + str(speed-99)+" "
                    nonMissiles = ""
                if speed == 1000:
                    nonMissiles = " against the population"
                shipCount = ship[2]
                msg = (f"{name} rolled the following {missiles}with their {shipCount}"
                       f" {Combat.translateShipAbrToName(ship[1])}{'' if shipCount == 1 else 's'}{nonMissiles}:\n")
                dieNums = []
                msg2 = "\n"
                for x in range(ship[2]):
                    for die in dice:
                        split = False
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1", "Miss").replace("6", ":boom:")
                        emojiName = f"dice_{Combat.translateColorToName(die)}_{random_number}"
                        guild_emojis = interaction.guild.emojis
                        matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
                        msg += str(num) + " "
                        if len(matching_emojis) > 0:
                            msg2 += str(matching_emojis[0]) + " "
                        # dieFiles.append(drawing.use_image("images/resources/components/dice_faces/dice_" +
                        #                                   Combat.translateColorToName(die) +
                        #                                   "_" + str(random_number) + ".png"))
                        if all([missiles == "",
                                Combat.translateColorToDamage(die, random_number) == 4]):
                            player = game.get_player_from_color(colorOrAI)
                            playerObj = game.getPlayerObjectFromColor(colorOrAI)
                            player_helper = PlayerHelper(player, playerObj)
                            researchedTechs = player_helper.getTechs()
                            if "ans" in researchedTechs:
                                split = True
                        if speed == 1000:
                            split = True
                        if not split:
                            dieNums.append([random_number, Combat.translateColorToDamage(die, random_number), die])
                        else:
                            for i in range(Combat.translateColorToDamage(die, random_number)):
                                dieNums.append([random_number, 1, die])
                if shipModel.computer > 0:
                    msg += f"\nThis ship type has a +{shipModel.computer} computer."

                if len(dice) > 0:
                    # await interaction.channel.send(msg,file=drawing.append_images(dieFiles))
                    await interaction.channel.send(msg + msg2)
                    oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                    counter = 0
                    for die in dieNums:
                        counter = counter + 1
                        tile_map = game.gamestate["board"]
                        player_ships = tile_map[pos]["player_ships"][:]
                        dieNum = die[0]
                        dieDam = die[1]
                        dieColor = die[2]
                        hittableShips = []
                        if dieColor != "pink":
                            hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                                dieNum, shipModel.computer, pos, speed)
                            if all([dieNum + shipModel.computer > 5,
                                    len(hittableShips) == 0,
                                    oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                                message = (f"The computer bonus for a die that rolled a {dieNum} was"
                                           " cancelled by the shields on each of the opponents ships.")
                                asyncio.create_task( interaction.channel.send(message))
                            if len(hittableShips) == 0 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                                if all([player is not None,
                                        "Lyra" in game.gamestate["players"][player]["name"],
                                        game.gamestate["players"][player]["colony_ships"] > 0,
                                        oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                                    viewLyr = View()
                                    label = "Reroll Die"
                                    buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                                f"_{shipModel.computer}_{dieColor}_{counter}")
                                    viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green,
                                                            custom_id=buttonID))
                                    viewLyr.add_item(Button(label="Decline", style=discord.ButtonStyle.red,
                                                            custom_id="FCID"+colorOrAI+"_deleteMsg"+"_"+str(counter)))
                                    message = (game.gamestate["players"][player]["player_name"] + ", you can reroll a"
                                               f" {dieColor} die that missed using one of your colony ships.")
                                    asyncio.create_task(interaction.channel.send(message, view=viewLyr))
                                continue
                        else:
                            if all([player is not None,
                                        "Lyra" in game.gamestate["players"][player]["name"],
                                        game.gamestate["players"][player]["colony_ships"] > 0,
                                        oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                                    viewLyr = View()
                                    label = "Reroll Die"
                                    buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                                f"_{shipModel.computer}_{dieColor}_{counter}")
                                    riftButtonID = (f"FCID{colorOrAI}_resolveLyraRiftRoll_{pos}_{colorOrAI}"
                                                f"_{str(dieNum)}_{str(speed)}_{str(dieDam)}_{counter}")
                                    viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green,
                                                            custom_id=buttonID))
                                    viewLyr.add_item(Button(label="Decline Reroll", style=discord.ButtonStyle.red,
                                                            custom_id=riftButtonID))
                                    emojiStr = str(dieNum)
                                    emojiName = f"dice_{Combat.translateColorToName('pink')}_{dieNum}"
                                    guild_emojis = interaction.guild.emojis
                                    matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
                                    msg += str(num) + " "
                                    if len(matching_emojis) > 0:
                                        emojiStr = str(matching_emojis[0]) 
                                    message = (game.gamestate["players"][player]["player_name"] + ", you can reroll a"
                                               f" rift die that rolled a {emojiStr} using one of your colony ships.")
                                    asyncio.create_task(interaction.channel.send(message, view=viewLyr))
                                    hitsToAssign = 1
                                    if "unresolvedHits" in game.gamestate["board"][pos]:
                                        hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                                    game.setUnresolvedHits(hitsToAssign, pos)
                                    continue
                            if dieNum == 2 or dieNum == 3:
                                continue
                            if dieNum == 1 or dieNum == 6:
                                ship = Combat.getShipToSelfHitWithRiftCannon(game, colorOrAI, player_ships, pos)
                                buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_1"
                                if dieNum != 6 or popRiftProtector:
                                    await Combat.assignHitTo(game, buttonID, interaction, False)
                                if dieNum == 6 and speed == 1000:
                                    popRiftProtector = False
                                
                            if dieNum > 3:
                                hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                                    6, shipModel.computer, pos, speed)
                        if len(hittableShips) > 0:
                            if speed == 1000:
                                msg = (f"{interaction.user.name}, choose what population to hit"
                                       f" with the die that rolled a {dieNum}.")

                                view = View()
                                for count, cube in enumerate(hittableShips):
                                    advanced = "advanced " if "adv" in cube else ""
                                    label = f"Hit {advanced}{cube.replace('adv', '')} population"
                                    buttonID = f"FCID{colorOrAI}_killPop_{pos}_{cube}_{count}"
                                    view.add_item(Button(label=label, style=discord.ButtonStyle.gray,
                                                         custom_id=buttonID))
                                asyncio.create_task(interaction.channel.send(msg, view=view))
                            else:
                                update = True
                                if len(hittableShips) > 1:
                                    msg = (f"{interaction.user.mention}, choose what ship to hit"
                                           f" with the die that rolled a {dieNum}. You will deal {dieDam} damage. "
                                           "The bot has calculated that you can hit these ships.")
                                    view = View()
                                    for ship in hittableShips:
                                        shipType = ship.split("-")[1]
                                        # shipOwner = ship.split("-")[0]
                                        label = "Hit " + Combat.translateShipAbrToName(shipType)
                                        buttonID = (f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}"
                                                    f"_{ship}_{dieNum}_{dieDam}_{counter}")
                                        view.add_item(Button(label=label, style=discord.ButtonStyle.red,
                                                             custom_id=buttonID))
                                    await interaction.channel.send(msg, view=view)
                                    hitsToAssign = 1
                                    if "unresolvedHits" in game.gamestate["board"][pos]:
                                        hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                                    game.setUnresolvedHits(hitsToAssign, pos)
                                else:
                                    ship = hittableShips[0]
                                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                                    await Combat.assignHitTo(game, buttonID, interaction, False)

        hitsToAssign = 0
        if speed != 1000:
            if "unresolvedHits" in game.gamestate["board"][pos]:
                hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"]
            if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
                await Combat.promptNextSpeed(game, pos, interaction.channel, update)

    @staticmethod
    async def rerollDie(game: GamestateHelper, buttonID: str, interaction: discord.Interaction,
                        player, player_helper: PlayerHelper):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        colorDie = buttonID.split("_")[4]
        computerVal = int(buttonID.split("_")[3])
        speed = game.gamestate["board"][pos]["currentSpeed"]
        tile_map = game.gamestate["board"]
        ships = player_helper.adjust_colony_ships(1)
        player_ships = tile_map[pos]["player_ships"][:]
        name = interaction.user.mention
        game.update_player(player_helper)
        msg = (f"{name} rerolled a {colorDie} die with their ability. "
               f"They have {ships} colony ship{'s' if ships == 1 else ''} left.\n")
        dice = [colorDie]
        dieNums = []
        msg2 = "\n"

        for die in dice:
            random_number = random.randint(1, 6)
            num = str(random_number).replace("1", "Miss").replace("6", ":boom:")
            emojiName = f"dice_{Combat.translateColorToName(die)}_{random_number}"
            guild_emojis = interaction.guild.emojis
            matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
            msg += str(num) + " "
            if len(matching_emojis) > 0:
                msg2 += str(matching_emojis[0]) + " "
            dieNums.append([random_number, Combat.translateColorToDamage(die, random_number), die])

        if computerVal > 0:
            msg += f"\nThis ship type has a +{str(computerVal)} computer."
        await interaction.channel.send(msg + msg2)

        oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
        for die in dieNums:
            tile_map = game.gamestate["board"]
            player_ships = tile_map[pos]["player_ships"][:]
            dieNum, dieDam, dieColor = die
            hittableShips = []
            if dieColor != "pink":
                hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                    dieNum, computerVal, pos, 3)
                if dieNum + computerVal > 5 and len(hittableShips) == 0:
                    message = (f"The computer bonus for a die that rolled a {dieNum}"
                               " was cancelled by the shields on each of the opponents ships.")
                    await interaction.channel.send(message)
                if len(hittableShips) == 0 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                    if all(["Lyra" in player["name"],
                            player["colony_ships"] > 0,
                            oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                        viewLyr = View()
                        label = "Reroll Die"
                        buttonID = f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}_{computerVal}_{dieColor}"
                        viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green, custom_id=buttonID))
                        viewLyr.add_item(Button(label="Decline", style=discord.ButtonStyle.red,
                                                custom_id="FCID" + colorOrAI + "_deleteMsg"))
                        message = (f"{player['player_name']}, you may reroll a {dieColor} die"
                                   " that missed using one of your colony ships.")
                        await interaction.channel.send(message, view=viewLyr)
                    continue
            else:
                if "unresolvedHits" in game.gamestate["board"][pos]:
                    hitsToAssign = max(game.gamestate["board"][pos]["unresolvedHits"] - 1, 0)
                game.setUnresolvedHits(hitsToAssign, pos)
                if all([player is not None,
                                        "Lyra" in player["name"],
                                        player["colony_ships"] > 0,
                                    oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                        viewLyr = View()
                        label = "Reroll Die"
                        buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                    f"_{0}_{dieColor}_{5}")
                        riftButtonID = (f"FCID{colorOrAI}_resolveLyraRiftRoll_{pos}_{colorOrAI}"
                                    f"_{str(dieNum)}_{str(speed)}_{str(dieDam)}_{5}")
                        viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green,
                                                custom_id=buttonID))
                        viewLyr.add_item(Button(label="Decline Reroll", style=discord.ButtonStyle.red,
                                                custom_id=riftButtonID))
                        emojiStr = str(dieNum)
                        emojiName = f"dice_{Combat.translateColorToName('pink')}_{dieNum}"
                        guild_emojis = interaction.guild.emojis
                        matching_emojis = [emoji for emoji in guild_emojis if emoji.name == emojiName]
                        msg += str(num) + " "
                        if len(matching_emojis) > 0:
                            emojiStr = str(matching_emojis[0]) 
                        message = (player["player_name"] + ", you can reroll a"
                                    f" rift die that rolled a {emojiStr} using one of your colony ships.")
                        asyncio.create_task(interaction.channel.send(message, view=viewLyr))
                        hitsToAssign = 1
                        if "unresolvedHits" in game.gamestate["board"][pos]:
                            hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                        game.setUnresolvedHits(hitsToAssign, pos)
                        continue
                if dieNum == 2 or dieNum == 3:
                    continue
                if dieNum == 1 or dieNum == 6:
                    ship = Combat.getShipToSelfHitWithRiftCannon(game, colorOrAI, player_ships, pos)
                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_1"
                    await Combat.assignHitTo(game, buttonID, interaction, False)
                if dieNum > 3:
                    hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                        6, computerVal, pos, 3)
            if len(hittableShips) > 0:
                if len(hittableShips) > 1:
                    if colorOrAI != "ai":
                        msg = (f"{interaction.user.mention}, choose which ship to hit"
                               f" with the die that rolled a {dieNum}. You will deal {dieDam} damage. "
                               "The bot has calculated that you can hit these ships.")
                        view = View()
                        for ship in hittableShips:
                            shipOwner, shipType = ship.split("-")
                            label = "Hit " + Combat.translateShipAbrToName(shipType)
                            buttonID = f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                            view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
                        asyncio.create_task(interaction.channel.send(msg, view=view))
                        hitsToAssign = 1
                        if "unresolvedHits" in game.gamestate["board"][pos]:
                            hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                        game.setUnresolvedHits(hitsToAssign, pos)
                else:
                    ship = hittableShips[0]
                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                    await Combat.assignHitTo(game, buttonID, interaction, False)
        await interaction.message.delete()

    @staticmethod
    async def killPop(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, player):
        pos = buttonID.split("_")[1]
        cube = buttonID.split("_")[2]
        owner = game.gamestate["board"][pos]["owner"]
        advanced = ""
        if "adv" in cube:
            advanced = "advanced "
        msg = f"{player['username']} hit {advanced + cube.replace('adv', '')} population."
        await interaction.channel.send(msg)
        game.remove_pop([cube + "_pop"], pos, game.get_player_from_color(owner), True)
        await interaction.message.delete()
        if len(PopulationButtons.findFullPopulation(game, pos)) == 0:
            game.remove_control(owner, pos)
            view2 = View()
            view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple,
                                  custom_id=f"FCID{player['color']}_addInfluenceFinish_" + pos))
            message = (f"{player['player_name']}, you may place your influence"
                       " on the tile now that you have destroyed all the enemy population.")
            await interaction.channel.send(message, view=view2)
            view3 = View()
            view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                  custom_id=f"FCID{player['color']}_startPopDrop"))
            message = (f"{player['player_name']}, if you have enough colony ships, "
                       "you may use this to drop population after taking control of the sector.")
            await interaction.channel.send(message, view=view3)

    @staticmethod
    async def checkForMorphShield(game: GamestateHelper, pos: str, channel, ships, players):
        for playerColor in players:
            if playerColor != "ai":
                for ship in Combat.getCombatantShipsBySpeed(game, playerColor, ships, pos):
                    player = game.get_player_from_color(playerColor)
                    shipModel = PlayerShip(game.gamestate["players"][player], ship[1])
                    shipName = playerColor + "-" + ship[1]
                    if shipModel.repair > 0 and shipName in game.gamestate["board"][pos].get("damage_tracker", []):
                        if game.gamestate["board"][pos]["damage_tracker"][shipName] > 0:
                            game.repair_damage(shipName, pos)
                            message = (f"{game.gamestate['players'][player]['player_name']} repaired 1 damage"
                                       f" on their {Combat.translateShipAbrToName(ship[1])} using a morph shield.")
                            await channel.send(message)
                            break

    @staticmethod
    async def promptNextSpeed(game: GamestateHelper, pos: str, channel, update: bool):
        currentSpeed = None
        if "currentSpeed" in game.gamestate["board"][pos]:
            currentSpeed = game.gamestate["board"][pos]["currentSpeed"]
        currentRoller = None
        if "currentRoller" in game.gamestate["board"][pos]:
            currentRoller = game.gamestate["board"][pos]["currentRoller"]
        attacker = game.gamestate["board"][pos]["attacker"]
        defender = game.gamestate["board"][pos]["defender"]
        ships = game.gamestate["board"][pos]["player_ships"]
        sortedSpeeds = Combat.getBothCombatantShipsBySpeed(game, defender, attacker, ships, pos)

        found = False
        nextSpeed = -20
        nextOwner = ""
        for speed, owner in sortedSpeeds:
            if any([found, currentSpeed is None, currentRoller is None,
                    currentSpeed is not None and speed < currentSpeed]):
                nextSpeed = speed
                nextOwner = owner
                break
            if speed == currentSpeed and currentRoller == owner:
                found = True
        if nextSpeed == -20:
            await Combat.checkForMorphShield(game, pos, channel, ships, [attacker, defender])
            for speed, owner in sortedSpeeds:
                if speed < 90:
                    nextSpeed = speed
                    nextOwner = owner
                    break
        view = View()
        checker = ""
        if update:
            drawing = DrawHelper(game.gamestate)
            asyncio.create_task(channel.send("Updated view",
                                             file=await asyncio.to_thread(drawing.board_tile_image_file, pos)))
        game.setCurrentRoller(nextOwner, pos)
        game.setCurrentSpeed(nextSpeed, pos)
        initiative = f"Initiative {nextSpeed}"
        if nextSpeed > 90:
            initiative = "Initiative " + str(nextSpeed-99)+" missiles"

        if [nextSpeed, nextOwner] in game.getRetreatingUnits(pos):
            checker = "FCID" + nextOwner + "_"
            playerObj = game.getPlayerObjectFromColor(nextOwner)
            viewedTiles = []
            msg = (f"{playerObj['player_name']} announced a retreat for ships with {initiative}"
                   " and should now choose a controlled sector adjacent that does not contain enemy ships.")
            for tile in Combat.getRetreatTiles(game, pos, nextOwner):
                if tile not in viewedTiles:
                    viewedTiles.append(tile)
                    view.add_item(Button(label=tile, style=discord.ButtonStyle.red,
                                         custom_id=(f"{checker}finishRetreatingUnits_{pos}_"
                                                    f"{nextOwner}_{str(nextSpeed)}_{tile}")))
        else:
            if nextOwner != "ai" and nextOwner != "":
                checker = "FCID" + nextOwner + "_"
                playerObj = game.getPlayerObjectFromColor(nextOwner)
                msg = f"{playerObj['player_name']}, it is your turn to roll your ships with {initiative}. "

                view.add_item(Button(label=f"Roll {initiative} Ships", style=discord.ButtonStyle.green,
                                     custom_id=f"{checker}rollDice_{pos}_{nextOwner}_{str(nextSpeed)}_deleteMsg"))
                if nextSpeed < 99 and len(Combat.getRetreatTiles(game, pos, nextOwner)) > 0:
                    msg += "You may also alternatively choose to start to retreat them. "
                    shipsSpeeds = Combat.getCombatantShipsBySpeed(game, nextOwner, ships, pos)
                    newSpeeds = 0
                    for ship in shipsSpeeds:
                        speed2 = ship[0]
                        if speed2 < 99 and speed2 != int(speed):
                            newSpeeds += 1
                            break
                    if newSpeeds < 1:
                        msg += ("You would lose out on the default"
                                " 1 reputation for battling if you choose to retreat here.")
                    view.add_item(Button(label=f"Retreat {initiative} Ships", style=discord.ButtonStyle.red,
                                         custom_id=f"{checker}startToRetreatUnits_{pos}_{nextOwner}_{str(nextSpeed)}"))
            else:
                view.add_item(Button(label=f"Roll {initiative} Ships For AI", style=discord.ButtonStyle.green,
                                     custom_id=f"{checker}rollDice_{pos}_{nextOwner}_{nextSpeed}_deleteMsg"))
                playerObj = game.getPlayerObjectFromColor(defender if attacker == "ai" else attacker)
                msg = f"{playerObj['player_name']}, please roll the dice for the AI ships with {initiative}."
        asyncio.create_task(channel.send(msg, view=view))

    @staticmethod
    async def finishRetreatingUnits(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, playerObj):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = buttonID.split("_")[3]
        destination = buttonID.split("_")[4]
        oldLength = len(Combat.findPlayersInTile(game, pos))
        game.removeCertainRetreatingUnits((int(speed), colorOrAI), pos)
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        for ship in player_ships:
            if colorOrAI in ship and "orb" not in ship and "mon" not in ship and "sb" not in ship:
                shiptype = ship.split("-")[1]
                player = game.get_player_from_color(colorOrAI)
                shipM = PlayerShip(game.gamestate["players"][player], shiptype)
                if shipM.speed == int(speed):
                    game.remove_units([ship], pos)
                    game.add_units([ship], destination)
        await interaction.message.delete()
        await interaction.channel.send(f"{playerObj['player_name']} has retreated all ships"
                                       f" with initiative {speed} to {destination}.")
        dracoNAnc = (len(Combat.findPlayersInTile(game, pos)) == 2
                     and "anc" in Combat.findShipTypesInTile(game, pos)
                     and "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game, pos)[1]))
        if len(Combat.findPlayersInTile(game, pos)) < 2 or dracoNAnc:
            await Combat.declareAWinner(game, interaction, pos)
        elif oldLength != len(Combat.findPlayersInTile(game, pos)):
            drawing = DrawHelper(game.gamestate)
            await interaction.channel.send("Updated view", view=Combat.getCombatButtons(game, pos),
                                           file=drawing.board_tile_image_file(pos))
            await Combat.startCombat(game, interaction.channel, pos)
        else:
            await Combat.promptNextSpeed(game, pos, interaction.channel, True)

    @staticmethod
    def getRetreatTiles(game: GamestateHelper, pos: str, color: str):
        playerObj = game.getPlayerObjectFromColor(color)
        player_helper = PlayerHelper(game.get_player_from_color(color), playerObj)
        techsResearched = player_helper.getTechs()
        configs = Properties()
        if game.gamestate.get("5playerhyperlane"):
            if game.gamestate.get("player_count") == 5:
                with open("data/tileAdjacencies_5p.properties", "rb") as f:
                    configs.load(f)
            elif game.gamestate.get("player_count") == 4:
                with open("data/tileAdjacencies_4p.properties", "rb") as f:
                    configs.load(f)
            else:
                with open("data/tileAdjacencies.properties", "rb") as f:
                    configs.load(f)
        else:
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
        wormHoleGen = "wog" in techsResearched
        validTiles = []
        for tile in playerObj["owned_tiles"]:
            players = Combat.findPlayersInTile(game, tile)
            if InfluenceButtons.areTwoTilesAdjacent(game, pos, tile, configs, wormHoleGen):
                if "Draco" not in player_helper.stats["name"]:
                    if len(players) > 1:
                        continue
                    if len(players) == 1 and players[0] != color:
                        continue
                    validTiles.append(tile)
                else:
                    validTile = True
                    for player in players:
                        if player != color:
                            if player == "ai":
                                playerShips = game.gamestate["board"][tile]["player_ships"][:]
                                if any("anc" in s for s in playerShips):
                                    valid = True
                                else:
                                    validTile = False
                            else:
                                validTile = False
                    if validTile:
                        validTiles.append(tile)
        return validTiles

    @staticmethod
    async def startToRetreatUnits(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = buttonID.split("_")[3]
        game.setRetreatingUnits((int(speed), colorOrAI), pos)
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        player = game.getPlayerObjectFromColor(colorOrAI)
        await interaction.message.delete()
        message = (f"{player['player_name']} has chosen to start to retreat the ships with initiative {speed}. "
                   "They will be prompted to retreat when their turn comes around again.")
        await interaction.channel.send(message)
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        newSpeeds = 0
        for ship in ships:
            speed2 = ship[0]
            if speed2 < 99 and speed2 != int(speed):
                newSpeeds += 1
                break
        if newSpeeds < 1:
            game.setRetreatingPenalty(colorOrAI, pos)
            message = (f"{interaction.user.mention} is attempting  to retreat all their remaining ships"
                       " and will thus not receive the default 1 reputation tile draw at the end of combat")
            await interaction.channel.send(message)
        await Combat.promptNextSpeed(game, pos, interaction.channel, False)

    @staticmethod
    async def declareAWinner(game: GamestateHelper, interaction: discord.Interaction, pos: str):
        game.updateSaveFile()

        actions_channel = discord.utils.get(interaction.guild.channels, name=game.game_id + "-actions")
        if actions_channel is not None and isinstance(actions_channel, discord.TextChannel):
            await actions_channel.send(f"Combat in tile {pos} has concluded. "
                                       f"There are {len(Combat.findTilesInConflict(game))} tiles left in conflict.")
            if len(Combat.findTilesInConflict(game)) == 0:
                role = discord.utils.get(interaction.guild.roles, name=game.game_id)
                view = View()
                view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                     custom_id="startPopDrop"))
                asyncio.create_task(actions_channel.send(role.mention+" Please run upkeep after all post combat events are resolved. "
                                           "You can use this button to drop pop after taking control of a tile",
                                           view=view))
        if "combatants" in game.gamestate["board"][pos]:
            players = game.gamestate["board"][pos]["combatants"]
        else:
            players = Combat.findPlayersInTile(game, pos)
        countDraw = 1
        game.removeFromKey("tilesToResolve", int(game.gamestate["board"][pos]["sector"]))
        for playerColor in players:
            if playerColor == "ai":
                continue
            player = game.getPlayerObjectFromColor(playerColor)
            count = str(game.getReputationTilesToDraw(pos, playerColor))
            view = View()
            label = f"Draw {count} Reputation"
            buttonID = (f"FCID{playerColor}_drawReputation_{count}_"
                        f"{game.gamestate['board'][pos]['sector']}_{countDraw}_{playerColor}")
            view.add_item(Button(label=label, style=discord.ButtonStyle.green, custom_id=buttonID))
            label = "Decline"
            buttonID = (f"FCID{playerColor}_dontDrawReputation_"
                        f"{game.gamestate['board'][pos]['sector']}_{countDraw}_{playerColor}")
            view.add_item(Button(label=label, style=discord.ButtonStyle.red, custom_id=buttonID))
            msg = (f"{player['player_name']}, the bot believes you should draw {count} reputation tiles here. "
                   "Click to do so or press decline if the bot messed up. "
                   "If other battles/players need to resolve first, "
                   "your draw will be queued after you click this button")
            if int(count) > 0:
                if "tilesToResolve" in game.gamestate:
                    game.addToKey("queuedQuestions", [int(game.gamestate["board"][pos]["sector"]),
                                                      countDraw, playerColor])
                    countDraw += 1
                asyncio.create_task(interaction.channel.send(msg, view=view))
        winner = Combat.findPlayersInTile(game, pos)[0]
        owner = game.gamestate["board"][pos]["owner"]

        if winner != "ai" and owner != winner:
            player = game.getPlayerObjectFromColor(winner)
            playerName = player["player_name"]
            if owner == 0:
                if game.gamestate["board"][pos]["disctile"] != 0:
                    view = View()
                    view.add_item(Button(label="Explore Discovery Tile", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{winner}_exploreDiscoveryTile_{pos}_deleteMsg"))
                    message = f"{playerName}, you may explore the discovery tile."
                    asyncio.create_task(interaction.channel.send(message, view=view))
                view2 = View()
                view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple,
                                      custom_id=f"FCID{winner}_addInfluenceFinish_{pos}"))
                message = f"{playerName}, you may place your influence on the tile."
                asyncio.create_task(interaction.channel.send(message, view=view2))
                view3 = View()
                view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                      custom_id=f"FCID{player['color']}_startPopDrop"))
                message = (f"{playerName}, if you have enough colony ships,"
                           " you may use this to drop population after taking control of the sector.")
                asyncio.create_task(interaction.channel.send(message, view=view3))
            else:
                p2 = game.getPlayerObjectFromColor(owner)
                player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
                player_helper2 = PlayerHelper(game.get_player_from_color(p2["color"]), p2)
                if (p2["name"] == "Planta" or game.is_population_gone(pos) or ("neb" in player_helper.getTechs() and "nea" not in player_helper2.getTechs())):
                    if game.gamestate["board"][pos]["disctile"] != 0:
                        view4 = View()
                        view4.add_item(Button(label="Explore Discovery Tile", style=discord.ButtonStyle.green,
                                             custom_id=f"FCID{winner}_exploreDiscoveryTile_{pos}_deleteMsg"))
                        message = f"{playerName}, you may explore the discovery tile."
                        asyncio.create_task(interaction.channel.send(message, view=view4))
                    view = View()
                    view.add_item(Button(label="Destroy All Population", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{winner}_removeInfluenceFinish_{pos}_graveYard"))
                    message = f"{playerName}, you may destroy all enemy influence and population automatically."
                    asyncio.create_task(interaction.channel.send(message, view=view))
                    view2 = View()
                    view2.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple,
                                          custom_id=f"FCID{winner}_addInfluenceFinish_{pos}"))
                    message = (f"{playerName}, you may place your influence on the"
                               " tile after destroying the enemy population.")
                    asyncio.create_task(interaction.channel.send(message, view=view2))
                    view3 = View()
                    view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                          custom_id=f"FCID{player['color']}_startPopDrop"))
                    message = (f"{playerName}, if you have enough colony ships,"
                               " you may use this to drop population after taking control of the sector.")
                    asyncio.create_task(interaction.channel.send(message, view=view3))
                else:
                    if p2["name"] == "Descendants of Draco" and game.gamestate["board"][pos]["disctile"] != 0:
                        await interaction.channel.send(f"**REMINDER: Do not resolve the discovery tile until bombing "
                                                       f"population has been resolved. In the case that Draco has population "
                                                       f"remaining after bombardment, they will gain the discovery tile. This "
                                                       f"is not fully automated yet so please use the draw tile command "
                                                       f"once the winner is decided.**")
                    view = View()
                    view.add_item(Button(label="Roll to Destroy Population", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{winner}_rollDice_{pos}_{winner}_1000_deleteMsg"))
                    message = f"{playerName}, you may roll to attempt to kill enemy population."
                    asyncio.create_task(interaction.channel.send(message, view=view))


    @staticmethod
    async def assignHitTo(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, button: bool):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        ship = buttonID.split("_")[3]
        dieNum = buttonID.split("_")[4]
        dieDam = buttonID.split("_")[5]
        shipType = ship.split("-")[1]
        shipOwner = ship.split("-")[0]
        if shipOwner == "ai":
            advanced = game.gamestate["advanced_ai"]
            worldsafar = game.gamestate["wa_ai"]
            if shipType+"_type" in game.gamestate:
                advanced = "adv" in game.gamestate[shipType+"_type"]
                worldsafar ="wa" in game.gamestate[shipType+"_type"]
            shipModel = AI_Ship(shipType, advanced, worldsafar)
        else:
            player = game.get_player_from_color(shipOwner)
            shipModel = PlayerShip(game.gamestate["players"][player], shipType)
        damage = game.add_damage(ship, pos, int(dieDam))
        if colorOrAI != "ai":
            msg = (f"{interaction.user.mention} dealt {dieDam} damage to a"
                   f" {Combat.translateShipAbrToName(shipType)} with a die that rolled a {str(dieNum)}. ")
        else:
            msg = (f"The AI dealt {dieDam} damage to a {Combat.translateShipAbrToName(shipType)}"
                   f" with a die that rolled a {str(dieNum)}. ")
        msg += f"The damaged ship has {shipModel.hull - damage + 1}/{shipModel.hull + 1} hp left. "
        oldLength = len(Combat.findPlayersInTile(game, pos))
        if shipModel.hull < damage:
            if colorOrAI not in ship:
                game.destroy_ship(ship, pos, colorOrAI)
            else:
                dummyKiller = "ai"
                attacker = game.gamestate["board"][pos].get("attacker",None)
                defender = game.gamestate["board"][pos].get("defender",None)
                if attacker != None and attacker != colorOrAI:
                    dummyKiller = attacker
                if defender  != None and defender  != colorOrAI:
                    dummyKiller = defender
                game.destroy_ship(ship, pos, dummyKiller)
            if colorOrAI != "ai":
                msg += (f"{interaction.user.name} destroyed the"
                        f" {Combat.translateShipAbrToName(shipType)} due to the damage exceeding the ships hull.")
            else:
                msg += (f"The AI destroyed the {Combat.translateShipAbrToName(shipType)}"
                        f" due to the damage exceeding the ships hull.")
            await interaction.channel.send(msg)
            dracoNAnc = (len(Combat.findPlayersInTile(game, pos)) == 2
                         and "anc" in Combat.findShipTypesInTile(game, pos)
                         and "Draco" in game.find_player_faction_name_from_color(Combat.findPlayersInTile(game,
                                                                                                          pos)[1]))
            if len(Combat.findPlayersInTile(game, pos)) < 2 or dracoNAnc:
                await Combat.declareAWinner(game, interaction, pos)
            elif oldLength != len(Combat.findPlayersInTile(game, pos)):
                drawing = DrawHelper(game.gamestate)
                asyncio.create_task(interaction.channel.send("Updated view", view=Combat.getCombatButtons(game, pos),
                                               file=await asyncio.to_thread(drawing.board_tile_image_file, pos)))
                await Combat.startCombat(game, interaction.channel, pos)
        else:
            await interaction.channel.send(msg)
        if button:
            await interaction.message.delete()
            hitsToAssign = 0
            if "unresolvedHits" in game.gamestate["board"][pos]:
                hitsToAssign = max(game.gamestate["board"][pos]["unresolvedHits"] - 1, 0)
            game.setUnresolvedHits(hitsToAssign, pos)
            if hitsToAssign == 0 and oldLength == len(Combat.findPlayersInTile(game, pos)):
                await Combat.promptNextSpeed(game, pos, interaction.channel, True)

    @staticmethod
    async def resolveQueue(game: GamestateHelper, interaction: discord.Interaction, forcedResolve=False):
        foundNoSuccess = False
        success = 1
        while not foundNoSuccess and success < 20:
            foundNoSuccess = True
            queuedDraws = game.gamestate["queuedDraws"][:]
            for system, drawOrder, color, num_options in queuedDraws:
                systemAheadNeedsToResolve = False
                for system2 in game.gamestate["tilesToResolve"]:
                    if system2 > system:
                        systemAheadNeedsToResolve = True
                if not systemAheadNeedsToResolve or forcedResolve:
                    goodToResolve = True
                    for system2, drawOrder2, color2, num_options2 in game.gamestate["queuedDraws"]:
                        if int(system2) > int(system) or (int(system2) == int(system) and drawOrder > drawOrder2):
                            goodToResolve = False
                    for system2, drawOrder2, color2 in game.gamestate["queuedQuestions"]:
                        if int(system2) > int(system) or (int(system2) == int(system) and drawOrder > drawOrder2):
                            goodToResolve = False
                    if goodToResolve:
                        foundNoSuccess = False
                        player_helper = PlayerHelper(game.get_player_from_color(color),
                                                     game.getPlayerObjectFromColor(color))
                        await ReputationButtons.resolveGainingReputation(game, num_options, interaction,
                                                                         player_helper, True)
                        game.removeFromKey("queuedDraws", [system, drawOrder, color, num_options])
                        success += 1

    @staticmethod
    async def dontDrawReputation(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, player_helper):
        system = int(buttonID.split("_")[1])
        drawOrder = int(buttonID.split("_")[2])
        color = buttonID.split("_")[3]
        if "tilesToResolve" in game.gamestate:
            game.removeFromKey("queuedQuestions", [system, drawOrder, color])
            await Combat.resolveQueue(game, interaction)
        await interaction.message.delete()

    @staticmethod
    async def drawReputation(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, player_helper):
        num_options = int(buttonID.split("_")[1])
        system = int(buttonID.split("_")[2])
        drawOrder = int(buttonID.split("_")[3])
        color = buttonID.split("_")[4]
        if "tilesToResolve" in game.gamestate:
            game.removeFromKey("queuedQuestions", [system, drawOrder, color])
            game.addToKey("queuedDraws", [system, drawOrder, color, num_options])
            await Combat.resolveQueue(game, interaction)
            if [system, drawOrder, color, num_options] in game.gamestate["queuedDraws"]:
                asyncio.create_task(interaction.channel.send(f"{interaction.user.name}, your reputation draw has been queued"))
            else:
                asyncio.create_task(interaction.channel.send(f"{interaction.user.name} drew {num_options} reputation tiles."))
        else:
            await ReputationButtons.resolveGainingReputation(game, num_options, interaction, player_helper, False)
            asyncio.create_task(interaction.channel.send(f"{interaction.user.name} drew {num_options} reputation tiles."))
        asyncio.create_task(interaction.message.delete())

    @staticmethod
    async def refreshImage(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos = buttonID.split("_")[1]
        drawing = DrawHelper(game.gamestate)
        view = View()
        if len(Combat.findPlayersInTile(game, pos)) > 1:
            view = Combat.getCombatButtons(game, pos)
        await interaction.channel.send("Updated view", view=view,
                                       file=await asyncio.to_thread(drawing.board_tile_image_file, pos))

    @staticmethod
    def translateColorToName(dieColor: str):
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
    def translateColorToDamage(dieColor: str, dieValue: int):
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
    def translateShipAbrToName(ship: str):
        if "-" in ship:
            ship = ship.split("-")[1]
        ship = ship.replace("adv", "").replace("ai-", "")
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
