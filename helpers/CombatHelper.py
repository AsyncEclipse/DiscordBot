import asyncio
import json
import random

import discord
from discord.ui import View, Button
from Buttons.Influence import InfluenceButtons
from Buttons.Population import PopulationButtons
from Buttons.Reputation import ReputationButtons
from Buttons.Upgrade import UpgradeButtons
from helpers import FactionData
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import AI_Ship, PlayerShip
from helpers.Turtugan import Carapace
from jproperties import Properties


class Combat:
    PHASE_OPTIONS = {
        "comp": ("+1 to Hit", 1),
        "shield": ("+1 Shield", 1),
        "speed": ("+2 Initiative", 2),
        "planets": ("Neutron Bombs", 2),
        "ignore": ("Ignore Shields", 3),
    }

    @staticmethod
    def exile_orbital_exists(game: GamestateHelper, pos):
        """A faction whose Orbitals count as Ships while they carry a Population Cube."""
        tile = game.gamestate["board"][pos]
        owner = game.getPlayerObjectFromColor(tile.get("owner"))
        return all([owner is not None,
                    tile.get("orbital_pop", [0])[0] == 1,
                    FactionData.has(owner, "orbital_pop_ships")])

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
                              if not FactionData.has(game.getPlayerObjectFromColor(color),
                                                     "may_not_fight_ancients")]
                    if allies:
                        sides[other] = allies
        return sides

    @staticmethod
    def isDracoAgainstAncients(game: GamestateHelper, pos: str):
        """FAQ: with nobody but Ancients left in the sector, Draco does not fight."""
        players = Combat.findPlayersInTile(game, pos)
        return (len(players) == 2 and "anc" in Combat.findShipTypesInTile(game, pos)
                and any(FactionData.has(game.getPlayerObjectFromColor(color), "may_not_fight_ancients")
                        for color in players))

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
            if Combat.exile_orbital_exists(game, pos):
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
            if tile_map[tile].get("type") == "nebula":
                continue
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
    def phase_mode(game: GamestateHelper, color: str, pos: str, ship_type: str):
        """The Phase Module declaration for one blueprint in this combat, if any."""
        modes = game.gamestate["board"].get(pos, {}).get("phaseModes", {})
        return modes.get(color, {}).get(ship_type, {})

    @staticmethod
    def phase_bombing_ship(game: GamestateHelper, color: str, pos: str):
        """The blueprint that pays the 2 Power for bombing: the one with the most power left."""
        player = game.getPlayerObjectFromColor(color)
        types = Combat.phase_ship_types(game, color, pos)
        return max(types, key=lambda ship: PlayerShip(player, ship).energy, default=None)

    @staticmethod
    def phase_bombing_cost(game: GamestateHelper, color: str, pos: str):
        player = game.getPlayerObjectFromColor(color)
        energy = max((PlayerShip(player, ship).energy
                      for ship in Combat.phase_ship_types(game, color, pos)), default=0)
        return max(0, 2 - max(0, energy))

    @staticmethod
    async def phaseBombing(game: GamestateHelper, player, interaction: discord.Interaction, customID: str):
        """Require 2 available blueprint Power for Neutron Bombs without combat."""
        pos = customID.split("_")[1]
        if not FactionData.has(player, "phase_module"):
            return
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        if "neb" not in player_helper.getTechs():
            await interaction.followup.send("Research Neutron Bombs before using them.", ephemeral=True)
            return
        if game.gamestate["board"][pos]["owner"] == 0:
            await interaction.followup.send("That sector no longer has an owner to bomb.", ephemeral=True)
            return
        parts = customID.split("_")
        if (len(parts) != 3 or parts[2] != str(game.gamestate["roundNum"])
                or pos not in [tile for sector, tile in Combat.findTilesInContention(game)]
                or player["color"] not in Combat.findPlayersInTile(game, pos)
                or game.is_population_gone(pos)):
            await interaction.followup.send("This bombing opportunity is no longer current.", ephemeral=True)
            return
        cost = Combat.phase_bombing_cost(game, player["color"], pos)
        if cost > 0:
            await interaction.followup.send("The Phase Module needs 2 Power for Neutron Bombs.",
                                            ephemeral=True)
            return
        bomb_ship = Combat.phase_bombing_ship(game, player["color"], pos)
        await interaction.channel.send(f"{player['player_name']} uses Neutron Bombs from their"
                                       f" {bomb_ship.capitalize()} (2 blueprint Power).")
        await InfluenceButtons.removeInfluenceFinish(
            game, interaction, f"removeInfluenceFinish_{pos}_graveYard", True, player)

    @staticmethod
    def phase_declared_planets(game: GamestateHelper, color: str, pos: str):
        modes = game.gamestate["board"].get(pos, {}).get("phaseModes", {}).get(color, {})
        return any(mode.get("planets") for mode in modes.values())

    @staticmethod
    def clear_phase_module(game: GamestateHelper, pos: str):
        tile = game.gamestate["board"].get(pos, {})
        for key in ("phaseModes", "phaseModuleReady", "phaseModuleColors", "phaseModulePrompted"):
            tile.pop(key, None)
        game.update()

    @staticmethod
    async def startCombat(game: GamestateHelper, channel, pos):
        # a new pairing on the tile is a new combat: last pairing's Techno-Magic parts come off first
        await Combat.revertTechnoMagic(game, channel, pos)
        Carapace.clear(game, pos)
        Combat.clearWolfPack(game, pos)
        game.gamestate["board"][pos].pop("ghostsRetreatPending", None)
        Combat.clear_phase_module(game, pos)
        game.gamestate["board"][pos].pop("technoMagicColors", None)
        game.gamestate["board"][pos].pop("technoMagicReady", None)
        drawing = DrawHelper(game.gamestate)
        sides = Combat.currentPairing(game, pos)
        game.setAttackerAndDefender(sides[1], sides[0], pos)
        tile = game.gamestate["board"][pos]
        tile["firstShotSide"] = Combat.firstShotSideOf(game, tile["attacker"], tile["defender"])
        tile["firstShotPhase"] = "opponent" if tile["firstShotSide"] else None
        tile.pop("rolledSteps", None)
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
        tm_waiting = await Combat.offerTechnoMagic(game, channel, pos)
        await Carapace.offer(game, channel, pos)
        waiting = await Combat.offerPhaseModule(game, channel, pos)
        if not tm_waiting and not waiting:
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
            wraithNeedsDeclaration = (FactionData.has(player, "phase_module")
                                      and "neb" in player_helper.getTechs())
            if any([FactionData.has(p2, "population_destroyed_in_combat"),
                    game.is_population_gone(pos),
                    ("neb" in player_helper.getTechs() and "nea" not in player_helper2.getTechs()
                     and not wraithNeedsDeclaration)]):
                view = View()
                view.add_item(Button(label="Destroy All Population", style=discord.ButtonStyle.green,
                                     custom_id=f"FCID{winner}_removeInfluenceFinish_{pos}_graveYard"))
                message = f"{playerName}, you may destroy all enemy influence and population automatically."
                if wraithNeedsDeclaration:
                    message += " Neutron Bombs (2 blueprint Power) apply here."
                asyncio.create_task(thread2.send(message, view=view))
                message = (f"{playerName}, you may place your influence on the tile"
                           " after destroying the enemy population.")
                await InfluenceButtons.offerInfluenceDisc(game, thread2, pos, [winner], message)
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
                if wraithNeedsDeclaration:
                    if Combat.phase_bombing_cost(game, winner, pos) == 0:
                        bomb_ship = Combat.phase_bombing_ship(game, winner, pos)
                        view.add_item(Button(label="Use Phase Module: Neutron Bombs (2 Power)",
                                             style=discord.ButtonStyle.blurple,
                                             custom_id=f"FCID{winner}_phaseBombing_{pos}_{game.gamestate['roundNum']}"))
                        message += (f" You may use 2 blueprint Power from your"
                                    f" {bomb_ship.capitalize()} for Neutron Bombs on the population.")
                    else:
                        message += (" The Phase Module needs 2 Power for Neutron Bombs,"
                                    " so only the roll is available here.")
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
            message = (f"{playerName}, you may place your influence on the tile after destroying the enemy population.")
            await InfluenceButtons.offerInfluenceDisc(game, thread3, pos, playerSide, message)
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
                    ships.append((ship.speed + Combat.phase_mode(
                        game, colorOrAI, pos, Combat.translateShipAbrToName(unitType)).get("speed", 0),
                        unitType))
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
    def firstShotSideOf(game: GamestateHelper, attacker, defender):
        """The Kurita colours that shoot second, or [] when both or neither side has first shot."""
        attacker = Combat.sideOf(attacker)
        defender = Combat.sideOf(defender)

        def first_shot_colors(side):
            return [color for color in side if color != "ai"
                    and FactionData.has(game.getPlayerObjectFromColor(color), "first_shot")]

        attacker_first = first_shot_colors(attacker)
        defender_first = first_shot_colors(defender)
        if bool(attacker_first) == bool(defender_first):
            return []
        return attacker_first or defender_first

    @staticmethod
    def firstShotSide(game: GamestateHelper, pos):
        """The delayed side of this pairing, derived from the pairing until startCombat records it."""
        tile = game.gamestate["board"][pos]
        if "firstShotPhase" in tile:
            return list(tile.get("firstShotSide") or []) if tile["firstShotPhase"] else []
        return Combat.firstShotSideOf(game, tile.get("attacker"), tile.get("defender"))

    @staticmethod
    def nextSpeedPair(sortedSpeeds, currentSpeed, currentRoller):
        """The pair after (currentSpeed, currentRoller) in a descending-speed list."""
        found = False
        for speed, owner in sortedSpeeds:
            if any([found, currentSpeed is None, currentRoller is None,
                    currentSpeed is not None and speed < currentSpeed]):
                return speed, owner
            if speed == currentSpeed and currentRoller == owner:
                found = True
        return None

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
                    # a weaponless Harvester cannot shoot; it can still be targeted
                    if (FactionData.has(game.gamestate["players"][player], "harvester")
                            and unitType == "sb" and not ship.dice and not ship.missile):
                        continue
                    speed = ship.speed + Combat.phase_mode(
                        game, owner, pos, Combat.translateShipAbrToName(unitType)).get("speed", 0)
                    if (speed, owner) not in ships:
                        ships.append((speed, owner))
                    if len(ship.missile) > 0:
                        if (speed+99, owner) not in ships:
                            ships.append((speed+99, owner))
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
                                     dieVal: int, computerVal: int, pos: str, speed: int,
                                     ignore_shields: bool = False):
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
                if opponent != "ai":
                    shieldVal += Combat.phase_mode(
                        game, opponent, pos, Combat.translateShipAbrToName(ship[1])).get("shield", 0)
                if ignore_shields:
                    shieldVal = 0
                if dieVal == 6 or dieVal + computerVal - shieldVal > 5:
                    ship_type = ship[1]
                    if "-" in ship_type:
                        temp = ship_type.split("-")
                        ship_type = temp[1]
                    hittableShips.append(opponent + "-" + ship_type.replace("adv", ""))
        return hittableShips

    @staticmethod
    async def sendCombatReports(channel, reports):
        text = "\n".join(reports)
        while text:
            split_at = text.rfind("\n", 0, 2001) if len(text) > 2000 else len(text)
            if split_at <= 0:
                split_at = 2000
            await channel.send(text[:split_at])
            text = text[split_at:].lstrip("\n")
        reports.clear()

    @staticmethod
    async def offerHitPrompt(game: GamestateHelper, interaction: discord.Interaction, pos: str,
                             colorOrAI: str, hittableShips, dieNum: int, dieDam: int,
                             counter=None, deferEnd: bool = False, reports=None):
        """Offer one die's targets, or assign the hit when there is only one."""
        if not hittableShips:
            return
        if len(hittableShips) > 1:
            if reports is not None:
                await Combat.sendCombatReports(interaction.channel, reports)
            msg = (f"{interaction.user.mention}, choose what ship to hit with the die that rolled a {dieNum}."
                   f" You will deal {str(dieDam).rstrip('!')} damage. The bot has calculated that you can hit"
                   f" these ships.")
            view = View()
            for ship in hittableShips:
                label, emoji = Combat.getTargetButton(game, pos, ship)
                suffix = f"_{counter}" if counter is not None else ""
                if deferEnd:
                    suffix += "_defer"
                buttonID = (f"FCID{colorOrAI}_assignHitTo_{pos}_{colorOrAI}"
                            f"_{ship}_{dieNum}_{dieDam}{suffix}")
                view.add_item(Button(label=label, emoji=emoji, style=discord.ButtonStyle.red,
                                     custom_id=buttonID))
            await interaction.channel.send(msg, view=view)
            game.setUnresolvedHits(game.gamestate["board"][pos].get("unresolvedHits", 0) + 1, pos)
        else:
            buttonID = f"assignHitTo_{pos}_{colorOrAI}_{hittableShips[0]}_{dieNum}_{dieDam}"
            if deferEnd:
                buttonID += "_defer"
            await Combat.assignHitTo(game, buttonID, interaction, False, deferEnd=deferEnd, reports=reports)

    @staticmethod
    def canResolveStalemate(game: GamestateHelper, pos: str):
        tile = game.gamestate["board"][pos]
        if tile.get("currentSpeed") is None or int(tile["currentSpeed"]) >= 90:
            return False
        if (tile.get("unresolvedHits", 0) > 0
                or tile.get("pendingRiftDice")
                or tile.get("carapacePendingMissiles")
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
            delayedSide = Combat.firstShotSide(game, pos)
            if delayedSide:
                sortedSpeeds = ([pair for pair in sortedSpeeds if pair[1] not in delayedSide]
                                + [pair for pair in sortedSpeeds if pair[1] in delayedSide])
            for speed, owner in sortedSpeeds:
                # Each ship rolls for its own colour, even when its side is an Alliance.
                checker = "" if owner == "ai" else f"FCID{owner}_"
                suffix, emoji = Combat.getCombatantTag(game, pos, owner)
                spine_modes = False
                if owner not in ("ai", "") and speed < 90:
                    playerObj = game.getPlayerObjectFromColor(owner)
                    spine_modes = FactionData.has(playerObj, "spine_cannons") and any(
                        speed2 == speed
                        and len(PlayerHelper.get_spine_cannon_slots(playerObj, shipType)) > 1
                        for speed2, shipType, _count in Combat.getCombatantShipsBySpeed(
                            game, owner, ships, pos))
                side = "Defender" if owner in defender else "Attacker"
                style = discord.ButtonStyle.green if owner in defender else discord.ButtonStyle.red
                if speed < 90:
                    label = f"({side}) Roll Initative {speed} Ships{suffix}"
                    roll_id = f"{checker}rollDice_{pos}_{owner}_{str(speed)}_{side.lower()}"
                else:
                    label = f"({side}) Roll Initative {speed-99} Missiles{suffix}"
                    roll_id = f"{checker}rollDice_{pos}_{owner}_{str(speed)}_{side.lower()}"
                if spine_modes:
                    view.add_item(Button(label=label + " (+X to Hit)", style=style, emoji=emoji,
                                         custom_id=roll_id + "_spinehit"))
                    view.add_item(Button(label=label + " (+X Damage)", style=style, emoji=emoji,
                                         custom_id=roll_id + "_spinedmg"))
                else:
                    view.add_item(Button(label=label, style=style, emoji=emoji, custom_id=roll_id))
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
            needed = shipModel.hull + 1 - game.gamestate["board"][pos].get("damage_tracker", {}).get(ship, 0)
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
    def getAIHitAllocation(game: GamestateHelper, colorOrAI, pos, speed, dice, computer):
        """Choose targets for a whole AI salvo before any hits are applied.

        shortcut: exhaustive allocation search grows exponentially; optimize
        if AI salvo sizes become large.
        """
        ships = game.gamestate["board"][pos]["player_ships"][:]
        targets_by_die = [
            Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, ships, die[0], computer, pos, speed)
            for die in dice
        ]
        models = {}
        initial_damage = {}
        for target in {target for options in targets_by_die for target in options}:
            owner, ship_type = target.split("-", 1)
            if owner == "ai":
                advanced = game.gamestate["advanced_ai"]
                worldsafar = game.gamestate["wa_ai"]
                if ship_type + "_type" in game.gamestate:
                    advanced = "adv" in game.gamestate[ship_type + "_type"]
                    worldsafar = "wa" in game.gamestate[ship_type + "_type"]
                model = AI_Ship(ship_type, advanced, worldsafar)
            else:
                player = game.get_player_from_color(owner)
                model = PlayerShip(game.gamestate["players"][player], ship_type)
            models[target] = model
            initial_damage[target] = game.add_damage(target, pos, 0)
        targets = sorted(models, key=lambda target: (models[target].cost, target), reverse=True)

        best_score = None
        best_allocation = [None] * len(dice)

        def search(die_index, allocation, damage, destroyed):
            nonlocal best_score, best_allocation
            if die_index == len(dice):
                candidate_score = (tuple(destroyed[target] for target in targets),
                                   tuple(damage[target] for target in targets))
                if best_score is None or candidate_score > best_score:
                    best_score = candidate_score
                    best_allocation = allocation[:]
                return
            options = list(dict.fromkeys(
                target for target in targets_by_die[die_index]
                if destroyed[target] < ships.count(target))) or [None]
            for target in options:
                next_damage = damage.copy()
                next_destroyed = destroyed.copy()
                if target is not None:
                    next_damage[target] += dice[die_index][1]
                    if next_damage[target] > models[target].hull:
                        next_destroyed[target] += 1
                        next_damage[target] = 0
                allocation.append(target)
                search(die_index + 1, allocation, next_damage, next_destroyed)
                allocation.pop()

        search(0, [], initial_damage, dict.fromkeys(targets, 0))
        return best_allocation

    @staticmethod
    async def applyRiftBackfire(game: GamestateHelper, colorOrAI, interaction: discord.Interaction, pos, totalDamage,
                                deferEnd: bool = False):
        reports = []
        for ship, damage in Combat.getRiftBackfireAllocation(game, colorOrAI,
                                                             game.gamestate["board"][pos]["player_ships"][:],
                                                             pos, totalDamage):
            buttonID = f"assignHitTo_{pos}_{colorOrAI}_{ship}_1_{damage}"
            await Combat.assignHitTo(game, buttonID, interaction, False, deferEnd=deferEnd, reports=reports)
        await Combat.sendCombatReports(interaction.channel, reports)

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
        reports = []
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
                        if len(matching_emojis) > 0:
                            msg2 += str(matching_emojis[0]) + " "
                        else:
                            msg += str(num) + " "
                        dieNums.append([random_number, Combat.translateColorToDamage(die, random_number), die])
                if shipModel.computer > 0:
                    msg += f"\nThis ship type has a +{shipModel.computer} computer."
                reports.append(msg + msg2)
                oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                allocation = Combat.getAIHitAllocation(game, colorOrAI, pos, speed, dieNums,
                                                       shipModel.computer)
                for die, target in zip(dieNums, allocation):
                    dieNum = die[0]
                    dieDam = die[1]
                    hittableShips = Combat.getOpponentUnitsThatCanBeHit(
                        game, colorOrAI, game.gamestate["board"][pos]["player_ships"][:],
                        dieNum, shipModel.computer, pos, speed)
                    if (dieNum + shipModel.computer > 5 and not hittableShips
                            and oldNumPeeps == len(Combat.findPlayersInTile(game, pos))):
                        message = (f"The computer bonus for a die that rolled a {dieNum}"
                                   " was cancelled by the shields on each of the opponents ships.")
                        reports.append(message)
                    if target is not None:
                        update = True
                        buttonID = f"assignHitTo_{pos}_{colorOrAI}_{target}_{dieNum}_{dieDam}"
                        await Combat.assignHitTo(game, buttonID, interaction, False, reports=reports)
        await Combat.sendCombatReports(interaction.channel, reports)
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
        spine_mode = ("spinehit" if "spinehit" in buttonID
                      else "spinedmg" if "spinedmg" in buttonID else None)
        tile = game.gamestate["board"][pos]
        pairing = Combat.sideOf(tile.get("attacker")) + Combat.sideOf(tile.get("defender"))
        # Initiative 1000 is population bombing, which has no pairing.
        if speed != 1000 and pairing and colorOrAI not in pairing:
            await interaction.channel.send("The combat pairing changed. Press Refresh Image and roll again.")
            return
        if Combat.technoMagicPending(game, pos):
            await interaction.channel.send("Finish your Techno-Magic upgrades before rolling initiative.")
            return
        if speed != 1000 and len(Combat.currentPairing(game, pos)) < 2:
            await interaction.channel.send("The combat in this sector has already ended.")
            return
        if tile.get("phaseModuleColors") and not tile.get("phaseModulePrompted"):
            await interaction.channel.send("Declare Phase Module options before rolling initiative.")
            return
        if tile.get("ghostsRetreatPending"):
            await interaction.channel.send("A retreat is being resolved; choose its destination first.")
            return
        if (speed != 1000 and pairing
                and (tile.get("phaseModuleColors") or tile.get("ghostsRetreatPending"))):
            effective = {ship_speed for ship_speed, owner in Combat.getBothCombatantShipsBySpeed(
                game, Combat.sideOf(tile.get("defender")), Combat.sideOf(tile.get("attacker")),
                tile.get("player_ships", []), pos) if owner == colorOrAI}
            if speed not in effective:
                await interaction.channel.send("That initiative step is no longer valid. Use the current prompt.")
                return
        if speed != 1000:
            Carapace.close_controls(game, pos)
            step = [speed, colorOrAI]
            if step in tile.get("rolledSteps", []):
                await interaction.channel.send(
                    "That initiative step has already rolled this engagement round. Use the current prompt.")
                return
            tile.setdefault("rolledSteps", []).append(step)
            game.update()
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
        reports = []
        popRiftProtector = True
        deferredEnd = False
        is_wolf = speed != 1000 and FactionData.has(game.getPlayerObjectFromColor(colorOrAI), "wolf_pack")
        wolf_sixes = {}
        wolf_misses = []
        wolf_miss_ids = set()
        roll_id = 0
        counter = 0
        for ship in ships:
            if ship[0] == speed or speed == (ship[0]+99) or speed == 1000:
                name = game.getPlayerObjectFromColor(colorOrAI)["player_name"]
                player = game.get_player_from_color(colorOrAI)
                rollerType = ship[1]
                shipModel = PlayerShip(game.gamestate["players"][player], rollerType)
                phase = Combat.phase_mode(game, colorOrAI, pos, Combat.translateShipAbrToName(rollerType))
                computerVal = shipModel.computer + phase.get("comp", 0)
                ignoreShields = bool(phase.get("ignore"))
                dice = shipModel.dice
                sources = shipModel.dice_sources
                augment = shipModel.spine_augment()
                spine_bonus = (Combat.translateColorToDamage(augment[2], 6)
                               if augment and spine_mode else 0)
                cannon_index = augment[0] if augment else None
                missiles = ""
                nonMissiles = " on initiative " + str(speed)
                incoming_shield = False
                if speed > 90 and speed < 1000:
                    attacker_side = Combat.sideOf(tile.get("attacker"))
                    defender_side = Combat.sideOf(tile.get("defender"))
                    enemy_side = defender_side if colorOrAI in attacker_side else attacker_side
                    incoming_shield = any(
                        Carapace.engaged(game, pos, enemy, ship_class)
                        for enemy in enemy_side
                        for ship_class in Carapace.classes_in_battle(game, pos, enemy))
                if speed > 90 and speed < 1000:
                    dice = shipModel.missile
                    sources = [None] * len(dice)
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
                shielded = Carapace.engaged(game, pos, colorOrAI, shipModel.ship_type)
                for x in range(ship[2]):
                    for die_index, die in enumerate(dice):
                        source = sources[die_index] if die_index < len(sources) else None
                        damage_bonus = (spine_bonus if spine_mode == "spinedmg"
                                        and source == cannon_index else 0)
                        split = False
                        roll_id += 1
                        random_number = random.randint(1, 6)
                        if random_number == 6:
                            wolf_sixes.setdefault(rollerType, []).append(die)
                        num = str(random_number).replace("1", "Miss").replace("6", ":boom:")
                        emojiName = f"dice_{Combat.translateColorToName(die)}_{random_number}"
                        matching_emojis = ([Emoji._app[emojiName]] if emojiName in Emoji._app
                                           else [e for e in interaction.guild.emojis if e.name == emojiName])
                        if len(matching_emojis) > 0:
                            msg2 += str(matching_emojis[0]) + " "
                        else:
                            msg += str(num) + " "
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
                        base_damage = Combat.translateColorToDamage(die, random_number)
                        total_damage = base_damage + damage_bonus
                        if shielded:
                            # Shields dock each rolled die by one before it can be split.
                            total_damage = Carapace.weapon_damage(game, pos, colorOrAI,
                                                                  shipModel.ship_type, total_damage)
                        if not split:
                            dieNums.append([random_number, total_damage, die, source, roll_id, total_damage])
                        else:
                            for i in range(total_damage):
                                dieNums.append([random_number, 1, die, source, roll_id, total_damage])
                if computerVal > 0:
                    msg += (f"\nThis ship type has a +{computerVal} computer"
                            + Combat.computer_description(shipModel, computerVal - shipModel.computer) + ".")
                if spine_bonus:
                    gun = Combat.part_name(shipModel.ship_parts[cannon_index])
                    if spine_mode == "spinehit":
                        msg += f"\nSpine Cannon augment: the {gun} adds +{spine_bonus} to Hit for its dice."
                    else:
                        msg += (f"\nSpine Cannon augment: the {gun} adds +{spine_bonus} Damage"
                                " to its dice (die damage + augment).")

                if len(dice) > 0:
                    # await interaction.channel.send(msg,file=drawing.append_images(dieFiles))
                    await interaction.channel.send(msg + msg2)
                    oldNumPeeps = len(Combat.findPlayersInTile(game, pos))
                    # A rift die defers the salvo's combat-end check, so every hit in
                    # the same salvo must defer too or the kill is declared twice.
                    salvo_defer = is_wolf or any(die[2] == "pink" for die in dieNums)
                    for die in dieNums:
                        counter = counter + 1
                        tile_map = game.gamestate["board"]
                        player_ships = tile_map[pos]["player_ships"][:]
                        dieNum = die[0]
                        dieDam = die[1]
                        dieColor = die[2]
                        die_source = die[3]
                        die_roll_id = die[4]
                        die_wolf_damage = die[5]
                        hit_bonus = (spine_bonus if spine_mode == "spinehit"
                                     and die_source == cannon_index else 0)
                        die_damage_bonus = (spine_bonus if spine_mode == "spinedmg"
                                            and die_source == cannon_index else 0)
                        computer_val = computerVal + hit_bonus
                        hittableShips = []
                        # A die that cannot hit even before the shield penalty has no choice to make.
                        shield_choice = (incoming_shield and dieColor != "pink"
                                         and Combat.getOpponentUnitsThatCanBeHit(
                                             game, colorOrAI, player_ships, dieNum, computerVal, pos, speed))
                        if shield_choice:
                            update = True
                            await Carapace.prompt_missile(game, interaction, pos, colorOrAI,
                                                          shipModel.ship_type, computerVal,
                                                          speed, dieNum, dieDam, counter)
                            continue
                        if dieColor != "pink":
                            hittableShips = Combat.getOpponentUnitsThatCanBeHit(game, colorOrAI, player_ships,
                                                                                dieNum, computer_val, pos, speed,
                                                                                ignoreShields)
                            if all([dieNum + computer_val > 5,
                                    len(hittableShips) == 0,
                                    oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                                message = (f"The computer bonus for a die that rolled a {dieNum} was"
                                           " cancelled by the shields on each of the opponents ships.")
                                asyncio.create_task( interaction.channel.send(message))
                            if len(hittableShips) == 0 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                                if (die_roll_id not in wolf_miss_ids and dieNum < 6
                                        and oldNumPeeps == len(Combat.findPlayersInTile(game, pos))):
                                    wolf_miss_ids.add(die_roll_id)
                                    wolf_misses.append([rollerType, dieNum, die_wolf_damage, dieColor,
                                                        computer_val, die_source, hit_bonus, die_damage_bonus])
                                if all([player is not None,
                                        "Lyra" in game.gamestate["players"][player]["name"],
                                        game.gamestate["players"][player]["colony_ships"] > 0,
                                        oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                                    viewLyr = View()
                                    label = "Reroll Die"
                                    buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                                f"_{computerVal}_{dieColor}_{counter}_{rollerType}")
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
                                                f"_{computerVal}_{dieColor}_{counter}_{rollerType}")
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
                                                                                    6, computerVal, pos, speed,
                                                                                    ignoreShields)
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
                                await Combat.offerHitPrompt(game, interaction, pos, colorOrAI, hittableShips,
                                                            dieNum, dieDam, counter=counter,
                                                            deferEnd=salvo_defer, reports=reports)
                                deferredEnd = deferredEnd or salvo_defer
                    await Combat.sendCombatReports(interaction.channel, reports)
                    if shipRiftBackfire > 0:
                        await Combat.applyRiftBackfire(game, colorOrAI, interaction, pos, shipRiftBackfire,
                                                       deferEnd=True)
                        deferredEnd = True

        if deferredEnd and not is_wolf:
            await Combat.checkCombatEnd(game, interaction, pos, oldLength)
        hitsToAssign = 0
        if speed != 1000 and not Carapace.has_pending_missiles(game, pos):
            if "unresolvedHits" in game.gamestate["board"][pos]:
                hitsToAssign = game.gamestate["board"][pos]["unresolvedHits"]
            if hitsToAssign == 0:
                playerObj = game.getPlayerObjectFromColor(colorOrAI)
                bank = game.gamestate["board"][pos].get("wolfPackRerolls", {}).get(colorOrAI, 0)
                if FactionData.has(playerObj, "wolf_pack") and (wolf_sixes or (bank > 0 and wolf_misses)):
                    state = {"color": colorOrAI, "speed": speed, "sixes": wolf_sixes,
                             "misses": wolf_misses, "available": bank, "oldLength": oldLength}
                    await Combat.offerWolfPack(game, pos, interaction, state)
                    return
                if is_wolf and await Combat.checkCombatEnd(game, interaction, pos, oldLength):
                    return
                if oldLength == len(Combat.findPlayersInTile(game, pos)):
                    await Combat.promptNextSpeed(game, pos, interaction.channel, update)
            elif hitsToAssign > 0:
                playerObj = game.getPlayerObjectFromColor(colorOrAI)
                bank = game.gamestate["board"][pos].get("wolfPackRerolls", {}).get(colorOrAI, 0)
                if FactionData.has(playerObj, "wolf_pack") and (wolf_sixes or (bank > 0 and wolf_misses)):
                    game.gamestate["board"][pos]["pendingWolfPack"] = {
                        "color": colorOrAI, "speed": speed, "sixes": wolf_sixes,
                        "misses": wolf_misses, "available": bank, "oldLength": oldLength}
                    game.update()

    @staticmethod
    def clearWolfPack(game: GamestateHelper, pos: str):
        tile = game.gamestate["board"][pos]
        if any(key in tile for key in ("wolfPack", "pendingWolfPack", "wolfPackRerolls")):
            tile.pop("wolfPack", None)
            tile.pop("pendingWolfPack", None)
            tile.pop("wolfPackRerolls", None)
            game.update()

    @staticmethod
    async def offerWolfPack(game: GamestateHelper, pos: str, interaction: discord.Interaction, state: dict):
        tile = game.gamestate["board"][pos]
        tile["wolfPack"] = state
        game.update()
        await Combat.wolfPackPrompt(game, pos, interaction)

    @staticmethod
    async def offerPendingWolfPack(game: GamestateHelper, pos: str, interaction: discord.Interaction):
        tile = game.gamestate["board"][pos]
        state = tile.pop("pendingWolfPack", None)
        if state is None:
            return False
        game.update()
        await Combat.offerWolfPack(game, pos, interaction, state)
        return True

    @staticmethod
    async def wolfPackPrompt(game: GamestateHelper, pos: str, interaction: discord.Interaction):
        tile = game.gamestate["board"][pos]
        state = tile.get("wolfPack")
        if state is None:
            return
        color = state["color"]
        player = game.getPlayerObjectFromColor(color)
        sixes = sum(len(colors) for colors in state["sixes"].values())
        if sixes > 0:
            faces = " ".join(Combat.die_face(interaction, dieColor, 6)
                             for colors in state["sixes"].values() for dieColor in colors)
            view = View()
            for index, miss in enumerate(state["misses"]):
                if miss[3] != "pink" and state["sixes"].get(miss[0]):
                    view.add_item(Button(
                        label=f"Convert a {Combat.translateShipAbrToName(miss[0])} miss ({miss[2]} damage)",
                        style=discord.ButtonStyle.green,
                        custom_id=f"FCID{color}_wolfPackConvert_{pos}_{index}"))
            view.add_item(Button(label="Save a Reroll", style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{color}_wolfPackSave_{pos}"))
            view.add_item(Button(label="Done", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{color}_wolfPackDone_{pos}"))
            await interaction.channel.send(
                f"{player['player_name']}, Wolf Pack: {sixes} six{'es' if sixes != 1 else ''}"
                f" ({faces}). "
                "Convert a miss from the same attack pool into a guaranteed hit (it counts as a 6),"
                " or save a reroll for a later ship.",
                view=view)
            return
        if state["available"] > 0:
            rerollable = [index for index, miss in enumerate(state["misses"]) if miss[3] != "pink"]
            if rerollable:
                view = View()
                for index in rerollable:
                    miss = state["misses"][index]
                    view.add_item(Button(
                        label=f"Reroll a {Combat.translateShipAbrToName(miss[0])} miss",
                        style=discord.ButtonStyle.green,
                        custom_id=f"FCID{color}_wolfPackReroll_{pos}_{index}"))
                view.add_item(Button(label="Decline", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{color}_wolfPackDecline_{pos}"))
                await interaction.channel.send(
                    f"{player['player_name']}, Wolf Pack: you have {state['available']} saved reroll"
                    f"{'s' if state['available'] != 1 else ''}. Reroll a miss from this attack?", view=view)
                return
        await Combat.finishWolfPack(game, pos, interaction)

    @staticmethod
    async def finishWolfPack(game: GamestateHelper, pos: str, interaction: discord.Interaction):
        tile = game.gamestate["board"][pos]
        state = tile.pop("wolfPack", None)
        tile.pop("pendingWolfPack", None)
        game.update()
        color = state["color"] if state else None
        if state is not None and await Combat.checkCombatEnd(
                game, interaction, pos, state["oldLength"]):
            return
        if color is not None and color in Combat.findPlayersInTile(game, pos):
            await Combat.promptNextSpeed(game, pos, interaction.channel, True)

    @staticmethod
    async def wolfPackChoice(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        parts = buttonID.split("_")
        kind, pos = parts[0], parts[1]
        tile = game.gamestate["board"][pos]
        state = tile.get("wolfPack")
        if state is None:
            return
        if interaction.message is not None:
            await interaction.message.delete()
        color = state["color"]
        player = game.getPlayerObjectFromColor(color)

        def save():
            tile["wolfPack"] = state
            game.update()

        async def targets_for(die_num, computer, damage, die_color, die_source, hit_bonus, damage_bonus):
            ships = game.gamestate["board"][pos]["player_ships"][:]
            targets = Combat.getOpponentUnitsThatCanBeHit(
                game, color, ships, die_num, computer, pos, state["speed"])
            state["pendingHit"] = {"dieNum": die_num, "dieDam": damage, "dieColor": die_color,
                                   "targets": targets, "source": die_source,
                                   "hitBonus": hit_bonus, "damageBonus": damage_bonus}
            if not targets:
                state.pop("pendingHit", None)
                save()
                await Combat.wolfPackPrompt(game, pos, interaction)
            elif len(targets) == 1:
                await Combat.wolfPackHit(game, pos, interaction, color, targets[0],
                                         die_num, damage)
                if tile.get("wolfPack") is not state:
                    return
                save()
                await Combat.wolfPackPrompt(game, pos, interaction)
            else:
                save()
                view = View()
                for index, ship in enumerate(targets):
                    label, emoji = Combat.getTargetButton(game, pos, ship)
                    view.add_item(Button(label=label, emoji=emoji, style=discord.ButtonStyle.red,
                                         custom_id=f"FCID{color}_wolfPackTarget_{pos}_{index}"))
                await interaction.channel.send(
                    f"{player['player_name']}, choose the ship your Wolf Pack hit damages.", view=view)

        if kind == "wolfPackConvert":
            index = int(parts[2])
            miss = state["misses"][index]
            pool = miss[0]
            if not state["sixes"].get(pool):
                return
            state["sixes"][pool].pop()
            state["misses"].pop(index)
            save()
            await interaction.channel.send(
                f"{player['player_name']} used Wolf Pack: the"
                f" {Combat.translateShipAbrToName(pool)} miss counts as a"
                f" {Combat.die_face(interaction, miss[3], 6)}, so it hits.")
            await targets_for(6, 0, miss[2], miss[3], miss[5], miss[6], miss[7])
        elif kind == "wolfPackSave":
            pool = next(pool for pool, colors in state["sixes"].items() if colors)
            state["sixes"][pool].pop()
            banks = tile.setdefault("wolfPackRerolls", {})
            banks[color] = banks.get(color, 0) + 1
            save()
            await interaction.channel.send(
                f"{player['player_name']} used Wolf Pack: saved a reroll for a ship firing later"
                f" this round ({banks[color]} saved).")
            await Combat.wolfPackPrompt(game, pos, interaction)
        elif kind == "wolfPackDone":
            state["sixes"] = {pool: [] for pool in state["sixes"]}
            save()
            await Combat.wolfPackPrompt(game, pos, interaction)
        elif kind == "wolfPackReroll":
            if state["available"] <= 0:
                return
            index = int(parts[2])
            miss = state["misses"].pop(index)
            state["available"] -= 1
            banks = tile.setdefault("wolfPackRerolls", {})
            banks[color] = max(0, banks.get(color, 0) - 1)
            roll = random.randint(1, 6)
            if roll == 6:
                state["sixes"].setdefault(miss[0], []).append(miss[3])
            damage = Combat.translateColorToDamage(miss[3], roll) + miss[7]
            save()
            await interaction.channel.send(
                f"{player['player_name']} used Wolf Pack to reroll the"
                f" {Combat.translateShipAbrToName(miss[0])} miss:"
                f" {Combat.die_face(interaction, miss[3], roll)}.")
            await targets_for(roll, miss[4], damage, miss[3], miss[5], miss[6], miss[7])
        elif kind == "wolfPackTarget":
            pending = state.get("pendingHit")
            if pending is None:
                return
            targets = pending["targets"]
            index = int(parts[2])
            if index >= len(targets):
                return
            state.pop("pendingHit", None)
            await Combat.wolfPackHit(game, pos, interaction, color, targets[index],
                                     pending["dieNum"], pending["dieDam"])
            if tile.get("wolfPack") is not state:
                return
            save()
            await Combat.wolfPackPrompt(game, pos, interaction)
        elif kind == "wolfPackDecline":
            await Combat.finishWolfPack(game, pos, interaction)

    @staticmethod
    async def wolfPackHit(game: GamestateHelper, pos: str, interaction: discord.Interaction,
                          color: str, ship: str, die_num: int, damage: int):
        await Combat.assignHitTo(game, f"assignHitTo_{pos}_{color}_{ship}_{die_num}_{damage}",
                                 interaction, False, deferEnd=True)

    @staticmethod
    async def rerollDie(game: GamestateHelper, buttonID: str, interaction: discord.Interaction,
                        player, player_helper: PlayerHelper):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        colorDie = buttonID.split("_")[4]
        computerVal = int(buttonID.split("_")[3])
        dieId = buttonID.split("_")[5] if colorDie == "pink" else None
        parts = buttonID.split("_")
        rollerType = parts[6] if len(parts) > 6 else None
        shipType = Combat.translateShipAbrToName(rollerType) if rollerType else None
        ignoreShields = bool(shipType and Combat.phase_mode(game, colorOrAI, pos, shipType).get("ignore"))
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
            if len(matching_emojis) > 0:
                msg2 += str(matching_emojis[0]) + " "
            else:
                msg += str(num) + " "
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
                                                                    dieNum, computerVal, pos, 3, ignoreShields)
                if dieNum + computerVal > 5 and len(hittableShips) == 0:
                    message = (f"The computer bonus for a die that rolled a {dieNum}"
                               " was cancelled by the shields on each of the opponents ships.")
                    await interaction.channel.send(message)
                if len(hittableShips) == 0 or oldNumPeeps > len(Combat.findPlayersInTile(game, pos)):
                    if all([FactionData.has(player, "reroll_dice_with_colony_ships"),
                            player["colony_ships"] > 0,
                            oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                        viewLyr = View()
                        label = "Reroll Die"
                        rerollSuffix = f"_{rollerType}" if rollerType else ""
                        buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                    f"_{computerVal}_{dieColor}{rerollSuffix}")
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
                                        FactionData.has(player, "reroll_dice_with_colony_ships"),
                                        player["colony_ships"] > 0,
                                    oldNumPeeps == len(Combat.findPlayersInTile(game, pos))]):
                        viewLyr = View()
                        label = "Reroll Die"
                        rerollSuffix = f"_{rollerType}" if rollerType else ""
                        buttonID = (f"FCID{colorOrAI}_rerollDie_{pos}_{colorOrAI}"
                                    f"_{0}_{dieColor}_{dieId}{rerollSuffix}")
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
                                                                        6, computerVal, pos, 3, ignoreShields)
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
        if (cube.replace("adv", "") in ("money", "science", "material", "orbital", "disc")
                and PlayerHelper.capture_wraith_soul(player, game.gamestate["board"][pos])):
            game.update_player(PlayerHelper(game.get_player_from_color(player["color"]), player))
            await interaction.channel.send(
                PlayerHelper.wraith_soul_message(player, game.get_tile_label(pos)))
        await interaction.message.delete()
        if len(PopulationButtons.findFullPopulation(game, pos)) == 0:
            game.remove_control(owner, pos)
            message = (f"{player['player_name']}, you may place your influence"
                       " on the tile now that you have destroyed all the enemy population.")
            await InfluenceButtons.offerInfluenceDisc(game, interaction.channel, pos, [player['color']], message)
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
    async def refreshCombatPrompt(game: GamestateHelper, pos: str, channel):
        tile = game.gamestate["board"][pos]
        if len(Combat.currentPairing(game, pos)) != 2 or Combat.isDracoAgainstAncients(game, pos):
            await channel.send("There is no active combat at that position.")
            return
        if Combat.technoMagicPending(game, pos):
            await channel.send("Finish your Techno-Magic upgrades before rolling initiative.")
            return
        if (tile.get("unresolvedHits", 0) > 0 or tile.get("pendingRiftDice")
                or any(tile.get("pendingRiftBackfire", {}).values())):
            await channel.send("Resolve the pending hits and Rift Cannon effects before rolling again.")
            return
        if (tile.get("wolfPack") or tile.get("pendingWolfPack") or tile.get("ghostsRetreatPending")
                or any(not tile.get("phaseModuleReady", {}).get(color)
                       for color in tile.get("phaseModuleColors", []))):
            await channel.send("Resolve the pending faction ability choices before rolling again.")
            return
        await Combat.promptNextSpeed(game, pos, channel, False, repeat=True)

    @staticmethod
    async def promptNextSpeed(game: GamestateHelper, pos: str, channel, update: bool, repeat: bool = False):
        if len(Combat.currentPairing(game, pos)) != 2:
            return
        tile = game.gamestate["board"].get(pos, {})
        if (Carapace.has_pending_missiles(game, pos) or Combat.technoMagicPending(game, pos)
                or (tile.get("phaseModuleColors") and not tile.get("phaseModulePrompted"))):
            return
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

        nextPair = Combat.nextSpeedPair(sortedSpeeds, currentSpeed, currentRoller)
        phase = game.gamestate["board"][pos].get("firstShotPhase")
        if phase is not None and not repeat:
            firstShotSide = game.gamestate["board"][pos].get("firstShotSide") or []
            phaseSpeeds = [pair for pair in sortedSpeeds
                           if (pair[1] in firstShotSide) == (phase == "kurita")]
            nextPair = Combat.nextSpeedPair(phaseSpeeds, currentSpeed, currentRoller)
            if nextPair is None:
                # The delayed side only starts after the other side's whole first pass.
                game.gamestate["board"][pos]["firstShotPhase"] = (
                    "kurita" if phase == "opponent" else None)
                game.setCurrentRoller(None, pos)
                game.setCurrentSpeed(None, pos)
                currentSpeed = currentRoller = None
                if game.gamestate["board"][pos]["firstShotPhase"] == "kurita":
                    nextPair = next((pair for pair in sortedSpeeds if pair[1] in firstShotSide), None)
        nextSpeed = -20
        nextOwner = ""
        if repeat and currentSpeed is not None and currentRoller is not None:
            nextSpeed, nextOwner = currentSpeed, currentRoller
        elif nextPair is not None:
            nextSpeed, nextOwner = nextPair
        if nextSpeed == -20 or (currentSpeed is not None and currentSpeed > 90 and 0 <= nextSpeed < 90):
            # Wolf Pack saved rerolls only last for the engagement round they were earned in
            game.gamestate["board"][pos].pop("wolfPackRerolls", None)
        if nextSpeed == -20:
            game.gamestate["board"][pos].pop("rolledSteps", None)
            await Combat.checkForMorphShield(game, pos, channel, ships, list(attacker) + list(defender))
            await Carapace.offer(game, channel, pos)
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
        spine_options = []
        if nextOwner not in ("", "ai") and nextSpeed < 99:
            playerObj = game.getPlayerObjectFromColor(nextOwner)
            if FactionData.has(playerObj, "spine_cannons"):
                spine_options = Combat.spine_mode_options(game, nextOwner, pos, nextSpeed)
        spine_modes = bool(spine_options)

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

                if spine_modes:
                    bonuses = {bonus for _ship, _gun, bonus in spine_options}
                    tag = f"+{bonuses.pop()}" if len(bonuses) == 1 else "+X"
                    view.add_item(Button(label=f"Roll {initiative} ({tag} to Hit)", style=discord.ButtonStyle.green,
                                         custom_id=(f"{checker}rollDice_{pos}_{nextOwner}_{str(nextSpeed)}"
                                                    "_deleteMsg_spinehit")))
                    view.add_item(Button(label=f"Roll {initiative} ({tag} Damage)", style=discord.ButtonStyle.green,
                                         custom_id=(f"{checker}rollDice_{pos}_{nextOwner}_{str(nextSpeed)}"
                                                    "_deleteMsg_spinedmg")))
                    listing = ", ".join(f"{ship} {gun} +{bonus}" for ship, gun, bonus in spine_options)
                    msg += (f"Spine Cannon augments this roll: {listing}. The value is the augment"
                            " gun's damage; choose +Hit or +Damage before rolling. ")
                else:
                    view.add_item(Button(label=f"Roll {initiative} Ships", style=discord.ButtonStyle.green,
                                         custom_id=(f"{checker}rollDice_{pos}_{nextOwner}_{str(nextSpeed)}"
                                                    "_deleteMsg")))
                if nextSpeed < 99 and len(Combat.getRetreatTiles(game, pos, nextOwner)) > 0:
                    shipsSpeeds = Combat.getCombatantShipsBySpeed(game, nextOwner, ships, pos)
                    newSpeeds = 0
                    for ship in shipsSpeeds:
                        speed2 = ship[0]
                        if speed2 < 99 and speed2 != int(nextSpeed):
                            newSpeeds += 1
                            break
                    if FactionData.has(playerObj, "ghosts") and Combat.has_retreatable_ship(
                            game, pos, nextOwner, nextSpeed):
                        msg += "You may also retreat them immediately, before they fire. "
                        view.add_item(Button(label="Retreat Now", style=discord.ButtonStyle.red,
                                             custom_id=f"{checker}ghostsRetreat_{pos}_{nextOwner}_{str(nextSpeed)}"))
                    elif not FactionData.has(playerObj, "ghosts"):
                        msg += "You may also alternatively choose to start to retreat them. "
                        view.add_item(Button(label=f"Retreat {initiative} Ships", style=discord.ButtonStyle.red,
                                             custom_id=(f"{checker}startToRetreatUnits_{pos}_"
                                                        f"{nextOwner}_{str(nextSpeed)}")))
                    if newSpeeds < 1:
                        msg += ("You would lose out on the default"
                                " 1 reputation for battling if you choose to retreat here.")
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
    async def completeRetreat(game: GamestateHelper, interaction: discord.Interaction, pos: str,
                              colorOrAI: str, speed, destination: str, playerObj=None):
        oldLength = len(Combat.findPlayersInTile(game, pos))
        Carapace.close_controls(game, pos)
        game.removeCertainRetreatingUnits((int(speed), colorOrAI), pos)
        tile_map = game.gamestate["board"]
        player_ships = tile_map[pos]["player_ships"][:]
        for ship in player_ships:
            if colorOrAI in ship and "orb" not in ship and "mon" not in ship and "sb" not in ship:
                shiptype = ship.split("-")[1]
                player = game.get_player_from_color(colorOrAI)
                shipM = PlayerShip(game.gamestate["players"][player], shiptype)
                if (shipM.speed + Combat.phase_mode(
                        game, colorOrAI, pos, Combat.translateShipAbrToName(shiptype)).get("speed", 0)
                        == int(speed)):
                    game.remove_units([ship], pos)
                    game.add_units([ship], destination)
        if playerObj is None:
            playerObj = game.getPlayerObjectFromColor(colorOrAI)
        await interaction.message.delete()
        await interaction.channel.send(f"{playerObj['player_name']} has retreated all ships"
                                       f" with initiative {speed} to {destination}.")
        continued = await Combat.checkCombatEnd(game, interaction, pos, oldLength)
        if not continued:
            await Combat.promptNextSpeed(game, pos, interaction.channel, True)

    @staticmethod
    async def finishRetreatingUnits(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, playerObj):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        speed = buttonID.split("_")[3]
        destination = buttonID.split("_")[4]
        await Combat.completeRetreat(game, interaction, pos, colorOrAI, speed, destination, playerObj)

    @staticmethod
    def has_retreatable_ship(game: GamestateHelper, pos: str, color: str, speed):
        ships = game.gamestate["board"][pos].get("player_ships", [])
        for ship_speed, unit_type, _count in Combat.getCombatantShipsBySpeed(game, color, ships, pos):
            if ship_speed == int(speed) and unit_type != "sb":
                return True
        return False

    @staticmethod
    async def ghostsRetreat(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos, color, speed = buttonID.split("_")[1:4]
        playerObj = game.getPlayerObjectFromColor(color)
        tile = game.gamestate["board"][pos]
        if not FactionData.has(playerObj, "ghosts"):
            return
        if (tile.get("currentSpeed") != int(speed) or tile.get("currentRoller") != color
                or not Combat.has_retreatable_ship(game, pos, color, speed)):
            await interaction.channel.send("That retreat is no longer available. Refresh the combat view.")
            return
        tiles = Combat.getRetreatTiles(game, pos, color)
        if not tiles:
            await interaction.channel.send("There is no controlled sector to retreat to.")
            return
        tile["ghostsRetreatPending"] = color
        game.update()
        view = View()
        for destination in dict.fromkeys(tiles):
            view.add_item(Button(label=destination, style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{color}_ghostsRetreatTo_{pos}_{color}_{speed}_{destination}"))
        await interaction.message.delete()
        await interaction.channel.send(f"{playerObj['player_name']}, choose the controlled sector adjacent"
                                       " to retreat to. The ships leave before they fire.", view=view)

    @staticmethod
    async def ghostsRetreatTo(game: GamestateHelper, buttonID: str, interaction: discord.Interaction):
        pos, color, speed, destination = buttonID.split("_")[1:5]
        playerObj = game.getPlayerObjectFromColor(color)
        if not FactionData.has(playerObj, "ghosts"):
            return
        tile = game.gamestate["board"][pos]
        if (tile.get("currentSpeed") != int(speed) or tile.get("currentRoller") != color
                or not Combat.has_retreatable_ship(game, pos, color, speed)):
            await interaction.channel.send("That retreat is no longer available. Refresh the combat view.")
            return
        if destination not in Combat.getRetreatTiles(game, pos, color):
            await interaction.channel.send("That sector is no longer a legal retreat destination.")
            return
        tile.pop("ghostsRetreatPending", None)
        game.update()
        ships = Combat.getCombatantShipsBySpeed(
            game, color, game.gamestate["board"][pos].get("player_ships", []), pos)
        if not any(ship[0] < 99 and ship[0] != int(speed) for ship in ships):
            game.setRetreatingPenalty(color, pos)
        await Combat.completeRetreat(game, interaction, pos, color, speed, destination, playerObj)

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
                if not FactionData.has(player_helper.stats, "may_not_fight_ancients"):
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
        Carapace.close_controls(game, pos)
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
        if newSpeeds < 1 or FactionData.has(player, "honour_victorious"):
            game.setRetreatingPenalty(colorOrAI, pos)
            if FactionData.has(player, "honour_victorious"):
                message = (f"{interaction.user.mention}'s honour: retreating any ship means no Battle Reputation"
                           " at all this battle.")
            else:
                message = (f"{interaction.user.mention} is attempting  to retreat all their remaining ships"
                           " and will thus not receive the default 1 reputation tile draw at the end of combat")
            await interaction.channel.send(message)
        await Combat.promptNextSpeed(game, pos, interaction.channel, False)

    @staticmethod
    def technoMagicPending(game: GamestateHelper, pos: str):
        """Techno-Magic upgrades change speed and missiles, so initiative waits for them."""
        tile = game.gamestate["board"].get(pos, {})
        ready = tile.get("technoMagicReady", {})
        return any(not ready.get(color) for color in tile.get("technoMagicColors", []))

    @staticmethod
    async def offerTechnoMagic(game: GamestateHelper, channel, pos: str):
        """Techno-Magic: at the start of a combat, one temporary Upgrade 1 per ship blueprint.
        The attacker chooses first, the defender last. Returns whether initiative must wait."""
        tile = game.gamestate["board"][pos]
        colors = []
        for color in Combat.sideOf(tile.get("attacker")) + Combat.sideOf(tile.get("defender")):
            if color and color != "ai" and FactionData.has(game.getPlayerObjectFromColor(color), "techno_magic"):
                colors.append(color)
        if not colors:
            return False
        tile["technoMagicColors"] = colors
        tile["technoMagicReady"] = {}
        game.update()
        for color in colors:
            player = game.getPlayerObjectFromColor(color)
            await channel.send(f"{player['player_name']}, Techno-Magic lets you temporarily Upgrade 1 on each"
                               " ship blueprint for this combat. The new parts are removed when the battle"
                               " ends. You may not remove ship parts or place Ancient ship parts.",
                               view=UpgradeButtons.getTechnoMagicView(game, player, pos))
        return True

    @staticmethod
    async def technoMagicDone(game: GamestateHelper, customID: str, player, interaction: discord.Interaction):
        pos = customID.split("_")[1]
        tile = game.gamestate["board"].get(pos, {})
        color = player["color"]
        if color not in tile.get("technoMagicColors", []):
            return
        ready = tile.setdefault("technoMagicReady", {})
        if ready.get(color):
            await interaction.followup.send("You have already finished Techno-Magic.", ephemeral=True)
            return
        ready[color] = True
        game.update()
        await interaction.message.edit(content=f"{player['player_name']} has finished Techno-Magic.", view=None)
        if not Combat.technoMagicPending(game, pos):
            await Combat.promptNextSpeed(game, pos, interaction.channel, False)

    @staticmethod
    async def technoMagicUpgrade(game: GamestateHelper, customID: str, player, interaction: discord.Interaction,
                                 player_helper: PlayerHelper):
        pos, ship = customID.split("_")[1:3]
        color = player["color"]
        if game.gamestate["board"].get(pos, {}).get("technoMagicReady", {}).get(color):
            await interaction.followup.send("You have already finished Techno-Magic.", ephemeral=True)
            return
        # the first install anywhere holds the pre-combat blueprint, so overlapping combats
        # each remove only their own temporary part
        base = next((tile["tmParts"][color][ship]["base"]
                     for tile in game.gamestate["board"].values()
                     if tile.get("tmParts", {}).get(color, {}).get(ship, {}).get("base")), None)
        record = game.gamestate["board"][pos].setdefault("tmParts", {}).setdefault(color, {}).setdefault(ship, {})
        if record.get("install"):
            await interaction.followup.send("You have already upgraded that blueprint this combat.", ephemeral=True)
            return
        record["base"] = base if base is not None else list(player[f"{ship}_parts"])
        game.update()
        await UpgradeButtons.upgradeShip(game, player, interaction, f"upgradeShip_1_{ship}_tm{pos}", player_helper)

    @staticmethod
    async def revertTechnoMagic(game: GamestateHelper, channel, pos: str):
        """The temporary parts installed at the start of this combat come off again."""
        for color, ships in game.gamestate["board"][pos].pop("tmParts", {}).items():
            player = game.getPlayerObjectFromColor(color)
            player_helper = PlayerHelper(color, player)
            restore = {}
            for ship, record in ships.items():
                pending = any(tile.get("tmParts", {}).get(color, {}).get(ship, {}).get("install")
                              for key, tile in game.gamestate["board"].items() if key != pos)
                if not pending:
                    restore[ship] = record["base"]
            if restore:
                for ship, parts in restore.items():
                    player[f"{ship}_parts"] = parts
                game.update_player(player_helper)
                await channel.send(f"Techno-Magic wears off: the temporary ship parts are removed"
                                   f" from {player['player_name']}'s blueprints.")
            else:
                # every install belongs to a combat that is still pending; the pop itself must persist
                game.update()

    @staticmethod
    def computer_description(shipModel, extra: int = 0):
        """Name the sources of a ship's computer total so a third player can audit it."""
        parts_comp = shipModel.computer - shipModel.base_computer
        bits = []
        if parts_comp:
            electron = shipModel.ship_parts.count("elc")
            bits.append(f"+{parts_comp} Electron Computer" if electron and parts_comp == electron
                        else f"+{parts_comp} ship parts")
        if shipModel.base_computer:
            label = FactionData.of(shipModel.player).get("offboard_computer_label", "off-board")
            bits.append(f"+{shipModel.base_computer} {label}")
        if extra:
            bits.append(f"+{extra} Phase Module")
        return " (" + ", ".join(bits) + ")" if bits else ""

    @staticmethod
    def spine_mode_options(game: GamestateHelper, color: str, pos: str, speed: int):
        """The Spine Cannon ships firing at this initiative and the bonus each augment gives."""
        player = game.get_player_from_color(color)
        with open("data/parts.json", "r") as part_file:
            part_data = json.load(part_file)
        options = []
        for speed2, ship_type, _count in Combat.getCombatantShipsBySpeed(
                game, color, game.gamestate["board"][pos].get("player_ships", []), pos):
            if speed2 != speed:
                continue
            ship = PlayerShip(game.gamestate["players"][player], ship_type)
            augment = ship.spine_augment()
            if not augment:
                continue
            gun = part_data.get(ship.ship_parts[augment[0]], {}).get("name", ship.ship_parts[augment[0]])
            options.append((Combat.translateShipAbrToName(ship_type), gun,
                            Combat.translateColorToDamage(augment[2], 6)))
        return options

    @staticmethod
    def part_name(part_id: str):
        with open("data/parts.json", "r") as part_file:
            return json.load(part_file).get(part_id, {}).get("name", part_id)

    @staticmethod
    def phase_option_cost(mode):
        """The printed 2-Power line buys Neutron Bombs and +2 Initiative together."""
        cost = sum(price for option, (_label, price) in Combat.PHASE_OPTIONS.items()
                   if mode.get(option) and option not in ("speed", "planets"))
        if mode.get("speed") or mode.get("planets"):
            cost += 2
        return cost

    @staticmethod
    def phase_ship_types(game: GamestateHelper, color: str, pos: str):
        ships = game.gamestate["board"][pos].get("player_ships", [])
        types = []
        for _speed, unit_type, _count in Combat.getCombatantShipsBySpeed(game, color, ships, pos):
            ship_type = Combat.translateShipAbrToName(unit_type)
            if ship_type not in types:
                types.append(ship_type)
        return types

    @staticmethod
    def phase_mode_valid(game: GamestateHelper, color: str, pos: str, ship_type: str, record):
        player = game.getPlayerObjectFromColor(color)
        modes = dict(game.gamestate["board"].get(pos, {}).get("phaseModes", {}).get(color, {}))
        modes[ship_type] = record
        return all(mode.get("cost", 0) <= max(0, PlayerShip(player, ship).energy)
                   for ship, mode in modes.items())

    @staticmethod
    def phase_module_main_view(game: GamestateHelper, color: str, pos: str):
        player = game.getPlayerObjectFromColor(color)
        types = Combat.phase_ship_types(game, color, pos)
        view = View()
        for ship_type in types:
            view.add_item(Button(label=ship_type.capitalize(), style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{color}_phaseModuleShip_{pos}_{color}_{ship_type}"))
        view.add_item(Button(label="Done Declaring", style=discord.ButtonStyle.green,
                             custom_id=f"FCID{color}_phaseModuleDone_{pos}_{color}"))
        view.add_item(Button(label="Clear All & Start Combat", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{color}_phaseModuleNone_{pos}_{color}"))
        power = ", ".join(f"{ship_type.capitalize()} {max(0, PlayerShip(player, ship_type).energy)}"
                          for ship_type in types)
        content = (f"{player['player_name']}, declare Phase Module options for this combat. "
                   f"Blueprint power: {power}. "
                   "Options: +1 to Hit (1), +1 Shield (1), +2 Initiative (2), "
                   "Neutron Bombs (2, needs the technology), Ignore Shields (3). "
                   "Neutron Bombs and +2 Initiative cost 2 power together. "
                   f"Each blueprint includes +{player.get('wraithSouls', 0)} permanent offboard power. "
                   "Cloaking Device is always on.")
        return content, view

    @staticmethod
    def phase_module_ship_view(game: GamestateHelper, color: str, pos: str, ship_type: str):
        player = game.getPlayerObjectFromColor(color)
        mode = Combat.phase_mode(game, color, pos, ship_type)
        view = View()
        options = [(option, label, cost) for option, (label, cost) in Combat.PHASE_OPTIONS.items()
                   if option != "planets"]
        if "neb" in PlayerHelper(game.get_player_from_color(color), player).getTechs():
            options.insert(3, ("planets", *Combat.PHASE_OPTIONS["planets"]))
        for option, label, cost in options:
            on = bool(mode.get(option))
            view.add_item(Button(label=f"{'✓ ' if on else ''}{label} ({cost})",
                                 style=discord.ButtonStyle.green if on else discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{color}_phaseModuleOption_{pos}_{color}_{ship_type}_{option}"))
        view.add_item(Button(label=f"Reset {ship_type.capitalize()}", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{color}_phaseModuleReset_{pos}_{color}_{ship_type}"))
        view.add_item(Button(label="Back", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{color}_phaseModuleBack_{pos}_{color}"))
        remaining = max(0, PlayerShip(player, ship_type).energy - mode.get("cost", 0))
        content = (f"{player['player_name']}, {ship_type.capitalize()}: "
                   f"{remaining} unused blueprint energy; "
                   f"Declared: {mode.get('cost', 0)} power.")
        return content, view

    @staticmethod
    def phase_declaration_summary(game: GamestateHelper, color: str, pos: str):
        """The options one player declared for each blueprint, for the whole table to read."""
        modes = game.gamestate["board"].get(pos, {}).get("phaseModes", {}).get(color, {})
        if not modes:
            return "No options were declared, so only the Cloaking Device applies."
        declared = "; ".join(
            f"{ship_type.capitalize()}: "
            + ", ".join(label for option, (label, _cost) in Combat.PHASE_OPTIONS.items()
                        if mode.get(option))
            + f" ({mode.get('cost', 0)} power)"
            for ship_type, mode in modes.items())
        return f"{declared}. Cloaking Device is always on."

    @staticmethod
    async def offerPhaseModule(game: GamestateHelper, channel, pos: str):
        """Phase Module: declare each blueprint's options before initiative is prompted."""
        tile = game.gamestate["board"][pos]
        pairing = Combat.sideOf(tile.get("attacker")) + Combat.sideOf(tile.get("defender"))
        colors = []
        for color in pairing:
            if color == "ai":
                continue
            player = game.getPlayerObjectFromColor(color)
            if (FactionData.has(player, "phase_module")
                    and Combat.phase_ship_types(game, color, pos)):
                colors.append(color)
        if not colors:
            return False
        tile["phaseModuleColors"] = colors
        tile["phaseModuleReady"] = {}
        tile["phaseModes"] = {}
        game.update()
        for color in colors:
            content, view = Combat.phase_module_main_view(game, color, pos)
            await channel.send(content, view=view)
        return True

    @staticmethod
    async def phaseModuleShip(game: GamestateHelper, customID: str, interaction: discord.Interaction):
        _tag, pos, color, ship_type = customID.split("_")
        player = game.getPlayerObjectFromColor(color)
        if (not FactionData.has(player, "phase_module")
                or game.gamestate["board"].get(pos, {}).get("phaseModuleReady", {}).get(color)
                or ship_type not in Combat.phase_ship_types(game, color, pos)):
            await interaction.followup.send("That blueprint is not in this combat.", ephemeral=True)
            return
        content, view = Combat.phase_module_ship_view(game, color, pos, ship_type)
        await interaction.message.edit(content=content, view=view)

    @staticmethod
    async def phaseModuleBack(game: GamestateHelper, customID: str, interaction: discord.Interaction):
        _tag, pos, color = customID.split("_")
        player = game.getPlayerObjectFromColor(color)
        if (not FactionData.has(player, "phase_module")
                or game.gamestate["board"].get(pos, {}).get("phaseModuleReady", {}).get(color)):
            return
        content, view = Combat.phase_module_main_view(game, color, pos)
        await interaction.message.edit(content=content, view=view)

    @staticmethod
    async def phaseModuleOption(game: GamestateHelper, customID: str, interaction: discord.Interaction):
        _tag, pos, color, ship_type, option = customID.split("_")
        player = game.getPlayerObjectFromColor(color)
        if (not FactionData.has(player, "phase_module")
                or game.gamestate["board"].get(pos, {}).get("phaseModuleReady", {}).get(color)
                or ship_type not in Combat.phase_ship_types(game, color, pos)):
            await interaction.followup.send("That blueprint is not in this combat.", ephemeral=True)
            return
        values = {option: cost for option, (_label, cost) in Combat.PHASE_OPTIONS.items()}
        if option not in values:
            return
        if option == "planets" and "neb" not in PlayerHelper(
                game.get_player_from_color(color), player).getTechs():
            await interaction.followup.send("Research Neutron Bombs before declaring that option.", ephemeral=True)
            return
        tile = game.gamestate["board"][pos]
        if color not in tile.get("phaseModuleColors", []):
            await interaction.followup.send("That Phase Module declaration is no longer current.",
                                            ephemeral=True)
            return
        modes = tile.setdefault("phaseModes", {}).setdefault(color, {})
        mode = dict(modes.get(ship_type, {"comp": 0, "shield": 0, "speed": 0,
                                          "planets": False, "ignore": False, "cost": 0}))
        mode[option] = 0 if mode.get(option) else values[option]
        if option in ("planets", "ignore"):
            mode[option] = bool(mode[option])
        mode["cost"] = Combat.phase_option_cost(mode)
        if not Combat.phase_mode_valid(game, color, pos, ship_type, mode):
            await interaction.followup.send("Not enough power available on this blueprint.",
                                            ephemeral=True)
            return
        if mode["cost"]:
            modes[ship_type] = mode
        else:
            modes.pop(ship_type, None)
        game.update()
        content, view = Combat.phase_module_ship_view(game, color, pos, ship_type)
        await interaction.message.edit(content=content, view=view)

    @staticmethod
    async def phaseModuleReset(game: GamestateHelper, customID: str, interaction: discord.Interaction):
        _tag, pos, color, ship_type = customID.split("_")
        player = game.getPlayerObjectFromColor(color)
        if (not FactionData.has(player, "phase_module")
                or game.gamestate["board"].get(pos, {}).get("phaseModuleReady", {}).get(color)):
            return
        modes = game.gamestate["board"][pos].get("phaseModes", {}).get(color, {})
        modes.pop(ship_type, None)
        game.update()
        content, view = Combat.phase_module_ship_view(game, color, pos, ship_type)
        await interaction.message.edit(content=content, view=view)

    @staticmethod
    async def phaseModuleDone(game: GamestateHelper, customID: str, interaction: discord.Interaction,
                              clear: bool = False):
        _tag, pos, color = customID.split("_")
        tile = game.gamestate["board"][pos]
        colors = tile.get("phaseModuleColors", [])
        player = game.getPlayerObjectFromColor(color)
        if color not in colors or not FactionData.has(player, "phase_module"):
            return
        ready = tile.setdefault("phaseModuleReady", {})
        if ready.get(color):
            await interaction.followup.send("You have already finished declaring.", ephemeral=True)
            return
        if clear:
            tile.get("phaseModes", {}).pop(color, None)
        modes = tile.get("phaseModes", {}).get(color, {})
        if any(not Combat.phase_mode_valid(game, color, pos, ship, mode)
               for ship, mode in modes.items()):
            await interaction.followup.send("Not enough power available on this blueprint.", ephemeral=True)
            return
        ready[color] = True
        game.update()
        await interaction.message.edit(
            content=(f"{player['player_name']} has finished declaring Phase Module options. "
                     f"{Combat.phase_declaration_summary(game, color, pos)}"),
            view=None)
        if (all(ready.get(color2) for color2 in colors)
                and not tile.get("phaseModulePrompted")):
            tile["phaseModulePrompted"] = True
            game.update()
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
        Combat.clearWolfPack(game, pos)

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
        await Combat.revertTechnoMagic(game, interaction.channel, pos)
        Carapace.clear(game, pos)
        entry_order = game.getCombatEntryOrder(pos)
        players = sorted(players, key=lambda color: (entry_order.index(color) if color in entry_order
                                                      else len(entry_order), players.index(color)))
        survivors = [color for color in Combat.findPlayersInTile(game, pos) if color != "ai"]
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
                if FactionData.has(player, "honour_victorious"):
                    side_survived = any(color == playerColor or game.areAllied(playerColor, color)
                                        for color in survivors)
                    game.gamestate.setdefault("battleRepAdjustments", {})[
                        f"{system}-{countDraw}-{playerColor}"] = 1 if side_survived else -1
                if "tilesToResolve" in game.gamestate:
                    game.addToKey("queuedQuestions", [int(game.gamestate["board"][pos]["sector"]),
                                                      countDraw, playerColor])
                    countDraw += 1
                asyncio.create_task(interaction.channel.send(msg, view=view))
        # An Alliance wins as a side. Its members decide who drops the disc in
        # order of entry to the sector, so offer it to the earliest first.
        entryOrder = game.getCombatEntryOrder(pos)
        survivors.sort(key=lambda color: entryOrder.index(color) if color in entryOrder else len(entryOrder))
        winner = next(iter(survivors), None)
        owner = game.gamestate["board"][pos]["owner"]

        winner_owns_or_allies = (winner is not None and owner != 0 and owner != "ai"
                                 and game.areAllied(winner, owner))
        # Nebula Sectors take no influence; their Discovery Tiles are offered at upkeep
        nebula = game.gamestate["board"][pos].get("type") == "nebula"
        if winner is not None and owner != winner and not winner_owns_or_allies and not nebula:
            player = game.getPlayerObjectFromColor(winner)
            playerName = player["player_name"]
            if owner == 0:
                if Combat.discoveryTileClaimable(game, pos):
                    await Combat.offerDiscoveryTile(game, interaction.channel, pos, winner)
                message = f"{playerName}, you may place your influence on the tile."
                if len(survivors) > 1:
                    message = (f"{playerName}, your Alliance may place an influence disc here. "
                               "The buttons are in order of entry to the sector, so the first of you to "
                               "want the disc should take it.")
                await InfluenceButtons.offerInfluenceDisc(game, interaction.channel, pos, survivors, message)
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
                wraithPlanets = (FactionData.has(player, "phase_module")
                                 and Combat.phase_declared_planets(game, player["color"], pos))
                if (FactionData.has(p2, "population_destroyed_in_combat") or game.is_population_gone(pos)
                        or ("neb" in player_helper.getTechs() and "nea" not in player_helper2.getTechs()
                            and (not FactionData.has(player, "phase_module") or wraithPlanets))):
                    if Combat.discoveryTileClaimable(game, pos):
                        await Combat.offerDiscoveryTile(game, interaction.channel, pos, winner)
                    view = View()
                    view.add_item(Button(label="Destroy All Population", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{winner}_removeInfluenceFinish_{pos}_graveYard"))
                    message = f"{playerName}, you may destroy all enemy influence and population automatically."
                    if wraithPlanets:
                        message += " Neutron Bombs were declared (2 blueprint Power)."
                    asyncio.create_task(interaction.channel.send(message, view=view))
                    message = (f"{playerName}, you may place your influence on the"
                               " tile after destroying the enemy population.")
                    await InfluenceButtons.offerInfluenceDisc(game, interaction.channel, pos, [winner], message)
                    view3 = View()
                    view3.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                                          custom_id=f"FCID{player['color']}_startPopDrop"))
                    message = (f"{playerName}, if you have enough colony ships,"
                               " you may use this to drop population after taking control of the sector.")
                    asyncio.create_task(interaction.channel.send(message, view=view3))
                else:
                    if (FactionData.has(p2, "may_not_fight_ancients")
                            and game.gamestate["board"][pos]["disctile"] != 0):
                        await interaction.channel.send("**REMINDER: Do not resolve the discovery tile until bombing "
                                                       "population has been resolved. If Draco still controls the "
                                                       "sector afterwards, they will gain the discovery tile at the "
                                                       "end of the Combat Phase.**")
                    view = View()
                    view.add_item(Button(label="Roll to Destroy Population", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{winner}_rollDice_{pos}_{winner}_1000_deleteMsg"))
                    message = f"{playerName}, you may roll to attempt to kill enemy population."
                    if (FactionData.has(player, "phase_module") and "neb" in player_helper.getTechs()
                            and not wraithPlanets):
                        message += (" The Phase Module Planets option was not declared at the start of this"
                                    " combat, so only the roll is available.")
                    asyncio.create_task(interaction.channel.send(message, view=view))
        for playerColor in players:
            game.gamestate["board"][pos].pop("retreatPenalty" + playerColor, None)
        game.gamestate["board"][pos].pop("ghostsRetreatPending", None)
        game.gamestate["board"][pos].pop("firstShotPhase", None)
        game.gamestate["board"][pos].pop("firstShotSide", None)
        Combat.clear_phase_module(game, pos)


    @staticmethod
    async def checkCombatEnd(game: GamestateHelper, interaction: discord.Interaction, pos: str, oldLength: int):
        if Carapace.has_pending_missiles(game, pos):
            # let the fired missiles resolve before a pairing can end the battle
            return True
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
                    or tile.get("carapacePendingMissiles")
                    or any(tile.get("pendingRiftBackfire", {}).values())):
                # Otherwise the last pending hit prompts the next initiative step.
                await Combat.promptNextSpeed(game, pos, interaction.channel, True)
            return True
        return False

    @staticmethod
    async def assignHitTo(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, button: bool,
                          deferEnd: bool = False, reports=None):
        pos = buttonID.split("_")[1]
        colorOrAI = buttonID.split("_")[2]
        ship = buttonID.split("_")[3]
        dieNum = buttonID.split("_")[4]
        dieDam = buttonID.split("_")[5]
        carapace_bypass = dieDam.endswith("!")
        dieDam = dieDam.rstrip("!")
        deferEnd = deferEnd or buttonID.endswith("_defer")
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
        ship_class = shipModel.ship_type if shipOwner != "ai" else shipType.replace("adv", "")
        damage_value = int(dieDam) if carapace_bypass else Carapace.incoming_damage(
            game, pos, shipOwner, ship_class, colorOrAI, int(dieDam))
        with game.batch_save():
            damage = game.add_damage(ship, pos, damage_value)
            if colorOrAI != "ai":
                msg = (f"{interaction.user.mention} dealt {damage_value} damage to a"
                       f" {Combat.translateShipAbrToName(shipType)}{suffix} with a die that rolled a {str(dieNum)}. ")
            else:
                msg = (f"The AI dealt {damage_value} damage to a {Combat.translateShipAbrToName(shipType)}{suffix}"
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
        if reports is None:
            await interaction.channel.send(msg)
        else:
            reports.append(msg)
        if shipModel.hull < damage and not deferEnd:
            if reports is not None and (oldLength != len(Combat.findPlayersInTile(game, pos))
                                        or len(Combat.findSidesInTile(game, pos)) < 2):
                await Combat.sendCombatReports(interaction.channel, reports)
            await Combat.checkCombatEnd(game, interaction, pos, oldLength)
        if button:
            await interaction.message.delete()
            if hitsToAssign == 0:
                playersAfter = len(Combat.findPlayersInTile(game, pos))
                if await Combat.offerPendingWolfPack(game, pos, interaction):
                    return
                if deferEnd and oldLength != playersAfter:
                    await Combat.checkCombatEnd(game, interaction, pos, oldLength)
                elif oldLength == playersAfter:
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
                        adjustment = game.gamestate.get("battleRepAdjustments", {}).pop(
                            f"{int(system)}-{drawOrder}-{color}", 0)
                        await ReputationButtons.resolveGainingReputation(
                            game, num_options, interaction, player_helper, True,
                            battle_rep_adjustment=adjustment)
                        game.removeFromKey("queuedDraws", [system, drawOrder, color, num_options])
                        success += 1

    @staticmethod
    async def dontDrawReputation(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, player_helper):
        system = int(buttonID.split("_")[1])
        drawOrder = int(buttonID.split("_")[2])
        color = buttonID.split("_")[3]
        game.gamestate.get("battleRepAdjustments", {}).pop(f"{system}-{drawOrder}-{color}", None)
        if "tilesToResolve" in game.gamestate:
            game.removeFromKey("queuedQuestions", [system, drawOrder, color])
            await Combat.resolveQueue(game, interaction)
        await interaction.message.delete()

    @staticmethod
    def battle_rep_suffix(adjustment):
        return f" ({adjustment:+d} for the battle)" if adjustment else ""

    @staticmethod
    async def drawReputation(game: GamestateHelper, buttonID: str, interaction: discord.Interaction, player_helper):
        num_options = int(buttonID.split("_")[1])
        system = int(buttonID.split("_")[2])
        drawOrder = int(buttonID.split("_")[3])
        color = buttonID.split("_")[4]
        if "tilesToResolve" in game.gamestate:
            adjustment = game.gamestate.get("battleRepAdjustments", {}).get(
                f"{system}-{drawOrder}-{color}", 0)
            game.removeFromKey("queuedQuestions", [system, drawOrder, color])
            game.addToKey("queuedDraws", [system, drawOrder, color, num_options])
            await Combat.resolveQueue(game, interaction)
            if [system, drawOrder, color, num_options] in game.gamestate["queuedDraws"]:
                asyncio.create_task(interaction.channel.send(f"{interaction.user.name}, your reputation draw has been queued"))
            else:
                asyncio.create_task(interaction.channel.send(
                    f"{interaction.user.name} drew {num_options} reputation tiles"
                    + Combat.battle_rep_suffix(adjustment) + "."))
            try:
                await interaction.message.delete()
            except discord.NotFound:
                print(f"Message {interaction.message.id} was already deleted.")
        else:
            adjustment = game.gamestate.get("battleRepAdjustments", {}).pop(
                f"{system}-{drawOrder}-{color}", 0)
            await ReputationButtons.resolveGainingReputation(game, num_options, interaction, player_helper, False,
                                                             battle_rep_adjustment=adjustment)
            asyncio.create_task(interaction.channel.send(
                f"{interaction.user.name} drew {num_options} reputation tiles"
                + Combat.battle_rep_suffix(adjustment) + "."))
            try:
                await interaction.message.delete()
            except discord.NotFound:
                print(f"Message {interaction.message.id} was already deleted.")

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
    def die_face(interaction: discord.Interaction, dieColor: str, dieValue: int):
        """A die face as its dice emoji, or the plain number when the bot has no such emoji."""
        name = f"dice_{Combat.translateColorToName(dieColor)}_{dieValue}"
        emoji = Emoji._app.get(name) or next(
            (str(item) for item in interaction.guild.emojis if item.name == name), None)
        return emoji or str(dieValue)

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
