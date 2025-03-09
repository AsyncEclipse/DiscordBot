import discord
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from discord.ui import View, Button
from jproperties import Properties


class BlackHoleButtons:

    @staticmethod
    def getBlackHoleShips(game: GamestateHelper, player):
        view = View()
        if "blackHoleReturn" in player:
            count = 1
            for shipKey in player["blackHoleReturn"]:
                count += 1
                shipType = shipKey.split("_")[0]
                ship = shipKey.split("_")[1]
                rnd = int(shipKey.split("_")[2])
                roundNum = 1
                if "roundNum" in game.gamestate:
                    roundNum = game.gamestate["roundNum"]
                if rnd != roundNum:
                    continue
                view.add_item(Button(label=f"Return Black Hole Ship ({game.getShipFullName(ship.split('-')[1])})",
                                     style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}"
                                     f"_blackHoleReturnStart_{shipType}_{ship}_{str(rnd)}_{str(count)}"))
        return view

    @staticmethod
    async def blackHoleReturnStart(game: GamestateHelper, player, customID: str, player_helper: PlayerHelper,
                                   interaction: discord.Interaction):
        shipKey = customID.replace("blackHoleReturnStart_", "")
        shipKey = shipKey.split("_")[0] + "_" + shipKey.split("_")[1] + "_" + shipKey.split("_")[2]
        if shipKey in player.get("blackHoleReturn", []):
            player_helper.stats["blackHoleReturn"].remove(shipKey)
            game.update_player(player_helper)
        else:
            return
        locationType = shipKey.split("_")[0]
        ship = shipKey.split("_")[1]
        await interaction.channel.send(player["player_name"] + ", select a tile to return the ship to.",
                                       view=BlackHoleButtons.findBlackHoleOptions(game, player, ship,
                                                                                  locationType, "no"))

    @staticmethod
    def findBlackHoleOptions(game: GamestateHelper, player, ship, locationType, damage):
        view = View()
        if "border" in locationType:
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
            for tile in game.gamestate["board"]:
                if "wormholes" in game.gamestate["board"][tile]:
                    for index, adjTile in enumerate(configs.get(tile)[0].split(",")):
                        tile_orientation_index = (index + int(game.gamestate["board"][tile]["orientation"]) // 60) % 6
                        if tile_orientation_index in game.gamestate["board"][tile]["wormholes"]:
                            if adjTile not in game.gamestate["board"] or "back" in game.gamestate["board"][adjTile]["sector"]:
                                view.add_item(Button(label=f"Add ship to Tile {tile}", style=discord.ButtonStyle.gray,
                                                     custom_id=f"FCID{player['color']}_blackHoleFinish"
                                                     f"_{ship}_{tile}_{damage}"))
                                break
        else:
            for tile in game.gamestate["board"]:
                if int(tile) < 200 and int(tile) > 99 and "back" not in game.gamestate["board"][tile]["sector"]:
                    view.add_item(Button(label=f"Add ship to Tile {tile}", style=discord.ButtonStyle.gray,
                                         custom_id=f"FCID{player['color']}_blackHoleFinish_{ship}_{tile}_{damage}"))
        return view

    @staticmethod
    async def blackHoleFinish(game: GamestateHelper, player, customID: str,
                              player_helper: PlayerHelper, interaction: discord.Interaction):
        ship = customID.split("_")[1]
        tile = customID.split("_")[2]
        damage = customID.split("_")[3]
        from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
        destination = tile
        game.add_units([ship], tile)
        shipName = game.getShipFullName(ship.split("-")[1])
        await interaction.channel.send(f"{player['player_name']} put a {shipName} in tile {tile}"
                                       " using the Black Hole return feature.")
        game.fixshipsOrder(tile)
        owner = game.gamestate["board"][destination]["owner"]
        if damage == "damage":
            game.add_damage(ship, destination, 1)
        if owner != 0 and isinstance(owner, str) and owner != player["color"]:
            p2 = game.getPlayerObjectFromColor(owner)
            player_helper2 = PlayerHelper(game.get_player_from_color(owner), p2)
            player_helper2.permanentlyPassTurn(False)
            game.update_player(player_helper2)
            await interaction.channel.send(p2["player_name"] + " your system has been invaded")
        await interaction.message.delete()
