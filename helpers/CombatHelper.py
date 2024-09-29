import json

import discord

from helpers.DrawHelper import DrawHelper
from helpers.GamestateHelper import GamestateHelper
from helpers.ShipHelper import AI_Ship, PlayerShip

class Combat:

    @staticmethod
    def findPlayersInTile(game:GamestateHelper,pos:str):
        tile_map = game.get_gamestate()["board"]
        if "player_ships" not in tile_map[pos]:
            return []
        player_ships = tile_map[pos]["player_ships"][:]
        players = []
        for ship in player_ships:
            color = ship.split("-")[0]
            if color not in players:
                players.append(color)
        return players
    
    @staticmethod
    def findTilesInConflict(game:GamestateHelper):
        tile_map = game.get_gamestate()["board"]
        tiles = []
        for tile in tile_map:
            if len(Combat.findPlayersInTile(game,tile)) > 1:
                tiles.append((int(tile_map[tile]["sector"]),tile))
        sorted_tiles = sorted(tiles, key=lambda x: x[0], reverse=True)  
        return sorted_tiles
    @staticmethod
    async def startCombatThreads(game:GamestateHelper, interaction:discord.Interaction):
        channel = interaction.channel
        role = discord.utils.get(interaction.guild.roles, name=game.get_gamestate()["game_id"])  
        tiles = Combat.findTilesInConflict(game)
        for tile in tiles:
            message_to_send = "Combat will occur in system "+str(tile[0])+", position "+tile[1]  
            message = await channel.send(message_to_send) 
            threadName = game.get_gamestate()["game_id"]+"-Round"+str(game.get_gamestate()["roundNum"])+" Tile "+tile[1]+" Combat"
            thread = await message.create_thread(name=threadName)
            drawing = DrawHelper(game.gamestate)
            await thread.send(role.mention +"Combat will occur in this tile",file=drawing.board_tile_image_file(tile[1]))
        await channel.send("Please resolve the combats in the order they appeared")
    @staticmethod
    def getCombatantShipsBySpeed(game:GamestateHelper, colorOrAI:str, playerShipsList):
        ships = []
        for unit in playerShipsList:
            type = unit.split("-")[1]
            owner = unit.split('-')[0]
            if colorOrAI == owner:
                if colorOrAI == "ai":
                    ship = AI_Ship(type, game.gamestate["advanced_ai"])
                    ships.append((ship.speed, type))
                else:
                    player = game.get_player_from_color(colorOrAI)
                    ship = PlayerShip(player, type)
                    ships.append((ship.speed, type))
        sorted_ships = sorted(ships, key=lambda x: x[0], reverse=True)  
        return sorted_ships

    @staticmethod
    def getCombatantSpeeds(game:GamestateHelper, colorOrAI:str, playerShipsList):
        ships = Combat.getCombatantShipsBySpeed(game, colorOrAI, playerShipsList)
        speeds =[]
        for ship in ships:
            if ship[0] not in speeds:
                speeds.append(ship[0])
        return speeds