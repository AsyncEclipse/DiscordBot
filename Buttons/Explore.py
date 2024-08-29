import json
import discord
from discord.ui import View
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
            if ("owner" in tile_map[tile] and tile_map[tile]["owner"] == player["color"]) or ("player_ships" in tile_map[tile] and ExploreButtons.doesPlayerHaveUnpinnedShips(player,tile_map[tile]["player_ships"])):
                tiles.append(tile)
        return tiles
    @staticmethod
    def doesPlayerHaveUnpinnedShips(player, playerShips):
        playerShipsCount = 0
        opponentShips = 0
        if len(playerShips) == 0:
            return False
        for ship in playerShips:
            if player["color"] in ship:
                playerShipsCount = playerShipsCount +1
            else:
                opponentShips = opponentShips +1
        return playerShipsCount > opponentShips

    @staticmethod
    async def startExplore(game: GamestateHelper, player, player_helper: PlayerHelper, interaction: discord.Interaction, buttonID:str):
        if "2" not in buttonID:
            player_helper.spend_influence_on_action("explore")
        game.update_player(player_helper)
        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        view = View()
        tilesViewed = []
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        for tile in playerTiles:
            for index, adjTile in enumerate(configs.get(tile)[0].split(",")):
                tile_orientation_index = (index + 6 + int(int(game.get_gamestate()["board"][tile]["orientation"]) / 60)) % 6
                if (
                    adjTile not in tilesViewed and
                    tile_orientation_index in game.get_gamestate()["board"][tile]["wormholes"] and
                    "back" in game.get_gamestate()["board"][str(adjTile)]["sector"]
                ):
                    tilesViewed.append(adjTile)
                    view.add_item(Button(label=str(adjTile), style=discord.ButtonStyle.primary, custom_id="exploreTile_" + str(adjTile)))
        await interaction.response.send_message(f"{interaction.user.mention} select the tile you would like to explore",view=view)
        if player["explore_apt"] > 1:
            view2 = View()
            view2.add_item(Button(label="Start 2nd explore", style=discord.ButtonStyle.danger, custom_id="startExplore2"))
            view2.add_item(Button(label="Decline 2nd Explore", style=discord.ButtonStyle.danger, custom_id="deleteMsg"))
            await interaction.channel.send(f"{interaction.user.mention} after exploring the first time, you can use this button to explore again.", view=view2)
        view = View()
        view.add_item(Button(label="End Turn", style=discord.ButtonStyle.danger, custom_id="endTurn"))
        await interaction.channel.send(f"{interaction.user.mention} when you're finished resolving your action, you may end turn with this button.", view=view)
        await interaction.message.delete()
    @staticmethod
    async def exploreTile(game: GamestateHelper, player, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        drawing = DrawHelper(game.gamestate)
        view = View()
        player = game.get_player(interaction.user.id)
        msg = interaction.data["custom_id"].split("_")
        if len(msg) > 2:
            tileID = msg[2]
            game.tile_discard(msg[3])
        else:
            tileID = game.tile_draw(msg[1])
            if player["name"]=="Descendants of Draco":
                tileID2 = game.tile_draw(msg[1])
                image = drawing.base_tile_image(tileID)
                image2 = drawing.base_tile_image(tileID2)
                await interaction.followup.send("Option #1",file=drawing.show_single_tile(image), ephemeral = True)
                await interaction.followup.send("Option #2",file=drawing.show_single_tile(image2), ephemeral = True)
                view.add_item(Button(label="Option #1",style=discord.ButtonStyle.success, custom_id=f"exploreTile_{msg[1]}_{tileID}_{tileID2}"))
                view.add_item(Button(label="Option #2",style=discord.ButtonStyle.success, custom_id=f"exploreTile_{msg[1]}_{tileID2}_{tileID}"))
                await interaction.channel.send(f"{interaction.user.mention} select the tile you wish to resolve.",view=view)
                await interaction.message.delete()
                return
        image = drawing.base_tile_image(tileID)
        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        wormholeStringsViewed = []
        with open("data/sectors.json") as f:
            tile_data = json.load(f)
        tile = tile_data[tileID]
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        count = 1
        for x in range(6):
            rotation = x * 60
            wormholeString = ''.join(str((wormhole + x) % 6) for wormhole in tile["wormholes"])
            if wormholeString in wormholeStringsViewed: continue
            wormholeStringsViewed.append(wormholeString)
            rotationWorks = False
            for index, adjTile in enumerate(configs.get(msg[1])[0].split(",")):
                tile_orientation_index = (index + 6 + x) % 6
                if adjTile in playerTiles and tile_orientation_index in tile["wormholes"]:
                    rotationWorks = True
                    break
            if rotationWorks:
                context = Image.new("RGBA", (345*3, 300*3), (255, 255, 255, 0))
                image = drawing.base_tile_image_with_rotation(tileID,rotation,tile["wormholes"])
                context.paste(image,(345, 300),mask=image)
                coords = [(345, 0), (605, 150),(605, 450),(345, 600), (85, 450),(85, 150)]
                for index, adjTile in enumerate(configs.get(msg[1])[0].split(",")):
                    if adjTile in game.get_gamestate()["board"]:
                        adjTileImage = drawing.board_tile_image(adjTile)
                        context.paste(adjTileImage,coords[index],mask=adjTileImage)
                font = ImageFont.truetype("images/resources/arial.ttf", size=50)
                ImageDraw.Draw(context).text((10, 10), f"Option #{count}", (255, 255, 255), font=font,
                                stroke_width=2, stroke_fill=(0, 0, 0))
                bytes = BytesIO()
                context.save(bytes, format="PNG")
                bytes.seek(0)
                file = discord.File(bytes, filename="tile_image.png")
                view.add_item(Button(label="Option #"+str(count),style=discord.ButtonStyle.success, custom_id=f"placeTile_{msg[1]}_{tileID}_{rotation}"))
                count += 1
                await interaction.followup.send(file=file, ephemeral = True)

        view.add_item(Button(label="Discard Tile",style=discord.ButtonStyle.danger, custom_id=f"discardTile_{tileID}"))
        await interaction.followup.send(f"{interaction.user.mention} select the orientation you prefer or discard the tile.",view=view)
        await interaction.message.delete()
    @staticmethod
    async def placeTile(game: GamestateHelper, interaction: discord.Interaction, player):
        await interaction.response.defer(thinking=True)
        msg = interaction.data["custom_id"].split("_")
        game.add_tile(msg[1], int(msg[3]), msg[2])
        await interaction.followup.send(f"Tile added to position {msg[1]}")
        if game.get_gamestate()["board"][msg[1]]["ancient"] == 0 or player["name"]=="Descendants of Draco":
            view = View()
            view.add_item(Button(label="Place Influence", style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_addInfluenceFinish_"+msg[1]))
            view.add_item(Button(label="Decline Influence Placement", style=discord.ButtonStyle.danger, custom_id="deleteMsg"))
            await interaction.channel.send(f"{interaction.user.mention} choose whether or not to place influence in the tile", view = view)
            if game.get_gamestate()["board"][msg[1]]["ancient"] == 0 and game.get_gamestate()["board"][msg[1]]["disctile"] > 0:
                await DiscoveryTileButtons.exploreDiscoveryTile(game, msg[1],interaction)
        await interaction.message.delete()
    @staticmethod
    async def discardTile(game: GamestateHelper, interaction: discord.Interaction):
        msg = interaction.data["custom_id"].split("_")
        game.tile_discard(msg[2])
        await interaction.response.send_message("Tile discarded")
        await interaction.message.delete()