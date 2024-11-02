import json
import discord
from Buttons.DiscoveryTile import DiscoveryTileButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties

class ExploreButtons:
    @staticmethod
    def getListOfTilesPlayerIsIn(game, player):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if ("owner" in tile_map[tile] and tile_map[tile]["owner"] == player["color"]) or ("player_ships" in tile_map[tile] and ExploreButtons.doesPlayerHaveUnpinnedShips(player,tile_map[tile]["player_ships"],game)):
                tiles.append(tile)
        return tiles
    @staticmethod
    def doesPlayerHaveUnpinnedShips(player, playerShips, game):
        player_helper = PlayerHelper(game.get_player_from_color(player['color']), player)
        playerShipsCount = 0
        opponentShips = 0
        if len(playerShips) == 0:
            return False
        for ship in playerShips:
            if "orb" not in ship and "mon" not in ship:
                if player["color"] in ship:
                    playerShipsCount = playerShipsCount +1
                else:
                    if "anc" not in ship or "Draco" not in player["name"]:
                        opponentShips = opponentShips +1
                    if "gcds" in ship:
                        opponentShips += 99
        researchedTechs = player_helper.getTechs()
        if "clo" in researchedTechs or "cld" in researchedTechs:
            playerShipsCount = playerShipsCount*2
        return playerShipsCount > opponentShips


    @staticmethod
    def getTilesToExplore(game: GamestateHelper, player):
        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        tilesViewed = []
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        for tile in playerTiles:
            for index, adjTile in enumerate(configs.get(tile)[0].split(",")):
                tile_orientation_index = (index + 6 + int(int(game.get_gamestate()["board"][tile]["orientation"]) / 60)) % 6
                if (
                    adjTile not in tilesViewed and
                    tile_orientation_index in game.get_gamestate()["board"][tile]["wormholes"] and
                    str(adjTile) in game.get_gamestate()["board"] and
                    "sector" in game.get_gamestate()["board"][str(adjTile)] and
                    "back" in game.get_gamestate()["board"][str(adjTile)]["sector"]
                ):
                    if int(adjTile) > 299 and len(game.get_gamestate()[f"tile_deck_300"]) == 0:
                        continue
                    tilesViewed.append(adjTile)
        return tilesViewed
    @staticmethod
    async def startExplore(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonID:str):
        if "2" not in buttonID:
            player_helper.spend_influence_on_action("explore")
            await interaction.channel.send(f"{player['player_name']} is using their turn to explore")
            game.update_player(player_helper)
        else:
            await interaction.channel.send(f"{player['player_name']} is resolving their second explore")
        view = View()
        for tile in ExploreButtons.getTilesToExplore(game, player):
            view.add_item(Button(label=str(tile), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_exploreTile_" + str(tile)))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_restartTurn"))
        await interaction.channel.send(f"{player['player_name']} select the tile you would like to explore",view=view)
        if player["explore_apt"] > 1 and "2" not in buttonID:
            view2 = View()
            view2.add_item(Button(label="Start 2nd explore", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startExplore2"))
            view2.add_item(Button(label="Decline 2nd Explore", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))
            await interaction.channel.send(f"{player['player_name']} after exploring the first time, you can use this button to explore again.", view=view2)
        await interaction.message.delete()
    @staticmethod
    async def exploreTile(game: GamestateHelper, player, interaction: discord.Interaction, customID:str):
        drawing = DrawHelper(game.gamestate)
        view = View()
        player = game.get_player(interaction.user.id)
        msg = customID.split("_")
        position = msg[1]
        if len(msg) > 2:
            tileID = msg[2]
            game.tile_discard(msg[3])
        else:
            tileID = game.tile_draw(msg[1])
            if player["name"]=="Descendants of Draco":
                ring = int(int(msg[1])/100)
                ring  = min(3, ring)
                discard = 0
                if "tile_discard_deck_300" in game.get_gamestate():
                    discard = len(game.gamestate[f"tile_discard_deck_300"])
                if ring != 3 or discard + len(game.gamestate[f"tile_deck_300"]) > 0:
                    tileID2 = game.tile_draw(msg[1])
                    image = drawing.base_tile_image(tileID)
                    image2 = drawing.base_tile_image(tileID2)
                    await interaction.channel.send("Option #1",file=drawing.show_single_tile(image))
                    await interaction.channel.send("Option #2",file=drawing.show_single_tile(image2))
                    view.add_item(Button(label="Option #1",style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_exploreTile_{position}_{tileID}_{tileID2}"))
                    view.add_item(Button(label="Option #2",style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_exploreTile_{position}_{tileID2}_{tileID}"))
                    await interaction.channel.send(f"{player['player_name']} select the tile you wish to resolve.",view=view)
                    await interaction.message.delete()
                    return
        image = drawing.base_tile_image(tileID)
        await interaction.channel.send("Tile explored in position "+position+": Tile "+tileID,file=drawing.show_single_tile(image))
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        view, file = drawing.draw_possible_oritentations(tileID,position,playerTiles, view,player)

        view.add_item(Button(label="Discard Tile",style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_discardTile_{tileID}"))
        await interaction.channel.send(f"{player['player_name']} select the orientation you prefer or discard the tile.",view=view, file=file)
        await interaction.message.delete()
    @staticmethod
    async def placeTile(game: GamestateHelper, interaction: discord.Interaction, player, customID, player_helper):
        msg = customID.split("_")
        game.add_tile(msg[1], int(msg[3]), msg[2])
        player_helper.specifyDetailsOfAction(f"Explored {msg[1]}.")
        view2 = View()
        game.update_player(player_helper)
        await interaction.channel.send(f"Tile added to position {msg[1]}")
        if game.get_gamestate()["board"][msg[1]]["ancient"] == 0 or player["name"]=="Descendants of Draco":
            view = View()
            view.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_addInfluenceFinish_"+msg[1]))
            view.add_item(Button(label="Decline Influence Placement", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_deleteMsg"))
            await interaction.channel.send(f"{player['player_name']} choose whether or not to place influence in the tile."+game.displayPlayerStats(player), view = view)
            if game.get_gamestate()["board"][msg[1]]["ancient"] == 0 and game.get_gamestate()["board"][msg[1]]["disctile"] > 0:
                await DiscoveryTileButtons.exploreDiscoveryTile(game, msg[1],interaction,player)
            view2.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
        else:
            await interaction.channel.send("There are "+str(game.get_gamestate()["board"][msg[1]]["ancient"])+" ancients in this tile, so you will not be able to claim it until you fight and destroy them.")
        
        
        view2.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.channel.send(f"{player['player_name']} when you're finished resolving your action, you may end turn with this button.", view=view2)
        await interaction.message.delete()
    @staticmethod
    async def discardTile(game: GamestateHelper, interaction: discord.Interaction, player, customID:str):
        msg = customID.split("_")
        game.tile_discard(msg[1])
        await interaction.channel.send("Tile discarded")
        view = View()
        view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_startPopDrop"))
        view.add_item(Button(label="Finish Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{player['color']}_finishAction"))
        await interaction.channel.send(f"{player['player_name']} when finished you may resolve your action "
                                           f"with this button.", view=view)
        await interaction.message.delete()