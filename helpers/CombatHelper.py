import asyncio
import random

import discord
from discord.ui import View, Button
from Buttons.Influence import InfluenceButtons
from Buttons.Population import PopulationButtons
from Buttons.Reputation import ReputationButtons
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
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
            if "orb" in ship:
                color = game.gamestate["board"][pos]["owner"]
            if color not in players:
                players.append(color)
        return players

    @staticmethod
    def sideOf(value):
        """A side is a list of colours. Saves written before alliances stored a
        bare colour, so accept that too."""
        if not value:
            return []
        if isinstance(value, str):
            return [value]
        return list(value)

    @staticmethod
    def currentPairing(game: GamestateHelper, pos: str):
        """The two sides that fight next. Draco may not battle the Ancients:
        when his Alliance faces them, his Ally fights and he sits it out (FAQ)."""
        sides = Combat.findSidesInTile(game, pos)[-2:]
        if len(sides) == 2 and "anc" in Combat.findShipTypesInTile(game, pos):
            for ancients, other in ((0, 1), (1, 0)):
                if "ai" in sides[ancients]:
                    allies = [color for color in sides[other]
                              if "Draco" not in game.find_player_faction_name_from_color(color)]
                    if allies:
                        sides[other] = allies
        return sides

    @staticmethod
    def isDracoAgainstAncients(game: GamestateHelper, pos: str):
        """FAQ: with nobody but Ancients left in the sector, Draco does not fight."""
        players = Combat.findPlayersInTile(game, pos)
        return (len(players) == 2 and "anc" in Combat.findShipTypesInTile(game, pos)
                and any("Draco" in game.find_player_faction_name_from_color(color) for color in players))

    @staticmethod
    def findSidesInTile(game: GamestateHelper, pos: str):
        """The colours in a sector grouped into sides: an Alliance fights as one
        side, so its members never end up opposing each other. Order matches
        findPlayersInTile, so the last side is the most recent arrival."""
        sides = []
        for color in Combat.findPlayersInTile(game, pos):
            for side in sides:
                if any(game.areAllied(color, member) for member in side):
                    side.append(color)
                    break
            else:
                sides.append([color])
        return sides

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
            if len(Combat.findSidesInTile(game, tile)) > 1:
                game.fixshipsOrder(tile)
                # Don't start combat between draco and ancients
                if Combat.isDracoAgainstAncients(game, tile):
                    continue
                tiles.append((int(tile_map[tile]["sector"]), tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)
        return sorted_tiles

    @staticmethod
    def findTilesInContention(game: GamestateHelper):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            sides = Combat.findSidesInTile(game, tile)
            if len(sides) != 1:
                continue
            side = sides[0]
            if (tile_map[tile]["owner"] != 0
                    and tile_map[tile]["owner"] not in side
                    and not any(game.areAllied(tile_map[tile]["owner"], color) for color in side)
                    and "ai" not in side):
                tiles.append((int(tile_map[tile]["sector"]), tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)
        return sorted_tiles

    @staticmethod
    def findUnownedTilesToTakeOver(game: GamestateHelper):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            if Combat.isDracoAgainstAncients(game, tile):
                if tile_map[tile].get("owner") == 0:
                    tiles.append((int(tile_map[tile]["sector"]), tile))
            else:
                sides = Combat.findSidesInTile(game, tile)
                if (len(sides) == 1 and "ai" not in sides[0] and tile_map[tile].get("owner") == 0
                        and tile_map[tile].get("type") != "nebula"):
                    tiles.append((int(tile_map[tile]["sector"]), tile))
        return sorted(tiles, key=lambda x: x[0], reverse=True)

    @staticmethod
    async def startCombat(game: GamestateHelper, channel, pos):
        drawing = DrawHelper(game.gamestate)
        sides = Combat.currentPairing(game, pos)
        game.setAttackerAndDefender(sides[1], sides[0], pos)
        game.setCurrentRoller(None, pos)
        game.setCurrentRoller(None, pos)
        for side in sides:
            for player in side:
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

            # Later pairings add their own colours, so only those who fight draw Reputation.
            participating_colors = [color for side in Combat.currentPairing(game, tile[1]) for color in side]
            game.setCombatants(participating_colors, tile[1])
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
            playerSide = Combat.findSidesInTile(game, tile2[1])[0]
            entryOrder = game.getCombatEntryOrder(tile2[1])
            playerSide.sort(key=lambda color: entryOrder.index(color) if color in entryOrder else len(entryOrder))
            playerColor = playerSide[0]
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
            playerSide = [color for color in Combat.findSidesInTile(game, tile3[1])[0] if color != "ai"]
            if not playerSide:
                playerSide = [color for color in Combat.findPlayersInTile(game, tile3[1]) if color != "ai"]
            entryOrder = game.getEntryOrder(tile3[1])
            playerSide.sort(key=lambda color: entryOrder.index(color) if color in entryOrder else len(entryOrder))
            playerColor = playerSide[0]
            winner = playerColor
            pos = tile3[1]
            player = game.getPlayerObjectFromColor(playerColor)
            playerName = player['player_name']
            view2 = View()
            for color in playerSide:
                label = "Place Influence"
                if len(playerSide) > 1:
                    label = f"Place Influence ({game.getPlayerObjectFromColor(color)['name']})"
                view2.add_item(Button(label=label, style=discord.ButtonStyle.blurple,
                                      custom_id=f"FCID{color}_addInfluenceFinish_{pos}"))
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

            if Combat.exile_orbital_exists(game, pos) and "orb" in unit:
                owner = game.gamestate["board"][pos]["owner"]
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
    def getBothCombatantShipsBySpeed(game: GamestateHelper, defender, attacker, playerShipsList, pos):
        """defender and attacker are sides: lists of colours."""
        ships = []
        for unit in playerShipsList:
            unitType = unit.split("-")[1]
            owner = unit.split('-')[0]
            if Combat.exile_orbital_exists(game, pos) and "orb" in unit:
                owner = game.gamestate["board"][pos]["owner"]
            elif "orb" in unit or "mon" in unit:
                continue
            if owner in defender or owner in attacker:
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
        sorted_ships = sorted(ships, key=lambda x: (x[0], x[1] in defender), reverse=True)
        return sorted_ships

    @staticmethod
    def allianceInCombat(game: GamestateHelper, pos: str):
        """True when either pairing is an Alliance. Its members field the same
        ship types, so buttons without an owner would be ambiguous."""
        tile = game.gamestate["board"][pos]
        return len(Combat.sideOf(tile.get("attacker"))) > 1 or len(Combat.sideOf(tile.get("defender"))) > 1

    @staticmethod
    def getCombatantTag(game: GamestateHelper, pos: str, colorOrAI: str):
        """Faction name and icon to add to one combatant's buttons, or empty
        strings when no Alliance is in the fight and the plain label suffices."""
        if colorOrAI == "ai" or not Combat.allianceInCombat(game, pos):
            return "", None
        player = game.getPlayerObjectFromColor(colorOrAI)
        return f" ({player['name']})", game.getPlayerEmoji(player)

    @staticmethod
    def getTargetButton(game: GamestateHelper, pos: str, ship: str):
        """Label and icon for a target button. An Alliance's members field the
        same ship types, so the ship type alone does not say whose ship it is."""
        owner, shipType = ship.split("-", 1)
        suffix, emoji = Combat.getCombatantTag(game, pos, owner)
        return f"Hit {Combat.translateShipAbrToName(shipType)}{suffix}", emoji

    @staticmethod
    def getOpponentUnitsThatCanBeHit(game: GamestateHelper, colorOrAI: str, playerShipsList,
                                     dieVal: int, computerVal: int, pos: str, speed: int):
        players = Combat.findPlayersInTile(game, pos)
        hittableShips = []
        if dieVal == 1 or dieVal + computerVal < 6:
            return hittableShips
        if len(players) < 2:
            if speed == 1000:
                if dieVal == 6 or dieVal + computerVal > 5:
                    for pop in PopulationButtons.findFullPopulation(game, pos):
                        hittableShips.append(pop)
            return hittableShips
        attacker = Combat.sideOf(game.gamestate["board"][pos].get("attacker"))
        defender = Combat.sideOf(game.gamestate["board"][pos].get("defender"))
        if colorOrAI in attacker:
            opponents = list(defender)
        elif colorOrAI in defender:
            opponents = list(attacker)
        elif not attacker and not defender:
            # No sides recorded yet, as in an older save: fall back to position.
            if colorOrAI == players[len(players) - 1]:
                opponents = [players[len(players) - 2]]
            else:
                opponents = [players[len(players) - 1]]
        else:
            # This player is not in the pairing that is currently fighting.
            return hittableShips
        # The rules break ties between allies by sector entry: the player who
        # arrived last is the first target. Every other rule is unchanged.
        entryOrder = game.getEntryOrder(pos)
        opponents.sort(key=lambda color: entryOrder.index(color) if color in entryOrder else -1, reverse=True)

        for opponent in opponents:
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
    def canResolveStalemate(game: GamestateHelper, pos: str):
        tile = game.gamestate["board"][pos]
        if tile.get("currentSpeed") is None or int(tile["currentSpeed"]) >= 90:
            return False
        if (tile.get("unresolvedHits", 0) > 0
                or tile.get("pendingRiftDice")
                or any(tile.get("pendingRiftBackfire", {}).values())):
            return False
        attacker = Combat.sideOf(tile.get("attacker"))
        defender = Combat.sideOf(tile.get("defender"))
        if not attacker or not defender:
            return False
        ships = tile.get("player_ships", [])
        for ship in ships:
            color, ship_type = ship.split("-", 1)
            if "mon" in ship:
                continue
            if "orb" in ship:
                if not Combat.exile_orbital_exists(game, pos):
                    continue
                color = tile["owner"]
            if color not in attacker and color not in defender:
                continue
            if color == "ai":
                advanced = game.gamestate["advanced_ai"]
                worldsafar = game.gamestate["wa_ai"]
                if ship_type + "_type" in game.gamestate:
                    advanced = "adv" in game.gamestate[ship_type + "_type"]
                    worldsafar = "wa" in game.gamestate[ship_type + "_type"]
                has_weapon = bool(AI_Ship(ship_type, advanced, worldsafar).dice)
            else:
                player = game.get_player_from_color(color)
                has_weapon = bool(PlayerShip(game.gamestate["players"][player], ship_type).dice)
            if has_weapon:
                return False
        return True

    @staticmethod
    async def resolveStalemate(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        parts = buttonID.split("_")
        if len(parts) != 3 or parts[0] != "resolveStalemate":
            await interaction.channel.send("This stalemate action is invalid. Refresh the combat view.")
            return
        _, pos, attacker_color = parts
        tile = game.gamestate["board"][pos]
        sides = Combat.currentPairing(game, pos)
        if len(sides) != 2:
            await interaction.channel.send("This battle no longer has two opposing sides. Refresh the combat view.")
            return
        expected_attacker, expected_defender = sides[1], sides[0]
        owner = tile.get("owner")
        if isinstance(owner, str) and owner in expected_attacker:
            expected_attacker, expected_defender = expected_defender, expected_attacker
        attacker = Combat.sideOf(tile.get("attacker"))
        defender = Combat.sideOf(tile.get("defender"))
        if (attacker_color not in attacker or set(attacker) != set(expected_attacker)
                or set(defender) != set(expected_defender)):
            await interaction.channel.send("The combat pairing changed. Refresh the combat view.")
            return
        if not Combat.canResolveStalemate(game, pos):
            await interaction.channel.send("The stalemate cannot be resolved while weapons or hits remain.")
            return

        defenders = [color for color in defender if color != "ai"]
        entry_order = game.getCombatEntryOrder(pos)
        defenders.sort(key=lambda color: entry_order.index(color) if color in entry_order else len(entry_order))
        if not defenders:
            defenders = ["ai"]

        attacker_ships = []
        tile_ships = tile.get("player_ships", [])
        for color in attacker:
            for _speed, ship_type, amount in Combat.getCombatantShipsBySpeed(game, color, tile_ships, pos):
                ship = ship_type if color == "ai" else f"{color}-{ship_type}"
                attacker_ships.extend([ship] * amount)
        def ship_size(ship):
            color, ship_type = ship.split("-", 1)
            ship_type = ship_type.removesuffix("adv")
            if color == "ai":
                return {"int": 1, "cru": 2, "drd": 3, "anc": 4, "grd": 5, "gcds": 6}.get(ship_type, 0)
            player = game.get_player_from_color(color)
            return PlayerShip(game.gamestate["players"][player], ship_type).cost

        attacker_ships.sort(key=ship_size, reverse=True)
        old_length = len(Combat.findPlayersInTile(game, pos))
        for index, ship in enumerate(attacker_ships):
            game.destroy_ship(ship, pos, defenders[index % len(defenders)])

        await interaction.channel.send("The stalemate destroyed the attacking ships.")
        await Combat.checkCombatEnd(game, interaction, pos, old_length)

    @staticmethod
    def getCombatButtons(game: GamestateHelper, pos: str):
        view = View()
        sides = Combat.currentPairing(game, pos)
        if len(sides) < 2:
            return view
        game.setAttackerAndDefender(sides[1], sides[0], pos)
        if len(sides) > 1:
            attacker = Combat.sideOf(game.gamestate["board"][pos]["attacker"])
            defender = Combat.sideOf(game.gamestate["board"][pos]["defender"])
            ships = game.gamestate["board"][pos]["player_ships"][:]
            sortedSpeeds = Combat.getBothCombatantShipsBySpeed(game, defender, attacker, ships, pos)
            for speed, owner in sortedSpeeds:
                # Each ship rolls for its own colour, even when its side is an Alliance.
                checker = "" if owner == "ai" else f"FCID{owner}_"
                suffix, emoji = Combat.getCombatantTag(game, pos, owner)
                if owner in defender:
                    if speed < 90:
                        view.add_item(Button(label=f"(Defender) Roll Initative {speed} Ships{suffix}",
                                            style=discord.ButtonStyle.green, emoji=emoji,
                                            custom_id=f"{checker}rollDice_{pos}_{owner}_{str(speed)}_defender"))
                    else:
                        view.add_item(Button(label=f"(Defender) Roll Initative {speed-99} Missiles{suffix}",
                                            style=discord.ButtonStyle.green, emoji=emoji,
                                            custom_id=f"{checker}rollDice_{pos}_{owner}_{str(speed)}_defender"))
                else:
                    if speed < 90:
                        view.add_item(Button(label=f"(Attacker) Roll Initative {speed} Ships{suffix}",
                                            style=discord.ButtonStyle.red, emoji=emoji,
                                            custom_id=f"{checker}rollDice_{pos}_{owner}_{str(speed)}_attacker"))
                    else:
                        view.add_item(Button(label=f"(Attacker) Roll Initative {speed-99} Missiles{suffix}",
                                            style=discord.ButtonStyle.red, emoji=emoji,
                                            custom_id=f"{checker}rollDice_{pos}_{owner}_{str(speed)}_attacker"))
        view.add_item(Button(label="Refresh Image", style=discord.ButtonStyle.blurple, custom_id=f"refreshImage_{pos}"))
        view.add_item(Button(label="Remove Units", style=discord.ButtonStyle.gray, custom_id=f"removeUnits_{pos}"))
        if Combat.canResolveStalemate(game, pos) and attacker:
            for color in attacker:
                checker = "" if color == "ai" else f"FCID{color}_"
                suffix, emoji = Combat.getCombatantTag(game, pos, color)
                view.add_item(Button(label=f"Resolve Stalemate (Destroy Attacking Ships){suffix}",
                                     style=discord.ButtonStyle.red, emoji=emoji,
                                     custom_id=f"{checker}resolveStalemate_{pos}_{color}"))
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
        await Combat.checkCombatEnd(game, interaction, pos, oldLength)

    @staticmethod
    def getRiftBackfireAllocation(game: GamestateHelper, colorOrAI, player_ships, pos, totalDamage):
        """Pool a salvo's rift backfire over the owner's rift ships.
        Destroy largest to smallest if possible, else deal as much damage as
        possible in that order."""
        entries = []
        for _speed, shipType, _amount in Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos):
            ship = colorOrAI + "-" + shipType
            player = game.get_player_from_color(colorOrAI)
            shipModel = PlayerShip(game.gamestate["players"][player], shipType)
            if "pink" not in shipModel.dice:
                continue
            needed = shipModel.hull + 1 - game.add_damage(ship, pos, 0)
            entries.append((ship, shipModel.cost, needed))
        entries.sort(key=lambda entry: entry[1], reverse=True)
        allocation = []
        remaining = totalDamage
        for ship, _cost, needed in entries:
            if needed <= remaining:
                allocation.append((ship, needed))
                remaining -= needed
        allocated = [ship for ship, _damage in allocation]
        for ship, _cost, needed in entries:
            if remaining <= 0:
                break
            if ship not in allocated:
                damage = min(remaining, needed)
                allocation.append((ship, damage))
                remaining -= damage
        return allocation

    @staticmethod
    async def applyRiftBackfire(game: GamestateHelper, colorOrAI, interaction: discord.Interaction, pos, totalDamage,
                                deferEnd: bool = False):
        for ship, damage in Combat.getRiftBackfireAllocation(game, colorOrAI,
                                                             game.gamestate["board"][pos]["player_ships"][:],
                                                             pos, totalDamage):
            buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_1_{damage}"
            await Combat.assignHitTo(game, buttonID, interaction, False, deferEnd=deferEnd)

    @staticmethod
    async def resolvePendingRiftBackfire(game: GamestateHelper, colorOrAI, interaction: discord.Interaction,
                                         pos, shipType, deferEnd: bool = False):
        """Apply a Ship type's pooled backfire once its last deferred Lyra die is decided."""
        board = game.gamestate["board"][pos]
        pending = board.get("pendingRiftBackfire", {}).get(shipType, 0)
        board.setdefault("pendingRiftBackfire", {})[shipType] = 0
        game.update()
        if pending > 0:
            await Combat.applyRiftBackfire(game, colorOrAI, interaction, pos, pending, deferEnd=deferEnd)

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
                        matching_emojis = ([Emoji._app[emojiName]] if emojiName in Emoji._app
                                           else [e for e in interaction.guild.emojis if e.name == emojiName])
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
        pendingDice = game.gamestate["board"][pos]["pendingRiftDice"]
        shipType = pendingDice.pop(str(counter))
        if dieNum == 1 or dieNum == 6:
            pendingBackfire = game.gamestate["board"][pos].setdefault("pendingRiftBackfire", {})
            pendingBackfire[shipType] = pendingBackfire.get(shipType, 0) + 1
        game.update()
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
                        label, emoji = Combat.getTargetButton(game, pos, ship)
                        buttonID = (f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}"
                                    f"_{ship}_{dieNum}_{dieDam}_{counter}")
                        view.add_item(Button(label=label, emoji=emoji, style=discord.ButtonStyle.red,
                                                custom_id=buttonID))
                    await interaction.channel.send(msg, view=view)
                    hitsToAssign = 1
                    if "unresolvedHits" in game.gamestate["board"][pos]:
                        hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                    game.setUnresolvedHits(hitsToAssign, pos)
                else:
                    ship = hittableShips[0]
                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                    await Combat.assignHitTo(game, buttonID, interaction, False, deferEnd=True)
            hitsToAssign = 0

        board = game.gamestate["board"][pos]
        if shipType not in pendingDice.values():
            await Combat.resolvePendingRiftBackfire(game, colorOrAI, interaction, pos, shipType, deferEnd=True)
        if speed != 1000:
            if "unresolvedHits" in game.gamestate["board"][pos]:
                hitsToAssign = board["unresolvedHits"]
            salvoDone = hitsToAssign == 0 and not pendingDice
            if salvoDone:
                await Combat.checkCombatEnd(game, interaction, pos, oldLength)
            if salvoDone and oldLength == len(Combat.findPlayersInTile(game, pos)):
                await Combat.promptNextSpeed(game, pos, interaction.channel, update)
        await interaction.message.delete()
    @staticmethod
    async def rollDice(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = int(buttonID.split("_")[3])
        tile = game.gamestate["board"][pos]
        pairing = Combat.sideOf(tile.get("attacker")) + Combat.sideOf(tile.get("defender"))
        # Initiative 1000 is population bombing, which has no pairing.
        if speed != 1000 and pairing and colorOrAI not in pairing:
            await interaction.channel.send("The combat pairing changed. Press Refresh Image and roll again.")
            return
        if colorOrAI == "ai":
            await Combat.rollDiceAI(game, buttonID, interaction)
            return
        oldLength = len(Combat.findPlayersInTile(game, pos))
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        game.setCurrentRoller(colorOrAI, pos)
        game.setCurrentSpeed(speed, pos)
        player = None
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, player_ships, pos)
        update = False
        popRiftProtector = True
        deferredEnd = False
        counter = 0
        for ship in ships:
            if ship[0] == speed or speed == (ship[0]+99) or speed == 1000:
                name = interaction.user.mention
                player = game.get_player_from_color(colorOrAI)
                rollerType = ship[1]
                shipModel = PlayerShip(game.gamestate["players"][player], rollerType)
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
                shipRiftBackfire = 0
                for x in range(ship[2]):
                    for die in dice:
                        split = False
                        random_number = random.randint(1, 6)
                        num = str(random_number).replace("1", "Miss").replace("6", ":boom:")
                        emojiName = f"dice_{Combat.translateColorToName(die)}_{random_number}"
                        matching_emojis = ([Emoji._app[emojiName]] if emojiName in Emoji._app
                                           else [e for e in interaction.guild.emojis if e.name == emojiName])
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
                                    matching_emojis = ([Emoji._app[emojiName]] if emojiName in Emoji._app
                                                       else [e for e in interaction.guild.emojis if e.name == emojiName])
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
                                    pendingDice = game.gamestate["board"][pos].setdefault("pendingRiftDice", {})
                                    pendingDice[str(counter)] = rollerType
                                    game.update()
                                    continue
                            if dieNum == 2 or dieNum == 3:
                                continue
                            if dieNum == 1 or dieNum == 6:
                                if dieNum != 6 or popRiftProtector:
                                    shipRiftBackfire += 1
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
                                        label, emoji = Combat.getTargetButton(game, pos, ship)
                                        buttonID = (f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}"
                                                    f"_{ship}_{dieNum}_{dieDam}_{counter}")
                                        view.add_item(Button(label=label, emoji=emoji, style=discord.ButtonStyle.red,
                                                             custom_id=buttonID))
                                    await interaction.channel.send(msg, view=view)
                                    hitsToAssign = 1
                                    if "unresolvedHits" in game.gamestate["board"][pos]:
                                        hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                                    game.setUnresolvedHits(hitsToAssign, pos)
                                else:
                                    ship = hittableShips[0]
                                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                                    await Combat.assignHitTo(game, buttonID, interaction, False,
                                                             deferEnd=dieColor == "pink")
                                    deferredEnd = deferredEnd or dieColor == "pink"
                    if shipRiftBackfire > 0:
                        await Combat.applyRiftBackfire(game, colorOrAI, interaction, pos, shipRiftBackfire,
                                                       deferEnd=True)
                        deferredEnd = True

        if deferredEnd:
            await Combat.checkCombatEnd(game, interaction, pos, oldLength)
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
        dieId = buttonID.split("_")[5] if colorDie == "pink" else None
        speed = game.gamestate["board"][pos]["currentSpeed"]
        tile_map = game.gamestate["board"]
        ships = player_helper.adjust_colony_ships(1)
        if ships is False:
            await interaction.channel.send(f"{interaction.user.mention}, you have no colony ships left to reroll with.")
            return
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
            matching_emojis = ([Emoji._app[emojiName]] if emojiName in Emoji._app
                               else [e for e in interaction.guild.emojis if e.name == emojiName])
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
                pendingDice = game.gamestate["board"][pos]["pendingRiftDice"]
                shipType = pendingDice.pop(dieId)
                game.update()
                if all([player is not None,
                                        "Lyra" in player["name"],
                                        player["colony_ships"] > 0,
                                    oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                        viewLyr = View()
                        label = "Reroll Die"
                        buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                    f"_{0}_{dieColor}_{dieId}")
                        riftButtonID = (f"FCID{colorOrAI}_resolveLyraRiftRoll_{pos}_{colorOrAI}"
                                    f"_{str(dieNum)}_{str(speed)}_{str(dieDam)}_{dieId}")
                        viewLyr.add_item(Button(label=label, style=discord.ButtonStyle.green,
                                                custom_id=buttonID))
                        viewLyr.add_item(Button(label="Decline Reroll", style=discord.ButtonStyle.red,
                                                custom_id=riftButtonID))
                        emojiStr = str(dieNum)
                        emojiName = f"dice_{Combat.translateColorToName('pink')}_{dieNum}"
                        matching_emojis = ([Emoji._app[emojiName]] if emojiName in Emoji._app
                                           else [e for e in interaction.guild.emojis if e.name == emojiName])
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
                        pendingDice[dieId] = shipType
                        game.update()
                        continue
                if dieNum == 2 or dieNum == 3:
                    continue
                if dieNum == 1 or dieNum == 6:
                    pendingBackfire = game.gamestate["board"][pos].setdefault("pendingRiftBackfire", {})
                    pendingBackfire[shipType] = pendingBackfire.get(shipType, 0) + 1
                    game.update()
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
                            label, emoji = Combat.getTargetButton(game, pos, ship)
                            buttonID = f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                            view.add_item(Button(label=label, emoji=emoji, style=discord.ButtonStyle.red, custom_id=buttonID))
                        asyncio.create_task(interaction.channel.send(msg, view=view))
                        hitsToAssign = 1
                        if "unresolvedHits" in game.gamestate["board"][pos]:
                            hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"] + 1
                        game.setUnresolvedHits(hitsToAssign, pos)
                else:
                    ship = hittableShips[0]
                    buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_{dieNum}_{dieDam}"
                    await Combat.assignHitTo(game, buttonID, interaction, False, deferEnd=dieColor == "pink")
        if colorDie == "pink" and shipType not in game.gamestate["board"][pos]["pendingRiftDice"].values():
            await Combat.resolvePendingRiftBackfire(game, colorOrAI, interaction, pos, shipType, deferEnd=True)
            if game.gamestate["board"][pos].get("unresolvedHits", 0) == 0:
                await Combat.checkCombatEnd(game, interaction, pos, oldNumPeeps)
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
        attacker = Combat.sideOf(game.gamestate["board"][pos]["attacker"])
        defender = Combat.sideOf(game.gamestate["board"][pos]["defender"])
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
            await Combat.checkForMorphShield(game, pos, channel, ships, list(attacker) + list(defender))
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
                # The AI has no player, so the opposing side rolls for it.
                rollerSide = list(defender) if "ai" in attacker else list(attacker)
                roller = next((color for color in rollerSide if color != "ai"), rollerSide[0])
                playerObj = game.getPlayerObjectFromColor(roller)
                msg = f"{playerObj['player_name']}, please roll the dice for the AI ships with {initiative}."
        if Combat.canResolveStalemate(game, pos):
            for color in attacker:
                if color == "ai":
                    continue
                suffix, emoji = Combat.getCombatantTag(game, pos, color)
                view.add_item(Button(label=f"Resolve Stalemate (Destroy Attacking Ships){suffix}",
                                     style=discord.ButtonStyle.red, emoji=emoji,
                                     custom_id=f"FCID{color}_resolveStalemate_{pos}_{color}"))
            msg += " Neither side has weapons remaining; the attacker must retreat or resolve the stalemate."
            if not any(Combat.getRetreatTiles(game, pos, color) for color in attacker if color != "ai"):
                msg += " There is no sector to retreat to."
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
        continued = await Combat.checkCombatEnd(game, interaction, pos, oldLength)
        if not continued:
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
                    if any(player != color and not game.areAllied(color, player)
                           for player in players):
                        continue
                    validTiles.append(tile)
                else:
                    validTile = True
                    for player in players:
                        if player != color and not game.areAllied(color, player):
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
    def discoveryTileClaimable(game: GamestateHelper, pos: str):
        """A Discovery Tile still on the board that no Ancients guard. Ancients
        guard their tile until destroyed, even against the Descendants of Draco."""
        tile = game.gamestate["board"].get(pos, {})
        return tile.get("disctile", 0) != 0 and "anc" not in Combat.findShipTypesInTile(game, pos)

    @staticmethod
    async def offerDiscoveryTile(game: GamestateHelper, channel, pos: str, color: str):
        player = game.getPlayerObjectFromColor(color)
        view = View()
        view.add_item(Button(label="Explore Discovery Tile", style=discord.ButtonStyle.green,
                             custom_id=f"FCID{color}_exploreDiscoveryTile_{pos}_deleteMsg"))
        await channel.send(f"{player['player_name']}, you may explore the discovery tile.", view=view)

    @staticmethod
    async def settleDiscoveryTiles(game: GamestateHelper, channel):
        """FAQ: at the end of the Combat Phase the player who Controls the sector
        takes a claimable Discovery Tile. With nobody in control, the first player
        with a Ship there takes it (allies in entry order)."""
        for pos, tile in game.gamestate["board"].items():
            if not Combat.discoveryTileClaimable(game, pos):
                continue
            owner = tile.get("owner", 0)
            if owner != 0 and owner != "ai":
                color = owner
            else:
                players = [color for color in Combat.findPlayersInTile(game, pos) if color != "ai"]
                if not players or len(Combat.findSidesInTile(game, pos)) > 1:
                    continue
                entryOrder = game.getEntryOrder(pos)
                players.sort(key=lambda color: entryOrder.index(color) if color in entryOrder else len(entryOrder))
                color = players[0]
            await Combat.offerDiscoveryTile(game, channel, pos, color)

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
        system = int(game.gamestate["board"][pos]["sector"])
        # Nebula Subsectors share a sector number, so number draws after any already queued for it
        countDraw = 1 + sum(q[0] == system for q in game.gamestate.get("queuedDraws", [])
                            + game.gamestate.get("queuedQuestions", []))
        game.removeFromKey("tilesToResolve", int(game.gamestate["board"][pos]["sector"]))
        entry_order = game.getCombatEntryOrder(pos)
        players = sorted(players, key=lambda color: (entry_order.index(color) if color in entry_order
                                                      else len(entry_order), players.index(color)))
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
        survivors = [color for color in Combat.findPlayersInTile(game, pos) if color != "ai"]
        # An Alliance wins as a side. Its members decide who drops the disc in
        # order of entry to the sector, so offer it to the earliest first.
        entryOrder = game.getCombatEntryOrder(pos)
        survivors.sort(key=lambda color: entryOrder.index(color) if color in entryOrder else len(entryOrder))
        winner = next(iter(survivors), None)
        owner = game.gamestate["board"][pos]["owner"]

        # Nebula Sectors take no influence; their Discovery Tiles are offered at upkeep
        nebula = game.gamestate["board"][pos].get("type") == "nebula"
        winner_owns_or_allies = (winner is not None and owner != 0 and owner != "ai"
                                 and game.areAllied(winner, owner))
        if winner is not None and owner != winner and not winner_owns_or_allies and not nebula:
            player = game.getPlayerObjectFromColor(winner)
            playerName = player["player_name"]
            if owner == 0:
                if Combat.discoveryTileClaimable(game, pos):
                    await Combat.offerDiscoveryTile(game, interaction.channel, pos, winner)
                view2 = View()
                for color in survivors:
                    label = "Place Influence"
                    if len(survivors) > 1:
                        label = f"Place Influence ({game.getPlayerObjectFromColor(color)['name']})"
                    view2.add_item(Button(label=label, style=discord.ButtonStyle.blurple,
                                          custom_id=f"FCID{color}_addInfluenceFinish_{pos}"))
                message = f"{playerName}, you may place your influence on the tile."
                if len(survivors) > 1:
                    message = (f"{playerName}, your Alliance may place an influence disc here. "
                               "The buttons are in order of entry to the sector, so the first of you to "
                               "want the disc should take it.")
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
                    if Combat.discoveryTileClaimable(game, pos):
                        await Combat.offerDiscoveryTile(game, interaction.channel, pos, winner)
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
                        await interaction.channel.send("**REMINDER: Do not resolve the discovery tile until bombing "
                                                       "population has been resolved. If Draco still controls the "
                                                       "sector afterwards, they will gain the discovery tile at the "
                                                       "end of the Combat Phase.**")
                    view = View()
                    view.add_item(Button(label="Roll to Destroy Population", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{winner}_rollDice_{pos}_{winner}_1000_deleteMsg"))
                    message = f"{playerName}, you may roll to attempt to kill enemy population."
                    asyncio.create_task(interaction.channel.send(message, view=view))


    @staticmethod
    async def checkCombatEnd(game: GamestateHelper, interaction: discord.Interaction, pos: str, oldLength: int):
        players = Combat.findPlayersInTile(game, pos)
        if len(Combat.findSidesInTile(game, pos)) < 2 or Combat.isDracoAgainstAncients(game, pos):
            await Combat.declareAWinner(game, interaction, pos)
            return True
        elif oldLength != len(players):
            tile = game.gamestate["board"][pos]
            attacker = Combat.sideOf(tile.get("attacker"))
            defender = Combat.sideOf(tile.get("defender"))
            present = set(players)
            if not attacker or not defender or not (set(attacker) & present) or not (set(defender) & present):
                drawing = DrawHelper(game.gamestate)
                image = await asyncio.to_thread(drawing.board_tile_image_file, pos)
                asyncio.create_task(interaction.channel.send("Updated view",
                                                             view=Combat.getCombatButtons(game, pos), file=image))
                await Combat.startCombat(game, interaction.channel, pos)
                return True
            if not (tile.get("unresolvedHits", 0) > 0 or tile.get("pendingRiftDice")
                    or any(tile.get("pendingRiftBackfire", {}).values())):
                # Otherwise the last pending hit prompts the next initiative step.
                await Combat.promptNextSpeed(game, pos, interaction.channel, True)
            return True
        return False

    @staticmethod
    async def assignHitTo(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, button: bool,
                          deferEnd: bool = False):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        ship = buttonID.split("_")[3]
        dieNum = buttonID.split("_")[4]
        dieDam = buttonID.split("_")[5]
        shipType = ship.split("-")[1]
        shipOwner = ship.split("-")[0]
        suffix, _emoji = Combat.getCombatantTag(game, pos, shipOwner)
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
                   f" {Combat.translateShipAbrToName(shipType)}{suffix} with a die that rolled a {str(dieNum)}. ")
        else:
            msg = (f"The AI dealt {dieDam} damage to a {Combat.translateShipAbrToName(shipType)}{suffix}"
                   f" with a die that rolled a {str(dieNum)}. ")
        msg += f"The damaged ship has {shipModel.hull - damage + 1}/{shipModel.hull + 1} hp left. "
        oldLength = len(Combat.findPlayersInTile(game, pos))
        if button:
            # Count this hit before checkCombatEnd looks for hits still pending.
            hitsToAssign = max(game.gamestate["board"][pos].get("unresolvedHits", 0) - 1, 0)
            game.setUnresolvedHits(hitsToAssign, pos)
        if shipModel.hull < damage:
            if colorOrAI not in ship:
                game.destroy_ship(ship, pos, colorOrAI)
            else:
                dummyKiller = "ai"
                attackerSide = Combat.sideOf(game.gamestate["board"][pos].get("attacker"))
                defenderSide = Combat.sideOf(game.gamestate["board"][pos].get("defender"))
                if attackerSide and colorOrAI not in attackerSide:
                    dummyKiller = attackerSide[0]
                if defenderSide and colorOrAI not in defenderSide:
                    dummyKiller = defenderSide[0]
                game.destroy_ship(ship, pos, dummyKiller)
            if colorOrAI != "ai":
                msg += (f"{interaction.user.name} destroyed the"
                        f" {Combat.translateShipAbrToName(shipType)}{suffix}"
                        " due to the damage exceeding the ships hull.")
            else:
                msg += (f"The AI destroyed the {Combat.translateShipAbrToName(shipType)}{suffix}"
                        " due to the damage exceeding the ships hull.")
            await interaction.channel.send(msg)
            if not deferEnd:
                await Combat.checkCombatEnd(game, interaction, pos, oldLength)
        else:
            await interaction.channel.send(msg)
        if button:
            await interaction.message.delete()
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
            asyncio.create_task(interaction.message.delete())
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
