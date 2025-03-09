import asyncio
import discord
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
                if tile_a in game.gamestate["board"] and tile_b in game.gamestate["board"] and adjTile == tile_b:
                    tile_orientation_index = (index + (int(game.gamestate["board"][tile_a]["orientation"]) // 60)) % 6
                    if tile_orientation_index in game.gamestate["board"][tile_a].get("wormholes", []):
                        return True
            if tile_a in game.gamestate["board"] and tile_b in game.gamestate["board"]:
                if game.gamestate["board"][tile_a].get("warp", 0) == 1:
                    if game.gamestate["board"][tile_b].get("warp", 0) == 1:
                        return True
            return False

        if wormholeGen:
            return is_adjacent(tile1, tile2) or is_adjacent(tile2, tile1)
        else:
            return is_adjacent(tile1, tile2) and is_adjacent(tile2, tile1)

    @staticmethod
    def getTilesToInfluence(game: GamestateHelper, player):
        from helpers.CombatHelper import Combat
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
        tile_map = game.gamestate["board"]
        player_helper = PlayerHelper(game.get_player_from_color(player["color"]), player)
        techsResearched = player_helper.getTechs()
        wormHoleGen = "wog" in techsResearched
        if "shrine_in_storage" in player:
            if all(player_helper.stats["shrine_in_storage"][n] == 0 for n in [0, 1, 2]):
                wormHoleGen = True
        tilesToInfluence = []
        playerTiles = InfluenceButtons.getListOfTilesPlayerIsInForInfluence(game, player)
        for tile in playerTiles:
            for adjTile in configs.get(tile)[0].split(","):
                if adjTile not in tilesViewed and InfluenceButtons.areTwoTilesAdjacent(game, tile, adjTile,
                                                                                       configs, wormHoleGen):
                    tilesViewed.append(adjTile)
                    if adjTile not in game.gamestate["board"]:
                        continue
                    if "bh" in game.gamestate["board"][adjTile].get("type", ""):
                        continue
                    if "exploded" in game.gamestate["board"][adjTile].get("type", ""):
                        continue
                    if "player_ships" not in game.gamestate["board"][adjTile]:
                        continue
                    playerShips = game.gamestate["board"][adjTile]["player_ships"][:]
                    playerShips.append(player["color"])
                    if all([game.gamestate["board"][adjTile].get("owner") == 0,
                            ExploreButtons.doesPlayerHaveUnpinnedShips(player, playerShips, game, adjTile), 
                            len(Combat.findPlayersInTile(game, adjTile)) < 2, "ai-grd" not in playerShips]):
                        tilesToInfluence.append(adjTile)
            if tile_map[tile].get("warp", 0) == 1:
                for tile2 in tile_map:
                    if tile2 not in tilesViewed and tile_map[tile2].get("warp", 0) == 1:
                        tilesViewed.append(tile2)
                        if adjTile not in game.gamestate["board"]:
                            continue
                        if "bh" in game.gamestate["board"][tile2].get("type", ""):
                            continue
                        if "exploded" in game.gamestate["board"][tile2].get("type", ""):
                            continue
                        if "player_ships" not in game.gamestate["board"][tile2]:
                            continue
                        playerShips = game.gamestate["board"][tile2]["player_ships"][:]
                        playerShips.append(player["color"])
                        if all([game.gamestate["board"][tile2].get("owner") == 0,
                                ExploreButtons.doesPlayerHaveUnpinnedShips(player, playerShips, game, tile2), 
                                len(Combat.findPlayersInTile(game, tile2)) < 2]):
                            tilesToInfluence.append(tile2)
            if tile not in tilesViewed:
                tilesViewed.append(tile)
                playerShips = game.gamestate["board"][tile]["player_ships"][:]
                playerShips.append(player["color"])
                if all([game.gamestate["board"][tile].get("owner") == 0,
                        ExploreButtons.doesPlayerHaveUnpinnedShips(player, playerShips, game, tile)]):
                    if any("ai" in s for s in playerShips):
                        if any("anc" in s for s in playerShips):
                            if "Draco" not in player["name"]:
                                continue
                        else:
                            continue
                    tilesToInfluence.append(tile)
        return tilesToInfluence

    @staticmethod
    def getListOfTilesPlayerIsInForInfluence(game, player):
        tile_map = game.gamestate["board"]
        tiles = []
        for tile in tile_map:
            if any([tile_map[tile].get("owner") == player["color"],
                    InfluenceButtons.doesPlayerHaveShips(player, tile_map[tile].get("player_ships", []))]):
                tiles.append(tile)
        return tiles
    @staticmethod
    def doesPlayerHaveShips(player, playerShips):
        playerShipsCount = 0
        if len(playerShips) == 0:
            return False
        for ship in playerShips:
            if "mon" not in ship:
                if player["color"] in ship and "orb" not in ship:
                    playerShipsCount = playerShipsCount + 1
        return playerShipsCount > 0

    @staticmethod
    async def startInfluence(game: GamestateHelper, p1, interaction: discord.Interaction):
        view = View()
        await interaction.channel.send(f"{p1['player_name']} is using their turn to influence.")
        view.add_item(Button(label="Remove Influence", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{p1['color']}_removeInfluenceStart"))
        if len(InfluenceButtons.getTilesToInfluence(game, p1)) > 0:
            view.add_item(Button(label="Add  Influence", style=discord.ButtonStyle.green,
                                 custom_id=f"FCID{p1['color']}_addInfluenceStart"))
        if "Magellan" in p1["name"]:
            view.add_item(Button(label="Refresh 1 Colony Ship", style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{p1['color']}_refreshPopShips"))
        else:
            view.add_item(Button(label="Refresh 2 Colony Ships", style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{p1['color']}_refreshPopShips"))
        view.add_item(Button(label="Put Down Population", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{p1['color']}_startPopDrop"))
        view.add_item(Button(label="Conclude Influence Action", style=discord.ButtonStyle.red,
                             custom_id=f"FCID{p1['color']}_finishInfluenceAction"))
        view.add_item(Button(label="Restart Turn", style=discord.ButtonStyle.gray,
                             custom_id=f"FCID{p1['color']}_restartTurn"))
        await interaction.message.delete()
        await interaction.channel.send(f"{p1['player_name']} you may remove up to two disks"
                                       " and influence up to 2 spaces. You may also refresh colony ships"
                                       " or put down population at any time during this resolution.", view=view)

    @staticmethod
    async def addInfluenceStart(game: GamestateHelper, p1, interaction: discord.Interaction):
        view = View()
        tiles = InfluenceButtons.getTilesToInfluence(game, p1)
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{p1['color']}_addInfluenceFinish_" + tile))
        await interaction.channel.send(f"{p1['player_name']} choose the tile you would like to influence", view=view)
        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))

    @staticmethod
    async def addInfluenceFinish(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID: str):
        tileLoc = buttonID.split("_")[1]
        if p1["influence_discs"] < 1:
            await interaction.channel.send(f"{p1['player_name']} does not have any more influence disks.")
            return
        if game.gamestate["board"][tileLoc]["owner"] != 0:
            await interaction.channel.send(f"Someone else controls {tileLoc}. "
                                           "Remove their control via valid means first.")
            return
        game.add_control(p1["color"], tileLoc)
        await interaction.channel.send(f"{p1['player_name']} acquired control of {tileLoc}.")
        await interaction.message.delete()

    @staticmethod
    async def refreshPopShips(game: GamestateHelper, player, interaction: discord.Interaction, buttonID: str):
        if "Magellan" in player["name"]:
            numShips = game.refresh_one_colony_ship(game.get_player_from_color(player["color"]))
        else:
            numShips = game.refresh_two_colony_ships(game.get_player_from_color(player["color"]))
        view = View.from_message(interaction.message)
        for button in view.children:
            if buttonID in button.custom_id:
                view.remove_item(button)
        await interaction.channel.send(f"{player['player_name']} now has {numShips}"
                                       f" colony ship{'s' if numShips == 1 else ''} available to use.")
        await interaction.message.edit(view=view)

    @staticmethod
    async def finishInfluenceAction(game: GamestateHelper, player, interaction: discord.Interaction,
                                    player_helper: PlayerHelper):
        player_helper.spend_influence_on_action("influence")
        game.update_player(player_helper)
        await TurnButtons.finishAction(player, game, interaction, player_helper)

    @staticmethod
    async def removeInfluenceStart(game: GamestateHelper, player, interaction: discord.Interaction):
        view = View()
        tiles = game.get_owned_tiles(player)
        for tile in tiles:
            view.add_item(Button(label=tile, style=discord.ButtonStyle.blurple,
                                 custom_id=f"FCID{player['color']}_removeInfluenceFinish_{tile}_normal"))
        await interaction.channel.send(f"{player['player_name']}, choose the tile"
                                       " you would like to remove influence from", view=view)

        drawing = DrawHelper(game.gamestate)
        if len(tiles) > 0:
            asyncio.create_task(interaction.followup.send(file=await asyncio.to_thread(drawing.mergeLocationsFile,
                                                                                       tiles), ephemeral=True))

    @staticmethod
    async def removeInfluenceFinish(game: GamestateHelper, interaction: discord.Interaction,
                                    buttonID: str, delete: bool):
        tileLoc = buttonID.split("_")[1]
        owner = game.gamestate["board"][tileLoc]["owner"]
        if owner == 0:
            await interaction.channel.send(f"No owner found of {tileLoc}.")
            return
        p1 = game.getPlayerObjectFromColor(owner)
        graveYard = buttonID.split("_")[2] == "graveYard"
        game.remove_control(p1["color"], tileLoc)
        await interaction.channel.send(f"{p1['player_name']} lost control of {tileLoc}.")
        for pop in PopulationButtons.findFullPopulation(game, tileLoc):
            neutralCubes, orbitalCubes = game.remove_pop([f"{pop}_pop"], tileLoc,
                                                         game.get_player_from_color(p1["color"]), graveYard)
            if neutralCubes > 0:
                view = View()
                planetTypes = ["money", "science", "material"]
                for planetT in planetTypes:
                    if p1[f"{planetT}_pop_cubes"] < 13:
                        view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple,
                                             custom_id=f"FCID{p1['color']}_addCubeToTrack_{planetT}"))
                await interaction.channel.send("A neutral cube was removed, "
                                               "please tell the bot what track you want it to go on.", view=view)
            if orbitalCubes > 0:
                view = View()
                planetTypes = ["money", "science"]
                for planetT in planetTypes:
                    if p1[f"{planetT}_pop_cubes"] < 13:
                        view.add_item(Button(label=planetT.capitalize(), style=discord.ButtonStyle.blurple,
                                             custom_id=f"FCID{p1['color']}_addCubeToTrack_{planetT}"))
                await interaction.channel.send("An orbital cube was removed, "
                                               "please tell the bot what track you want it to go on.", view=view)
            else:
                await interaction.channel.send(f"{p1['username']} Removed 1 {pop.replace('adv', '')} population.")
        if delete:
            await interaction.message.delete()
        p1 = game.getPlayerObjectFromColor(owner)
        if len(p1["owned_tiles"]) == 0:
            view = View()
            view.add_item(Button(label="Confirm Elimination", style=discord.ButtonStyle.red,
                                            custom_id=f"FCID{p1['color']}_eliminatePlayer"))
            view.add_item(Button(label="False Alarm", style=discord.ButtonStyle.gray,
                                            custom_id=f"FCID{p1['color']}_deleteMsg"))
            await interaction.channel.send(f"{p1['player_name']} you lost control of your last sector, and may be eliminated if you "
                                           "cannot afford upkeep or if you have no more ships on the board. "
                                           "Press this button to confirm elimination", view=view)

    @staticmethod
    async def eliminatePlayer(game: GamestateHelper, player, interaction: discord.Interaction,
                                    player_helper: PlayerHelper, delete:bool):
        player_helper.setEliminated(True)
        game.update_player(player_helper)
        if delete:
            await interaction.message.delete()
        player_name = player["player_name"]
        player_color = player["color"]
        for tile in game.gamestate["board"]:
            if "back" in game.gamestate["board"][tile]["sector"] or "owner" not in game.gamestate["board"][tile]:
                continue
            if game.gamestate["board"][tile]["owner"] == player_color:
                game.gamestate["board"][tile]["owner"] = 0
                if len(game.gamestate["board"][tile]["money_pop"]) > 0:
                    game.gamestate["board"][tile]["money_pop"][0] = 0
                if len(game.gamestate["board"][tile]["science_pop"]) > 0:
                    game.gamestate["board"][tile]["science_pop"][0] = 0
                if len(game.gamestate["board"][tile]["material_pop"]) > 0:
                    game.gamestate["board"][tile]["material_pop"][0] = 0
                if len(game.gamestate["board"][tile]["neutral_pop"]) > 0:
                    game.gamestate["board"][tile]["neutral_pop"][0] = 0
                if len(game.gamestate["board"][tile]["moneyadv_pop"]) > 0:
                    game.gamestate["board"][tile]["moneyadv_pop"][0] = 0
                if len(game.gamestate["board"][tile]["scienceadv_pop"]) > 0:
                    game.gamestate["board"][tile]["scienceadv_pop"][0] = 0
                if len(game.gamestate["board"][tile]["materialadv_pop"]) > 0:
                    game.gamestate["board"][tile]["materialadv_pop"][0] = 0
                if len(game.gamestate["board"][tile]["neutraladv_pop"]) > 0:
                    game.gamestate["board"][tile]["neutraladv_pop"][0] = 0
            game.gamestate["board"][tile]["player_ships"] = [e
                                                            for e in game.gamestate["board"][tile]["player_ships"]
                                                            if (player_color not in e or "mon" in e or "orb" in e)]
        try:
            if player_name in game.gamestate["pass_order"]:
                game.gamestate["pass_order"].remove(player_name)
        except KeyError:
            pass
        try:
            if player_name in game.gamestate["turn_order"]:
                game.gamestate["turn_order"].remove(player_name)
        except KeyError:
            pass
        try:
            if player_color in game.gamestate["peopleToCheckWith"]:
                game.gamestate["peopleToCheckWith"].remove(player_color)
        except KeyError:
            pass
        game.update()


    @staticmethod
    async def addCubeToTrack(game: GamestateHelper, p1, interaction: discord.Interaction, buttonID: str):
        pop = buttonID.split("_")[1]
        cubes = p1[f"{pop}_pop_cubes"]
        player = game.getPlayerObjectFromColor(p1["color"])
        oldIncome = player["population_track"][player[f"{pop}_pop_cubes"] - 1]
        if cubes > 12:
            await interaction.channel.send(f"The {pop} track is full. Cannot add more cubes to this track.")
            return
        game.remove_pop([f"{pop}_pop"], "dummy", game.get_player_from_color(p1["color"]), False)
        income = player["population_track"][player[f"{pop}_pop_cubes"] - 1]
        await interaction.channel.send(f"{p1['player_name']} added 1 {pop.replace('adv', '')}"
                                       f" population back to its track. "
                                       f"Income went from {oldIncome} to {income}.")
        await interaction.message.delete()
