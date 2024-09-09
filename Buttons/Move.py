import discord
from discord.ui import View
from Buttons.Explore import ExploreButtons
from Buttons.Influence import InfluenceButtons
from Buttons.Turn import TurnButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button
from jproperties import Properties

from helpers.ShipHelper import PlayerShip

class MoveButtons:
    @staticmethod
    def getListOfUnpinnedShipTiles(game:GamestateHelper, player):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if ("player_ships" in tile_map[tile] and ExploreButtons.doesPlayerHaveUnpinnedShips(player,tile_map[tile]["player_ships"])):
                tiles.append(tile)
        return tiles
    @staticmethod
    async def startMove(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str, button : bool):
        moveCount = 1
        if "_" in buttonID:
            moveCount = buttonID.split("_")[1]
        view = View()
        for tile in MoveButtons.getListOfUnpinnedShipTiles(game, player):
            view.add_item(Button(label=tile.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_moveFrom_{tile}_{moveCount}"))
        if button:
            await interaction.message.delete()
        await interaction.response.send_message( f"{interaction.user.mention} Select the tile you would like to move from", view=view)

    @staticmethod
    async def moveFrom(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        view = View()
        originT = buttonID.split("_")[1]
        moveCount = buttonID.split("_")[2]
        shipTypes = ["interceptor","cruiser","dreadnought"]
        for shipType in shipTypes:
            player_color = player["color"]
            if f"{player_color}-{game.getShipShortName(shipType)}" in game.get_gamestate()["board"][originT]["player_ships"]:
                view.add_item(Button(label=shipType.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_moveThisShip_{originT}_{shipType}_{moveCount}"))
        await interaction.message.delete()
        await interaction.response.send_message( f"{interaction.user.mention} Select the ship you would like to move from {originT}", view=view)
    @staticmethod
    def getTilesInRange(game: GamestateHelper, player, origin:str, shipRange : int):
        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        tile_map = game.get_gamestate()["board"]

        def recursive_search(pos, distance, visited):
            if distance >  shipRange:
                return
            if pos in visited:
                return
            visited.add(pos)
            player_ships = tile_map[pos]["player_ships"]
            player_ships.append(f"{player['color']}-cruiser") #adding phantom ship so I can reuse a method
            if not ExploreButtons.doesPlayerHaveUnpinnedShips(player, player_ships):
                return

            for adjTile in configs.get(pos)[0].split(","):
                if InfluenceButtons.areTwoTilesAdjacent(game, pos, adjTile, configs):
                    recursive_search(adjTile, distance + 1, visited)

        visited_tiles = set()
        recursive_search(origin, 0, visited_tiles)
        return visited_tiles
    @staticmethod
    async def moveThisShip(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        view = View()
        originT = buttonID.split("_")[1]
        shipType = buttonID.split("_")[2]
        moveCount = buttonID.split("_")[3]
        ship = PlayerShip(player, shipType)
        shipRange = ship.getRange()
        for destination in MoveButtons.getTilesInRange(game, player, originT, shipRange):
            view.add_item(Button(label=destination, style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_moveTo_{originT}_{shipType}_{destination}_{moveCount}"))
        await interaction.message.delete()
        await interaction.response.send_message( f"{interaction.user.mention} Select the tile you would like to move a {shipType} from {originT} to", view=view)
    @staticmethod
    async def moveTo(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str, player_helper:PlayerHelper, bot):
        originT = buttonID.split("_")[1]
        shipType = buttonID.split("_")[2]
        destination = buttonID.split("_")[3]
        moveCount = int(buttonID.split("_")[4])
        player_color = player["color"]
        shipName = f"{player_color}-{game.getShipShortName(shipType)}"
        game.remove_units([shipName],originT)
        game.add_units([shipName],destination)
        drawing = DrawHelper(game.gamestate)
        await interaction.message.delete()
        await interaction.channel.send( f"{interaction.user.mention} Moved a {shipType} from {originT} to {destination}.", file=drawing.board_tile_image_file(destination))
        if moveCount == 1:
            player_helper.spend_influence_on_action("move")
            game.update_player(player_helper)
        if player["move_apt"] > moveCount:
            view = View()
            view.add_item(Button(label="Move an additional ship", style=discord.ButtonStyle.green, custom_id=f"FCID{player['color']}_startMove_"+str(moveCount+1)))
            view.add_item(Button(label="End Turn", style=discord.ButtonStyle.red, custom_id=f"FCID{player['color']}_endTurn"))
            await interaction.response.send_message(f"{interaction.user.mention} you can move an additional ship or end turn.", view=view)
        else:
            if player["move_apt"] == moveCount:
                await TurnButtons.endTurn(player, game, interaction, bot)

