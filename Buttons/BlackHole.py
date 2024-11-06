import asyncio
import discord
from discord.ui import View
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
                type = shipKey.split("_")[0]
                ship = shipKey.split("_")[1]
                round = int(shipKey.split("_")[2])
                roundNum = 1
                if "roundNum" in game.gamestate:
                    roundNum = game.gamestate["roundNum"]
                if round != roundNum:
                    continue
                view.add_item(Button(label=f"Return Black Hole Ship ("+game.getShipFullName(ship.split("-")[1])+")", style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_blackHoleReturnStart_{type}_{ship}_{str(round)}_{str(count)}"))
        return view

    @staticmethod
    async def blackHoleReturnStart(game: GamestateHelper, player, customID:str, player_helper:PlayerHelper, interaction:discord.Interaction):
        shipKey = customID.replace("blackHoleReturnStart_","")
        shipKey = shipKey.split("_")[0]+"_"+shipKey.split("_")[1]+"_"+shipKey.split("_")[2]
        if "blackHoleReturn" in player and shipKey in player["blackHoleReturn"]:
            player_helper.stats["blackHoleReturn"].remove(shipKey)
            game.update_player(player_helper)
        else:
            return
        type = shipKey.split("_")[0]
        ship = shipKey.split("_")[1]
        round = int(shipKey.split("_")[2])
        await interaction.channel.send(player["player_name"]+" Select a tile to return the ship to", view=BlackHoleButtons.findBlackHoleOptions(game, player, ship, type,"no"))

    @staticmethod
    def findBlackHoleOptions(game: GamestateHelper, player, ship, type, damage):
        view = View()
        if "border" in type:
            configs = Properties()
            if "5playerhyperlane" in game.gamestate and game.gamestate["5playerhyperlane"]:
                with open("data/tileAdjacencies_5p.properties", "rb") as f:
                    configs.load(f)
            else:
                with open("data/tileAdjacencies.properties", "rb") as f:
                    configs.load(f)
            for tile in game.gamestate["board"]:
                if "wormholes" in game.gamestate["board"][tile]:
                    for index, adjTile in enumerate(configs.get(tile)[0].split(",")):
                        tile_orientation_index = (index + 6 + int(int(game.gamestate["board"][tile]["orientation"]) / 60)) % 6
                        if tile_orientation_index in game.gamestate["board"][tile]["wormholes"]:
                            if adjTile not in game.gamestate["board"] or "back" in game.gamestate["board"]["adjTile"]["sector"]:
                                view.add_item(Button(label=f"Add ship to Tile "+tile, style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_blackHoleFinish_{ship}_{tile}_{damage}"))
                                break
        else:
            for tile in game.gamestate["board"]:
                if int(tile) < 200 and int(tile) > 99 and "back" not in game.gamestate["board"][tile]["sector"]:
                    view.add_item(Button(label=f"Add ship to Tile "+tile, style=discord.ButtonStyle.gray, custom_id=f"FCID{player['color']}_blackHoleFinish_{ship}_{tile}_{damage}"))
        return view

    @staticmethod
    async def blackHoleFinish(game: GamestateHelper, player, customID:str, player_helper:PlayerHelper, interaction:discord.Interaction):
        ship = customID.split("_")[1]
        tile = customID.split("_")[2]
        damage = customID.split("_")[3]
        from Buttons.DiplomaticRelations import DiplomaticRelationsButtons
        destination = tile
        game.add_units([ship],tile)
        await interaction.channel.send(player["player_name"]+" put a "+game.getShipFullName(ship.split("-")[1])+" in tile "+tile +" using the black hole return feature")
        game.fixshipsOrder(tile)
        owner = game.gamestate["board"][destination]["owner"]
        if damage == "damage":
            game.add_damage(ship, destination, 1)
        if owner != 0 and isinstance(owner, str) and owner != player["color"]:
            p2 = game.getPlayerObjectFromColor(owner)
            player_helper2 = PlayerHelper(game.get_player_from_color(owner), p2)
            player_helper2.permanentlyPassTurn(False)
            game.update_player(player_helper2)
            await interaction.channel.send(p2["player_name"]+" your system has been invaded")
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
                    await interaction.channel.send( f"{player['player_name']} You broke relations with {color} and now are a traitor.")
        await interaction.message.delete()