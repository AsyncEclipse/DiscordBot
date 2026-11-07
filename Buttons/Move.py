import asyncio
import random
import discord
from Buttons.BlackHole import BlackHoleButtons
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from helpers import FactionData
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button
from jproperties import Properties

from helpers.ShipHelper import PlayerShip


class MoveButtons:
    @staticmethod
    def getMoveQueueCount(buttonID: str):
        for part in buttonID.split("_"):
            if part.startswith("q") and part[1:].isdigit():
                return int(part[1:])
        return 0

    @staticmethod
    def hasMoveQueueMarker(buttonID: str):
        return any(part.startswith("q") and part[1:].isdigit() for part in buttonID.split("_"))

    @staticmethod
    def withoutMoveQueueCount(buttonID: str):
        return "_".join(part for part in buttonID.split("_")
                        if not (part.startswith("q") and part[1:].isdigit()))

    @staticmethod
    def getRemainingMoveActivations(player, moveCount: int, nested: bool):
        if nested or player.get("passed") or moveCount <= 0 or moveCount > player["move_apt"]:
            return 1
        return player["move_apt"] - moveCount + 1

    @staticmethod
    def getMovableShipsOfType(game: GamestateHelper, player, origin: str, shipType: str):
        shipName = f"{player['color']}-{game.getShipShortName(shipType)}"
        ships = game.gamestate["board"][origin].get("player_ships", [])[:]
        movable = 0
        while shipName in ships and ExploreButtons.doesPlayerHaveUnpinnedShips(player, ships, game, origin):
            ships.remove(shipName)
            movable += 1
        return movable

    @staticmethod
    def buildShipTypeView(game: GamestateHelper, player, originT: str, moveCount: str,
                          ship_filter: str, nested: bool, phase: str):
        view = View()
        shipTypes = ["interceptor", "cruiser", "dreadnought"]
        if FactionData.has(player, "harvester"):
            shipTypes.append("starbase")
        if ship_filter == "sb":
            shipTypes = ["starbase"]
        suffix = f"_herRegroup_{phase}" if nested else f"_{ship_filter}"
        for shipType in shipTypes:
            key = {"dreadnought": "dread"}.get(shipType, shipType)
            if not player.get(f"{key}_parts"):
                continue
            ship = PlayerShip(player, shipType)
            shipTest = f"{player['color']}-{game.getShipShortName(shipType)}"
            movable = MoveButtons.getMovableShipsOfType(game, player, originT, shipType)
            if shipTest in game.gamestate["board"][originT].get("player_ships", []) and movable and ship.getRange() > 0:
                shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(shipType))
                view.add_item(Button(label=f"{shipType.capitalize()} (Range: {ship.getRange()})", emoji=shipEmoji,
                                     style=discord.ButtonStyle.blurple,
                                     custom_id=(f"FCID{player['color']}_moveThisShip_{originT}"
                                                f"_{shipType}_{moveCount}{suffix}")))
        return view

    @staticmethod
    def buildMoveQueueView(player, origin: str, shipType: str, moveCount: str, selected: int,
                           max_selected: int, suffix: str):
        view = View()
        view.add_item(Button(label=f"Add {shipType.capitalize()} ({selected}/{max_selected})",
                             style=discord.ButtonStyle.blurple,
                             disabled=selected >= max_selected,
                             custom_id=(f"FCID{player['color']}_moveQueueAdd_{origin}_{shipType}"
                                        f"_{moveCount}_{selected}{suffix}")))
        view.add_item(Button(label="Reset Selection", style=discord.ButtonStyle.gray,
                             custom_id=(f"FCID{player['color']}_moveQueueReset_{origin}_{shipType}"
                                        f"_{moveCount}{suffix}")))
        view.add_item(Button(label=f"Done ({selected})", style=discord.ButtonStyle.green,
                             custom_id=(f"FCID{player['color']}_moveQueueDone_{origin}_{shipType}"
                                        f"_{moveCount}_{selected}{suffix}")))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        return view

    @staticmethod
    def getMoveQueueContext(buttonID: str, suffix_start: int):
        parts = buttonID.split("_")
        nested = "herRegroup" in parts[suffix_start:]
        phase = parts[-1] if nested else ""
        ship_filter = "all" if nested else (parts[suffix_start] if len(parts) > suffix_start else "all")
        suffix = f"_herRegroup_{phase}" if nested else f"_{ship_filter}"
        return nested, phase, ship_filter, suffix

    @staticmethod
    async def moveQueueAdd(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        parts = buttonID.split("_")
        origin, shipType, moveCount, selected = parts[1], parts[2], parts[3], int(parts[4])
        nested, phase, _ship_filter, suffix = MoveButtons.getMoveQueueContext(buttonID, 5)
        max_selected = min(MoveButtons.getMovableShipsOfType(game, player, origin, shipType),
                           MoveButtons.getRemainingMoveActivations(player, int(moveCount), nested))
        selected = min(selected + 1, max_selected)
        view = MoveButtons.buildMoveQueueView(player, origin, shipType, moveCount, selected, max_selected, suffix)
        await interaction.message.edit(content=(f"{player['player_name']}, select how many {shipType}s to move "
                                               f"from {game.get_tile_label(origin)} "
                                               f"({max_selected} activations available)."), view=view)

    @staticmethod
    async def moveQueueReset(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        parts = buttonID.split("_")
        origin, moveCount = parts[1], parts[3]
        nested, phase, ship_filter, _suffix = MoveButtons.getMoveQueueContext(buttonID, 4)
        view = MoveButtons.buildShipTypeView(game, player, origin, moveCount, ship_filter, nested, phase)
        if nested:
            MoveButtons.addRegroupBackButton(view, player, phase)
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.message.edit(content=(f"{player['player_name']}, select the ship to move from "
                                               f"{game.get_tile_label(origin)}"), view=view)

    @staticmethod
    async def moveQueueDone(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        parts = buttonID.split("_")
        origin, shipType, moveCount, selected = parts[1], parts[2], parts[3], int(parts[4])
        nested, phase, _ship_filter, suffix = MoveButtons.getMoveQueueContext(buttonID, 5)
        max_selected = min(MoveButtons.getMovableShipsOfType(game, player, origin, shipType),
                           MoveButtons.getRemainingMoveActivations(player, int(moveCount), nested))
        if selected < 1 or selected > max_selected:
            await interaction.followup.send("That many ships can no longer move from this sector.", ephemeral=True)
            return
        await MoveButtons.moveThisShip(game, player, interaction,
                                       f"moveThisShip_{origin}_{shipType}_{moveCount}_q{selected - 1}{suffix}")

    @staticmethod
    async def moveQueueContinue(game: GamestateHelper, player, interaction: discord.Interaction,
                                buttonID: str, player_helper: PlayerHelper):
        parts = buttonID.split("_")
        origin, shipType, destination = parts[1], parts[2], parts[3]
        moveCount, remaining = int(parts[4]), int(parts[5])
        if player.get("passed") or not 1 < moveCount <= player["move_apt"]:
            await interaction.message.delete()
            await interaction.channel.send("No move activations remain for the queued ship.")
            await MoveButtons.sendMoveContinuation(player, interaction, moveCount - 1)
            return
        if (MoveButtons.getMovableShipsOfType(game, player, origin, shipType) < 1
                or destination not in MoveButtons.getTilesInRange(
                    game, player, origin, PlayerShip(player, shipType).getRange(),
                    PlayerShip(player, shipType).getJumpDrive())
                or destination == origin):
            await interaction.message.delete()
            await interaction.channel.send(f"The queued {shipType} can no longer move to "
                                           f"{game.get_tile_label(destination)}.")
            await MoveButtons.sendMoveContinuation(player, interaction, moveCount - 1)
            return
        await MoveButtons.moveTo(game, player, interaction,
                                 f"moveTo_{origin}_{shipType}_{destination}_{moveCount}_q{remaining - 1}_all",
                                 player_helper)

    @staticmethod
    def addRegroupBackButton(view: View, player, phase: str):
        if phase == "before":
            view.add_item(Button(label="Back to Build", style=discord.ButtonStyle.gray,
                                 custom_id=f"FCID{player['color']}_herBackToBuild"))
        else:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))

    @staticmethod
    def getListOfUnpinnedShipTiles(game: GamestateHelper, player, ship_filter="all"):
        tile_map = game.gamestate["board"]
        ship_types = ("int", "cru", "drd")
        if FactionData.has(player, "harvester"):
            ship_types += ("sb",)
        if ship_filter == "sb":
            ship_types = ("sb",)
        tiles = []
        for tile in tile_map:
            if "player_ships" in tile_map[tile]:
                if not any(f"{player['color']}-{ship}" in tile_map[tile]["player_ships"]
                           for ship in ship_types):
                    continue
                if ExploreButtons.doesPlayerHaveUnpinnedShips(player, tile_map[tile]["player_ships"], game, tile):
                    tiles.append(tile)
        return tiles

    @staticmethod
    async def startMove(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str, button: bool):
        nested = "herRegroup" in buttonID
        raid_resume = "herRaidResume" in buttonID
        phase = buttonID.rsplit("_", 1)[1] if nested else ""
        moveCount = 1
        ship_filter = "all"
        if "_" in buttonID:
            moveCount = buttonID.split("_")[1]
        if buttonID == "startMove":
            player.pop("pulsarMove", None)
            if FactionData.has(player, "raid") or FactionData.has(player, "regroup"):
                player["herCrossUsed"] = False
                player["herRaidCharged"] = False
            game.update()
        if not nested and len(buttonID.split("_")) > 2 and not raid_resume:
            ship_filter = buttonID.split("_")[2]
        view = View()
        tiles = MoveButtons.getListOfUnpinnedShipTiles(game, player, ship_filter)
        suffix = f"_herRegroup_{phase}" if nested else ""
        if not nested and ship_filter != "all":
            suffix = f"_{ship_filter}"
        for tile in tiles:
            view.add_item(Button(label=game.get_tile_label(tile), style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_moveFrom_{tile}_{moveCount}{suffix}"))
        raid_offer = (not player.get("passed") and FactionData.has(player, "raid")
                      and not player.get("pulsarMove") and not player.get("herCrossUsed")
                      and int(moveCount) <= player["move_apt"])
        if nested:
            MoveButtons.addRegroupBackButton(view, player, phase)
        elif raid_offer:
            view.add_item(Button(label="Build Activation (1)", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_herRaidBuild_{moveCount}"))
        if raid_resume:
            view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        if button:
            if moveCount == 1 and not nested:
                await interaction.channel.send(f"{player['player_name']} is using their turn to move")
            await interaction.message.delete()
        message = f"{player['player_name']} Select the tile you would like to move from"
        if raid_offer and not nested:
            message += ". Raid: this Move action also includes one Build activation"
        await interaction.channel.send(message, view=view)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))

    @staticmethod
    async def startHarvesterMove(game: GamestateHelper, player, interaction: discord.Interaction):
        """The free Harvester move that belongs to an Explore action."""
        if not FactionData.has(player, "harvester"):
            return
        if player.get("harvester_free_move_used"):
            await interaction.followup.send("You already moved a Harvester for free this Explore action.",
                                            ephemeral=True)
            return
        if not MoveButtons.getListOfUnpinnedShipTiles(game, player, "sb"):
            await interaction.followup.send("Your Harvester is pinned and cannot move.", ephemeral=True)
            return
        player["harvester_free_move_used"] = True
        game.update()
        await MoveButtons.startMove(game, player, interaction, "startMove_0_sb", True)

    @staticmethod
    async def moveFrom(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        originT = buttonID.split("_")[1]
        moveCount = buttonID.split("_")[2]
        nested = "herRegroup" in buttonID
        phase = buttonID.rsplit("_", 1)[1] if nested else ""
        ship_filter = "all" if nested else (buttonID.split("_")[3] if len(buttonID.split("_")) > 3 else "all")
        view = MoveButtons.buildShipTypeView(game, player, originT, moveCount, ship_filter, nested, phase)
        if nested:
            MoveButtons.addRegroupBackButton(view, player, phase)
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']}, select the ship"
                                       f" you would like to move from {game.get_tile_label(originT)}", view=view)

    @staticmethod
    def getTilesInRange(game: GamestateHelper, player, origin: str, shipRange: int, jumpDrivePresent: int):
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
        tile_map = game.gamestate["board"]
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        techsResearched = player_helper.getTechs()
        wormHoleGen = "wog" in techsResearched
        if "shrine_in_storage" in player:
            if all(player_helper.stats["shrine_in_storage"][n] == 0 for n in [0, 1, 2]):
                wormHoleGen = True
        jumpDrive = False
        if jumpDrivePresent == 1:
            jumpDrive = True

        def recursive_search(pos, distance, visited, jumpDriveAvailable):
            if distance > shipRange:
                return
            if pos not in tile_map:
                return
            if "player_ships" not in tile_map[pos]:
                return
            visited.add(pos)
            player_ships = tile_map[pos]["player_ships"][:]
            player_ships.append(f"{player['color']}-cruiser")  # adding phantom ship so I can reuse a method
            if not ExploreButtons.doesPlayerHaveUnpinnedShips(player, player_ships, game, pos):
                return

            candidates = tile_map[pos].get("adjacent") or configs.get(pos)[0].split(",")
            for adjTile in candidates:
                if ("nebula_internal" in tile_map.get(adjTile, {})
                        and adjTile not in tile_map[pos].get("nebula_internal", [])):
                    parent = adjTile
                    subsectors = [parent, *tile_map[parent].get("nebula_internal", [])]
                    border_subsector = next((subsector for subsector in subsectors
                                             if pos in tile_map[subsector].get("adjacent", [])), None)
                    if border_subsector is not None:
                        adjTile = border_subsector
                    else:
                        edge_source = tile_map[pos].get("nebula_parent", pos)
                        edge = configs.get(edge_source)[0].split(",").index(adjTile)
                        adjTile = game.nebula_subsector_for_edge(adjTile, (edge + 3) % 6)
                if adjTile in tile_map and InfluenceButtons.areTwoTilesAdjacent(game, pos, adjTile,
                                                                                configs, wormHoleGen):
                    recursive_search(adjTile, distance + 1, visited, jumpDriveAvailable)
                elif jumpDriveAvailable and "wormholes" in tile_map.get(adjTile, []):
                    recursive_search(adjTile, distance + 1, visited, False)
            if tile_map[pos].get("warp", 0) == 1:
                for tile in tile_map:
                    if tile_map[tile].get("warp", 0) == 1:
                        recursive_search(tile, distance + 1, visited, jumpDriveAvailable)

        visited_tiles = set()
        recursive_search(origin, 0, visited_tiles, jumpDrive)
        return visited_tiles

    @staticmethod
    async def moveThisShip(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        queue_remaining = MoveButtons.getMoveQueueCount(buttonID)
        is_queued_move = MoveButtons.hasMoveQueueMarker(buttonID)
        buttonID = MoveButtons.withoutMoveQueueCount(buttonID)
        view = View()
        originT = buttonID.split("_")[1]
        shipType = buttonID.split("_")[2]
        moveCount = buttonID.split("_")[3]
        nested = "herRegroup" in buttonID
        phase = buttonID.rsplit("_", 1)[1] if nested else ""
        ship_filter = "all" if nested else (buttonID.split("_")[4] if len(buttonID.split("_")) > 4 else "all")
        suffix = f"_herRegroup_{phase}" if nested else f"_{ship_filter}"
        ship = PlayerShip(player, shipType)
        shipRange = ship.getRange()
        movable = MoveButtons.getMovableShipsOfType(game, player, originT, shipType)
        max_selected = min(movable, MoveButtons.getRemainingMoveActivations(player, int(moveCount), nested))
        if not is_queued_move and max_selected > 1:
            view = MoveButtons.buildMoveQueueView(player, originT, shipType, moveCount, 1, max_selected, suffix)
            await interaction.message.edit(content=(f"{player['player_name']}, select how many {shipType}s to move "
                                                   f"from {game.get_tile_label(originT)} "
                                                   f"({max_selected} activations available)."), view=view)
            return
        if not movable or shipRange <= 0:
            await interaction.message.delete()
            if is_queued_move:
                await interaction.channel.send(f"The remaining {shipType}s can no longer move from "
                                                f"{game.get_tile_label(originT)}.")
                await MoveButtons.sendMoveContinuation(player, interaction, max(0, int(moveCount) - 1))
            else:
                await interaction.channel.send(f"No {shipType}s can move from {game.get_tile_label(originT)} right now.")
            return
        tiles = MoveButtons.getTilesInRange(game, player, originT, shipRange, ship.getJumpDrive())
        if originT in tiles:
            tiles.remove(originT)
        view2 = View()
        count = 0
        for destination in tiles:
            if count < 24:
                view.add_item(Button(label=game.get_tile_label(destination), style=discord.ButtonStyle.blurple,
                                     custom_id=(f"FCID{player['color']}_moveTo_{originT}"
                                                f"_{shipType}_{destination}_{moveCount}"
                                                f"_q{queue_remaining}{suffix}")))
            else:
                view2.add_item(Button(label=game.get_tile_label(destination), style=discord.ButtonStyle.blurple,
                                      custom_id=(f"FCID{player['color']}_moveTo_{originT}"
                                                 f"_{shipType}_{destination}_{moveCount}"
                                                 f"_q{queue_remaining}{suffix}")))
            count += 1
        if nested:
            MoveButtons.addRegroupBackButton(view, player, phase)
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))

        await interaction.message.delete()
        await interaction.channel.send(f"{player['player_name']}, select the tile you would like to move "
                                       f"a {shipType} from {game.get_tile_label(originT)} to.", view=view)
        if count > 24:
            await interaction.channel.send("Additional Options", view=view2)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) < 15 and len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))


    

    @staticmethod
    async def moveTo(game: GamestateHelper, player, interaction: discord.Interaction,
                     buttonID: str, player_helper: PlayerHelper):
        queue_remaining = MoveButtons.getMoveQueueCount(buttonID)
        originT = buttonID.split("_")[1]
        shipType = buttonID.split("_")[2]
        destination = buttonID.split("_")[3]
        moveCount = int(buttonID.split("_")[4])
        player_color = player["color"]
        shipName = f"{player_color}-{game.getShipShortName(shipType)}"
        tile_ships = game.gamestate["board"][destination]["player_ships"]
        game.remove_units([shipName], originT)
        game.add_units([shipName], destination)
        game.fixshipsOrder(destination)
        drawing = DrawHelper(game.gamestate)
        await interaction.channel.send(f"{player['player_name']} Moved a {shipType} from "
                                       f"{game.get_tile_label(originT)} to {game.get_tile_label(destination)}.",
                                       file=await asyncio.to_thread(drawing.board_tile_image_file, destination))
        owner = game.gamestate["board"][destination]["owner"]
        if tile_ships:
            p2_color = tile_ships[0].split("-")[0]
        if (owner != 0 and isinstance(owner, str) and owner != player_color
                and not game.areAllied(player_color, owner)):
            p2 = game.getPlayerObjectFromColor(owner)
            player_helper2 = PlayerHelper(game.get_player_from_color(owner), p2)
            player_helper2.permanentlyPassTurn(False)
            game.update_player(player_helper2)
            await interaction.channel.send(p2["player_name"] + " your system has been invaded")
        if (tile_ships and owner == 0 and p2_color != "ai" and p2_color != player_color
                and not game.areAllied(player_color, p2_color)):
            p2 = game.getPlayerObjectFromColor(p2_color)
            player_helper2 = PlayerHelper(game.get_player_from_color(p2_color), p2)
            player_helper2.permanentlyPassTurn(False)
            game.update_player(player_helper2)
            await interaction.channel.send(p2["player_name"] + f" another player has entered an airspace you occupy")
        if "bh" in game.gamestate["board"][destination].get("type", ""):
            bhtype = game.gamestate["board"][destination]["type"]
            random_number = random.randint(1, 6)
            roundNum = 1
            game.remove_units([shipName], destination)
            shipModel = PlayerShip(player, shipName.split("-")[1])
            if "roundNum" in game.gamestate:
                roundNum = game.gamestate["roundNum"]
            location = " any inner (first ring) sector"
            if "border" in game.gamestate["board"][destination]["type"]:
                location = " any tile with a wormhole facing an empty space."
            msg = f"This is a black hole tile, and the ship rolled a {random_number}. That means it will "
            if random_number == 1 or random_number == 6:
                msg += " take one damage and "
                if shipModel.hull > 0:
                    msg += f"then teleport to {location}."
                else:
                    msg += "thus die due to lack of hull."
            elif random_number == 2 or random_number == 3:
                if roundNum == 8:
                    msg += "die as it would return after the game ends."
                else:
                    msg += f"go away for now and return next round on one of your actions, teleporting to {location}."
                    if "blackHoleReturn" not in player_helper.stats:
                        player_helper.stats["blackHoleReturn"] = []
                    player_helper.stats["blackHoleReturn"].append(f"{bhtype}_{shipName}_{roundNum + 1}")
                    game.update_player(player_helper)
            else:
                if roundNum > 6:
                    msg += "die as it would return after the game ends."
                else:
                    msg += "go away for now and return in 2 rounds on one of your actions, teleporting to {location}."
                    if "blackHoleReturn" not in player_helper.stats:
                        player_helper.stats["blackHoleReturn"] = []
                    player_helper.stats["blackHoleReturn"].append(f"{bhtype}_{shipName}_{roundNum + 2}")
                    game.update_player(player_helper)
            await interaction.channel.send(msg)

            if random_number == 1 or random_number == 6:
                if "teleport" in msg:
                    await interaction.channel.send(player["player_name"] + " Select a tile to return the ship to",
                                                   view=BlackHoleButtons.findBlackHoleOptions(game, player, shipName,
                                                                                              bhtype, "damage"))
            if game.gamestate["board"][destination]["disctile"] > 0:
                await DiscoveryTileButtons.exploreDiscoveryTile(game, destination, interaction, player)

        nested = "herRegroup" in buttonID
        if nested:
            player_helper.stats["herCrossUsed"] = True
        elif moveCount == 1:
            if player.get("herRaidCharged"):
                player_helper.stats.pop("herRaidCharged", None)
            else:
                player_helper.spend_influence_on_action("move")
        if nested or moveCount == 1:
            game.update_player(player_helper)
        player_helper.specifyDetailsOfAction(f"Moved a {shipType} from {originT} to {destination}.")
        game.update_player(player_helper)
        if nested:
            phase = buttonID.rsplit("_", 1)[1]
            from Buttons.Build import BuildButtons
            if phase == "before":
                await interaction.message.delete()
                await BuildButtons.startBuild(game, player, interaction, "startBuild2_herRegroupResume",
                                              player_helper)
            elif BuildButtons.buildsLeft(player_helper.stats, player["build_apt"]) > 0:
                # Regroup adds the move to the Build action; a finished build must not end it.
                await interaction.message.delete()
                await BuildButtons.startBuild(game, player, interaction,
                                              "startBuild2_herRegroupResumeAfter", player_helper)
            else:
                from Buttons.Turn import TurnButtons
                await TurnButtons.finishAction(player, game, interaction, player_helper)
            return
        queue_suffix = ""
        if queue_remaining:
            if nested:
                queue_suffix = f"_herRegroup_{phase}"
            else:
                ship_filter = buttonID.rsplit("_q", 1)[-1]
                ship_filter = ship_filter.rsplit("_", 1)[-1]
                queue_suffix = f"_{ship_filter}" if ship_filter in ("all", "sb") else "_all"
        await interaction.message.delete()
        await MoveButtons.sendMoveContinuation(player, interaction, moveCount, queue_remaining,
                                               originT, shipType, queue_suffix, game.get_tile_label(destination),
                                               destination)

    @staticmethod
    async def sendMoveContinuation(player, interaction: discord.Interaction, moveCount: int,
                                   queue_remaining: int = 0, origin: str = "", shipType: str = "",
                                   suffix: str = "", destination_label: str = "", destination: str = ""):
        view = View()
        if (moveCount > 0 and not player.get("passed") and FactionData.has(player, "raid")
                and not player.get("pulsarMove") and not player.get("herCrossUsed")
                and moveCount <= player["move_apt"]):
            view.add_item(Button(label="Build Activation (1)", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_herRaidBuild_{moveCount + 1}"))
        if moveCount > 0 and player["move_apt"] > moveCount and not player.get("passed"):
            view.add_item(Button(label="Move an additional ship", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_startMove_{moveCount + 1}"))
        if (queue_remaining > 0 and moveCount > 0 and player["move_apt"] > moveCount
                and not player.get("passed")):
            view.add_item(Button(label=f"Move next queued {shipType} to {destination_label}"
                                       f" ({queue_remaining} left)",
                                 style=discord.ButtonStyle.green,
                                 custom_id=(f"FCID{player['color']}_moveQueueContinue_{origin}_{shipType}"
                                            f"_{destination}_{moveCount + 1}_{queue_remaining}{suffix}")))
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        moves_left = max(0, player["move_apt"] - moveCount)
        await interaction.channel.send(f"{interaction.user.mention} you may move an additional ship"
                                       f" if you still have move activations ({moves_left} left),"
                                       " or end your action.", view=view)
