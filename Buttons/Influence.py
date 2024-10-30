import asyncio
import discord
from discord.ui import View
from Buttons.Explore import ExploreButtons
from Buttons.Population import PopulationButtons
from Buttons.Turn import TurnButtons
from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button
from jproperties import Properties

class InfluenceButtons:

    @staticmethod
    def areTwoTilesAdjacent(game: GamestateHelper, tile1, tile2, configs, wormholeGen: bool):

        def is_adjacent(tile_a, tile_b):
            for index, adjTile in enumerate(configs.get(tile_a)[0].split(",")):
                if tile_a in game.gamestate["board"]:
                    tile_orientation_index = (index + 6 + int(int(game.gamestate["board"][tile_a]["orientation"]) / 60)) % 6
                    if adjTile == tile_b and "wormholes" in game.gamestate["board"][tile_a] and tile_orientation_index in game.gamestate["board"][tile_a]["wormholes"]:
                        return True
            if tile_a in game.gamestate["board"] and tile_b in game.gamestate["board"]:
                if "warp" in game.gamestate["board"][tile_a] and game.gamestate["board"][tile_a]["warp"] == 1:
                    if "warp" in game.gamestate["board"][tile_b] and game.gamestate["board"][tile_b]["warp"] == 1:
                        return True
            return False

        if wormholeGen:
            return is_adjacent(tile1, tile2) or is_adjacent(tile2, tile1)
        else:
            return is_adjacent(tile1, tile2) and is_adjacent(tile2, tile1)

    @staticmethod
    def getTilesToInfluence(game: GamestateHelper, player):
        configs = Properties()
        with open("data/tileAdjacencies.properties", "rb") as f:
            configs.load(f)
        tilesViewed = []
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]),player)
        techsResearched = player_helper.getTechs()
        wormHoleGen = "wog" in techsResearched
        tilesToInfluence = []
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)
        for tile in playerTiles:
            for adjTile in configs.get(tile)[0].split(","):
                if adjTile not in tilesViewed and InfluenceButtons.areTwoTilesAdjacent(game, tile, adjTile, configs, wormHoleGen):
                    tilesViewed.append(adjTile)
                    playerShips =game.get_gamestate()["board"][adjTile]["player_ships"]
                    playerShips.append(player["color"])
                    if "owner" in game.get_gamestate()["board"][adjTile] and game.get_gamestate()["board"][adjTile]["owner"]==0 and ExploreButtons.doesPlayerHaveUnpinnedShips(player, playerShips,game):
                        tilesToInfluence.append(adjTile)
            if tile not in tilesViewed:
                    tilesViewed.append(tile)
                    playerShips =game.get_gamestate()["board"][tile]["player_ships"]
                    playerShips.append(player["color"])
                    if "owner" in game.get_gamestate()["board"][tile] and game.get_gamestate()["board"][tile]["owner"]==0 and ExploreButtons.doesPlayerHaveUnpinnedShips(player, playerShips,game):
                        if any("ai" in s for s in playerShips):
                            if any("anc" in s for s in playerShips):
                                if "Draco" not in player["name"]:
                                    continue
                            else:
                                    continue
                        tilesToInfluence.append(tile)
        return tilesToInfluence
    @staticmethod
    async def startInfluence(game: GamestateHelper, p1, interaction: discord.Interaction):
        view = View()
        view.add_item(Button(label=f"Remove Influence", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_removeInfluenceStart"))
        if len(InfluenceButtons.getTilesToInfluence(game,p1)) > 0:
            view.add_item(Button(label=f"Add  Influence", style=discord.ButtonStyle.green, custom_id=f"FCID{p1['color']}_addInfluenceStart"))
        view.add_item(Button(label="Refresh 2 Colony Ships", style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1['color']}_refreshPopShips"))
        view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_startPopDrop"))
        view.add_item(Button(label="Conclude Influence Action", style=discord.ButtonStyle.red, custom_id=f"FCID{p1['color']}_finishInfluenceAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray, custom_id=f"FCID{p1['color']}_restartTurn"))
        await interaction.message.delete()
        await interaction.channel.send( f"{interaction.user.mention} you can remove up to two disks and influence up to 2 spaces. You can also refresh 2 colony ships or put down population at any time during this resolution", view=view)

    @staticmethod
    async def addInfluenceStart(game: GamestateHelper, p1, interaction: discord.Interaction):
        view = View()
        tiles = InfluenceButtons.getTilesToInfluence(game, p1)
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1['color']}_addInfluenceFinish_"+tile))
        await interaction.channel.send( f"{interaction.user.mention} choose the tile you would like to influence", view=view)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=drawing.mergeLocationsFile(tiles), ephemeral=True))
    @staticmethod
    async def addInfluenceFinish(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID:str):
        tileLoc = buttonID.split("_")[1]
        if game.get_gamestate()["board"][tileLoc]["owner"] != 0:
            await interaction.channel.send( f"Someone else controls {tileLoc}. Remove their control via valid means first")
            return
        game.add_control(p1["color"],tileLoc)
        await interaction.channel.send( f"{interaction.user.mention} acquired control of "+tileLoc)
        await interaction.message.delete()

    @staticmethod
    async def refreshPopShips(game: GamestateHelper, player, interaction: discord.Interaction, buttonID:str):
        numShips = game.refresh_two_colony_ships(game.get_player_from_color(player["color"]))
        view = View.from_message(interaction.message)
        for button in view.children:
            if buttonID in button.custom_id:
                view.remove_item(button)
        await interaction.followup.send( f"{interaction.user.mention} now has "+str(numShips)+" colony ships "
                                                                                               "available to use")
        await interaction.message.edit(view=view)

    @staticmethod
    async def finishInfluenceAction(game: GamestateHelper, player, interaction: discord.Interaction, player_helper:PlayerHelper):
        player_helper.spend_influence_on_action("influence")
        game.update_player(player_helper)
        await TurnButtons.finishAction(player, game, interaction)

    @staticmethod
    async def removeInfluenceStart(game: GamestateHelper, player, interaction: discord.Interaction):
        view = View()
        tiles = game.get_owned_tiles(player)
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple, custom_id=f"FCID{player['color']}_removeInfluenceFinish_"+tile+"_normal"))
        await interaction.channel.send( f"{interaction.user.mention} choose the tile you would like to remove influence from", view=view)

        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=drawing.mergeLocationsFile(tiles), ephemeral=True))
    @staticmethod
    async def removeInfluenceFinish(game: GamestateHelper, interaction: discord.Interaction, buttonID:str, delete:bool):
        tileLoc = buttonID.split("_")[1]
        owner = game.get_gamestate()["board"][tileLoc]["owner"]
        if owner == 0:
            await interaction.channel.send("No owner found of "+tileLoc)
            return
        p1 = game.getPlayerObjectFromColor(owner)
        graveYard = buttonID.split("_")[2] == "graveYard"
        game.remove_control(p1["color"],tileLoc)
        await interaction.channel.send( f"{p1['player_name']} lost control of "+tileLoc)
        for pop in PopulationButtons.findFullPopulation(game, tileLoc):
            neutralCubes, orbitalCubes = game.remove_pop([pop+"_pop"],tileLoc,game.get_player_from_color(p1["color"]), graveYard)
            if neutralCubes > 0:
                view=View()
                planetTypes = ["money","science","material"]
                for planetT in planetTypes:
                    if p1[planetT+"_pop_cubes"] < 12:
                        view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1['color']}_addCubeToTrack_"+planetT))
                await interaction.channel.send( f"A neutral cube was removed, please tell the bot what track you want it to go on", view=view)
            if orbitalCubes > 0:
                view=View()
                planetTypes = ["money","science"]
                for planetT in planetTypes:
                    if p1[planetT+"_pop_cubes"] < 12:
                        view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple, custom_id=f"FCID{p1['color']}_addCubeToTrack_"+planetT))
                await interaction.channel.send( f"An orbital cube was removed, please tell the bot what track you want it to go on", view=view)
            else:
                await interaction.channel.send( f"{p1['username']} Removed 1 "+pop.replace("adv","")+" population")
        if delete:
            await interaction.message.delete()
    @staticmethod
    async def addCubeToTrack(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID:str):
        pop = buttonID.split("_")[1]
        cubes = p1[pop+"_pop_cubes"]
        if cubes > 12:
            await interaction.channel.send("The "+pop + " track is full. Cannot add more cubes to this track")
            return
        game.remove_pop([pop+"_pop"],"dummy",game.get_player_from_color(p1["color"]), False)
        await interaction.channel.send( f"{p1['player_name']} Added 1 "+pop.replace('adv','')+" population back to its track")
        await interaction.message.delete()