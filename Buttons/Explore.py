import asyncio
import discord
from Buttons.DiscoveryTile import DiscoveryTileButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from jproperties import Properties


class ExploreButtons:
    @staticmethod
    def getListOfTilesPlayerIsIn(game, player):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            if any([tile_map[tile].get("owner") == player["color"],
                    ExploreButtons.doesPlayerHaveUnpinnedShips(player, tile_map[tile].get("player_ships", []),game, tile)]):
                tiles.append(tile)
        return tiles

    @staticmethod
    def doesPlayerHaveUnpinnedShips(player, playerShips, game, tile):
        player_helper = PlayerHelper(game.get_player_from_color(player['color']), player)
        playerShipsCount = 0
        opponentShips = 0
        if len(playerShips) == 0:
            return False
        for ship in playerShips:
            if "mon" not in ship:
                if player["color"] in ship and "orb" not in ship:
                    playerShipsCount += 1
                else:
                    if "gcds" in ship:
                        opponentShips += 99
                    if "orb" in ship:
                        
                        if game.gamestate["board"][tile]["owner"] != player["color"]:
                            color = game.gamestate["board"][tile]["owner"]
                            if all([game.find_player_faction_name_from_color(color) == "The Exiles",
                                    game.gamestate["board"][tile].get("orbital_pop", [0])[0] == 1]):
                                opponentShips += 1
                        else:
                            color = player["color"]
                            if all([game.find_player_faction_name_from_color(color) == "The Exiles",
                                    game.gamestate["board"][tile].get("orbital_pop", [0])[0] == 1]):
                                playerShipsCount += 1
                    elif "anc" not in ship or "Draco" not in player["name"]:
                        opponentShips = opponentShips + 1
        researchedTechs = player_helper.getTechs()
        if "clo" in researchedTechs or "cld" in researchedTechs:
            playerShipsCount *= 2
        return playerShipsCount > opponentShips

    @staticmethod
    def getTilesToExplore(game: GamestateHelper, player):
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
        tilesViewed = []
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        for tile in playerTiles:
            for index, adjTile in enumerate(configs.get(tile)[0].split(",")):
                tile_orientation_index = (index + int(game.gamestate["board"][tile]["orientation"]) // 60) % 6
                if all([adjTile not in tilesViewed,
                        tile_orientation_index in game.gamestate["board"][tile]["wormholes"],
                        "back" in game.gamestate.get("board", {}).get(str(adjTile), {}).get("sector", [])]):
                    if int(adjTile) > 299 and len(game.gamestate["tile_deck_300"]) == 0:
                        continue
                    tilesViewed.append(adjTile)
        return tilesViewed

    @staticmethod
    async def startExplore(game: GamestateHelper, player, player_helper: PlayerHelper,
                           interaction: discord.Interaction, buttonID: str):
        if "2" not in buttonID:
            player_helper.spend_influence_on_action("explore")
            await interaction.channel.send(f"{player['player_name']} is using their turn to explore")
            game.update_player(player_helper)
        else:
            await interaction.channel.send(f"{player['player_name']} is resolving their second explore")
        view = View()
        for tile in ExploreButtons.getTilesToExplore(game, player):
            view.add_item(Button(label=str(tile), style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_exploreTile_" + str(tile)))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.channel.send(f"{player['player_name']} select the tile you would like to explore",
                                       view=view)
        if player["explore_apt"] > 1 and "2" not in buttonID:
            view2 = View()
            view2.add_item(Button(label="Start 2nd explore", style=discord.ButtonStyle.green,
                                  custom_id=f"FCID{player['color']}_startExplore2"))
            view2.add_item(Button(label="Decline 2nd Explore", style=discord.ButtonStyle.red,
                                  custom_id=f"FCID{player['color']}_deleteMsg"))
            await interaction.channel.send(f"{player['player_name']} after exploring the first time, "
                                           "you may use this button to explore again.", view=view2)
        await interaction.message.delete()

    @staticmethod
    async def exploreTile(game: GamestateHelper, player, interaction: discord.Interaction, customID: str):
        drawing = DrawHelper(game.gamestate)
        view = View()
        player = game.get_player(interaction.user.id,interaction)
        msg = customID.split("_")
        position = msg[1]
        if len(msg) > 2:
            tileID = msg[2]
            game.tile_discard(msg[3])
        else:
            tileID = game.tile_draw(msg[1])
            if player["name"] == "Descendants of Draco":
                ring = min(3, int(msg[1]) // 100)
                discard = 0
                if "tile_discard_deck_300" in game.gamestate:
                    discard = len(game.gamestate["tile_discard_deck_300"])
                if ring != 3 or discard + len(game.gamestate["tile_deck_300"]) > 0:
                    tileID2 = game.tile_draw(msg[1])
                    image = await asyncio.to_thread(drawing.base_tile_image, tileID)
                    image2 = await asyncio.to_thread(drawing.base_tile_image, tileID2)
                    await interaction.channel.send("Option #1",
                                                   file=await asyncio.to_thread(drawing.show_single_tile, image))
                    await interaction.channel.send("Option #2",
                                                   file=await asyncio.to_thread(drawing.show_single_tile, image2))
                    view.add_item(Button(label="Option #1", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{player['color']}_exploreTile_{position}_{tileID}_{tileID2}"))
                    view.add_item(Button(label="Option #2", style=discord.ButtonStyle.green,
                                         custom_id=f"FCID{player['color']}_exploreTile_{position}_{tileID2}_{tileID}"))
                    await interaction.channel.send(f"{player['player_name']} select the tile you wish to resolve.",
                                                   view=view)
                    await interaction.message.delete()
                    return
        image = await asyncio.to_thread(drawing.base_tile_image, tileID)
        file2 = await asyncio.to_thread(drawing.show_single_tile, image)
        await interaction.channel.send(f"Tile explored in position {position}: Tile {tileID}.", file=file2)
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        view, file = await asyncio.to_thread(drawing.draw_possible_oritentations, tileID, position,
                                             playerTiles, view, player)

        view.add_item(Button(label="Discard Tile", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_discardTile_{tileID}"))
        asyncio.create_task(interaction.channel.send(f"{player['player_name']} select the orientation you prefer"
                                                     " or discard the tile.", view=view, file=file))
        await interaction.message.delete()

    @staticmethod
    async def placeTile(game: GamestateHelper, interaction: discord.Interaction, player,
                        customID: str, player_helper: PlayerHelper):
        msg = customID.split("_")
        game.add_tile(msg[1], int(msg[3]), msg[2])
        player_helper.specifyDetailsOfAction(f"Explored {msg[1]}.")
        view2 = View()
        game.update_player(player_helper)
        await interaction.channel.send(f"Tile added to position {msg[1]}")
        if game.gamestate["board"][msg[1]]["ancient"] == 0 or player["name"] == "Descendants of Draco":
            view = View()
            if "bh" in game.gamestate["board"][msg[1]].get("type", ""):
                await interaction.channel.send("This is a black hole tile, "
                                               "so its discovery tile cannot be claimed until a ship moves in, "
                                               "at which point a die will be rolled and it might teleport.")
            else:
                view.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple,
                                     custom_id=f"FCID{player['color']}_addInfluenceFinish_" + msg[1]))
                view.add_item(Button(label="Decline Influence Placement", style=discord.ButtonStyle.red,
                                     custom_id=f"FCID{player['color']}_deleteMsg"))
                await interaction.channel.send(f"{player['player_name']}, choose whether or not"
                                               " to place influence in the tile." + game.displayPlayerStats(player),
                                               view=view)
                if all([game.gamestate["board"][msg[1]]["ancient"] == 0,
                        game.gamestate["board"][msg[1]]["disctile"] > 0]):
                    await DiscoveryTileButtons.exploreDiscoveryTile(game, msg[1], interaction, player)
                
        else:
            ancients = game.gamestate["board"][msg[1]]["ancient"]
            await interaction.channel.send(f"There are {ancients} ancients in this tile, "
                                           "so you will not be able to claim it until you fight and destroy them.")

        view2.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                              custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.channel.send(f"{player['player_name']} when you're finished resolving your action, "
                                       "you proceed to end of turn things with this button.", view=view2)
        await interaction.message.delete()

    @staticmethod
    async def discardTile(game: GamestateHelper, interaction: discord.Interaction, player, customID: str):
        msg = customID.split("_")
        game.tile_discard(msg[1])
        await interaction.channel.send("Tile discarded")
        view = View()
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.channel.send(f"{player['player_name']} when finished you may resolve your action "
                                       f"with this button.", view=view)
        await interaction.message.delete()
