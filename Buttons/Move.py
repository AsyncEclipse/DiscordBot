import asyncio
import random
import discord
from Buttons.BlackHole import BlackHoleButtons
from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
from Buttons.DiscoveryTile import DiscoveryTileButtons
from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from helpers.DrawHelper import DrawHelper
from helpers.EmojiHelper import Emoji
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button
from jproperties import Properties

from helpers.ShipHelper import PlayerShip


class MoveButtons:
    @staticmethod
    def getListOfUnpinnedShipTiles(game: GamestateHelper, player):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if all(["player_ships" in tile_map[tile],
                    ExploreButtons.doesPlayerHaveUnpinnedShips(player, tile_map[tile]["player_ships"], game, tile)]):
                tiles.append(tile)
        return tiles

    @staticmethod
    async def startMove(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str, button: bool):
        moveCount = 1
        if "_" in buttonID:
            moveCount = buttonID.split("_")[1]
        view = View()
        tiles = MoveButtons.getListOfUnpinnedShipTiles(game, player)
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.red,
                                 custom_id=f"FCID{player['color']}_moveFrom_{tile}_{moveCount}"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        if button:
            if moveCount == 1:
                await interaction.channel.send(f"{player['player_name']} is using their turn to move")
            await interaction.message.delete()
        await interaction.channel.send(f"{interaction.user.mention} Select the tile you would like to move from",
                                       view=view)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))

    @staticmethod
    async def moveFrom(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        view = View()
        originT = buttonID.split("_")[1]
        moveCount = buttonID.split("_")[2]
        shipTypes = ["interceptor", "cruiser", "dreadnought"]
        for shipType in shipTypes:
            player_color = player["color"]
            ship = PlayerShip(player, shipType)
            shipRange = ship.getRange()
            shipTest = f"{player_color}-{game.getShipShortName(shipType)}"
            if shipTest in game.get_gamestate()["board"][originT]["player_ships"] and shipRange > 0:
                shipEmoji = Emoji.getEmojiByName(player['color'] + game.getShipShortName(shipType))
                view.add_item(Button(label=f"{shipType.capitalize()} (Range: {shipRange})", emoji=shipEmoji,
                                     style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_moveThisShip_{originT}_{shipType}_{moveCount}"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.message.delete()
        await interaction.channel.send(f"{interaction.user.mention}, select the ship"
                                       f" you would like to move from {originT}", view=view)

    @staticmethod
    def getTilesInRange(game: GamestateHelper, player, origin: str, shipRange: int, jumpDrivePresent: int):
        configs = Properties()
        if game.gamestate.get("5playerhyperlane"):
            with open("data/tileAdjacencies_5p.properties", "rb") as f:
                configs.load(f)
        else:
            with open("data/tileAdjacencies.properties", "rb") as f:
                configs.load(f)
        tile_map = game.get_gamestate()["board"]
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

            for adjTile in configs.get(pos)[0].split(","):
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
        view = View()
        originT = buttonID.split("_")[1]
        shipType = buttonID.split("_")[2]
        moveCount = buttonID.split("_")[3]
        ship = PlayerShip(player, shipType)
        shipRange = ship.getRange()
        tiles = MoveButtons.getTilesInRange(game, player, originT, shipRange, ship.getJumpDrive())
        if originT in tiles:
            tiles.remove(originT)
        view2 = View()
        count = 0
        for destination in tiles:
            if count < 24:
                view.add_item(Button(label=destination, style=discord.ButtonStyle.blurple,
                                     custom_id=(f"FCID{player['color']}_moveTo_{originT}"
                                                f"_{shipType}_{destination}_{moveCount}")))
            else:
                view2.add_item(Button(label=destination, style=discord.ButtonStyle.blurple,
                                      custom_id=(f"FCID{player['color']}_moveTo_{originT}"
                                                 f"_{shipType}_{destination}_{moveCount}")))
            count += 1
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))

        await interaction.message.delete()
        await interaction.channel.send(f"{interaction.user.mention}, select the tile you would like to move "
                                       f"a {shipType} from {originT} to.", view=view)
        if count > 24:
            await interaction.channel.send("Additional Options", view=view2)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) < 15 and len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))

    @staticmethod
    async def moveTo(game: GamestateHelper, player, interaction: discord.Interaction,
                     buttonID: str, player_helper: PlayerHelper):
        originT = buttonID.split("_")[1]
        shipType = buttonID.split("_")[2]
        destination = buttonID.split("_")[3]
        moveCount = int(buttonID.split("_")[4])
        player_color = player["color"]
        shipName = f"{player_color}-{game.getShipShortName(shipType)}"
        game.remove_units([shipName], originT)
        game.add_units([shipName], destination)
        game.fixshipsOrder(destination)
        drawing = DrawHelper(game.gamestate)
        await interaction.channel.send(f"{player['player_name']} Moved a {shipType} from {originT} to {destination}.",
                                       file=await asyncio.to_thread(drawing.board_tile_image_file, destination))
        player_helper.specifyDetailsOfAction(f"Moved a {shipType} from {originT} to {destination}.")
        game.update_player(player_helper)
        owner = game.gamestate["board"][destination]["owner"]
        if owner != 0 and isinstance(owner, str) and owner != player["color"]:
            p2 = game.getPlayerObjectFromColor(owner)
            player_helper2 = PlayerHelper(game.get_player_from_color(owner), p2)
            player_helper2.permanentlyPassTurn(False)
            game.update_player(player_helper2)
            await interaction.channel.send(p2["player_name"] + " your system has been invaded")
        for tile in player["reputation_track"]:
            if isinstance(tile, str) and "-" in tile and "minor" not in tile:
                color = tile.split("-")[2]
                p2 = game.getPlayerObjectFromColor(color)
                broken = False
                if destination in p2["owned_tiles"]:
                    broken = True
                for ship in game.gamestate["board"][destination]["player_ships"]:
                    if "orb" in ship or "mon" in ship:
                        continue
                    if color in ship:
                        broken = True
                if broken:
                    await DiplomaticRelationsButtons.breakRelationsWith(game, player, p2, interaction)
                    game.makeEveryoneNotTraitor()
                    player_helper.setTraitor(True)
                    game.update_player(player_helper)
                    await interaction.channel.send(f"{player['player_name']}, you broke relations with {color}"
                                                   " and now are the Traitor.")
        if "bh" in game.get_gamestate()["board"][destination].get("type", ""):
            bhtype = game.get_gamestate()["board"][destination]["type"]
            random_number = random.randint(1, 6)
            roundNum = 1
            game.remove_units([shipName], destination)
            shipModel = PlayerShip(player, shipName.split("-")[1])
            if "roundNum" in game.gamestate:
                roundNum = game.gamestate["roundNum"]
            location = " any inner (first ring) sector"
            if "border" in game.get_gamestate()["board"][destination]["type"]:
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
            if game.get_gamestate()["board"][destination]["disctile"] > 0:
                await DiscoveryTileButtons.exploreDiscoveryTile(game, destination, interaction, player)

        if moveCount == 1:
            player_helper.spend_influence_on_action("move")
            game.update_player(player_helper)
        view = View()
        await interaction.message.delete()
        if player["move_apt"] > moveCount and not player.get("passed"):
            view.add_item(Button(label="Move an additional ship", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{player['color']}_startMove_{moveCount + 1}"))
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.channel.send(f"{interaction.user.mention} you may move an additional ship"
                                       " if you still have move activations, or end your action.", view=view)
