import discord
from discord.ext import commands
from discord.ui import View
from Buttons.Explore import ExploreButtons
from Buttons.Population import PopulationButtons
from helpers.GamestateHelper import GamestateHelper
from helpers.PlayerHelper import PlayerHelper
from helpers.DrawHelper import DrawHelper
from discord.ui import View, Button
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties

class InfluenceButtons:

    @staticmethod  
    def areTwoTilesAdjacent(game: GamestateHelper, tile1, tile2, configs):  

        def is_adjacent(tile_a, tile_b):  
            for index, adjTile in enumerate(configs.get(tile_a)[0].split(",")):  
                tile_orientation_index = (index + 6 + int(game.get_gamestate()["board"][tile_a]["orientation"] / 60)) % 6  
                if adjTile == tile_b and tile_orientation_index in game.get_gamestate()["board"][tile_a]["wormholes"]:   
                    return True  
            return False  
        
        return is_adjacent(tile1, tile2) and is_adjacent(tile2, tile1)  

    @staticmethod  
    def getTilesToInfluence(game: GamestateHelper, player):  
        configs = Properties()  
        with open("data/tileAdjacencies.properties", "rb") as f:  
            configs.load(f)  
        tilesViewed = []
        tilesToInfluence = []
        playerTiles = ExploreButtons.getListOfTilesPlayerIsIn(game, player)  
        for tile in playerTiles:  
            for adjTile in configs.get(tile)[0].split(","):  
                if adjTile not in tilesViewed and InfluenceButtons.areTwoTilesAdjacent(game, tile, adjTile, configs):
                    tilesViewed.append(adjTile)
                    if "owner" in game.get_gamestate()["board"][adjTile] and game.get_gamestate()["board"][adjTile]["owner"]==0:
                        tilesToInfluence.append(adjTile)
            if tile not in tilesViewed:
                    tilesViewed.append(tile)
                    if "owner" in game.get_gamestate()["board"][tile] and game.get_gamestate()["board"][tile]["owner"]==0:
                        tilesToInfluence.append(tile)
        return tilesToInfluence
    @staticmethod  
    def getTilesToInfluence(game: GamestateHelper, player):  