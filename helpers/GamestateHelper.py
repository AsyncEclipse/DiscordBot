import json
import config
import numpy as np  
from PIL import Image, ImageDraw, ImageFont
from jproperties import Properties
import cv2
import os
import random

class GamestateHelper:
    def __init__(self, game_id):
        self.game_id = game_id
        self.gamestate = self.get_gamestate()

    def get_gamestate(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "r") as f:
            gamestate = json.load(f)
        return gamestate
    
    def showTile(self, tileName):
        filepath = "images/resources/hexes/sector1/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/sector2/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/sector3/"+tileName+".png"
        if os.path.exists(filepath):  
            tileImage = Image.open(filepath).convert("RGBA")
            tileImage = tileImage.resize((345, 299))
            return tileImage
    
    def retrieveTileFromList(self, ring):
        tileList = self.gamestate["tile_deck_"+str(ring)+"00"]
        random.shuffle(tileList)
        tile = tileList.pop()
        self.gamestate["tile_deck_"+str(ring)+"00"] = tileList
        self.update()
        return tile

    
    def drawTile(self, context, position, tileName, rotation):
        configs = Properties()
        with open("data/tileImageCoordinates.properties", "rb") as f:
            configs.load(f)
        x = int(configs.get(position)[0].split(",")[0])
        y = int(configs.get(position)[0].split(",")[1])
        filepath = "images/resources/hexes/defended/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/homesystems/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/backs/"+tileName+".png"
        if not os.path.exists(filepath):
            filepath = "images/resources/hexes/sector1/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/sector2/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/sector3/"+tileName+".png"
        if os.path.exists(filepath):  
            tileImage = Image.open(filepath).convert("RGBA")
            tileImage = tileImage.rotate(rotation)
            tileImage = tileImage.resize((345, 299))
            
            font = ImageFont.truetype("arial.ttf", size=45) 
            text = str(position)
            text_position = (255, 132) 
            text_color = (255, 255, 255) 
            textDrawableImage = ImageDraw.Draw(tileImage)
            textDrawableImage.text(text_position,text,text_color,font=font)
            context.paste(tileImage,(x,y),mask=tileImage)

        return context

    def updateTileList(self, tileList):
        self.gamestate["board"] = tileList
        self.update()
    
    def addTile(self, position, image, orientation):
        tileList = self.gamestate["board"]
        tileList[position] = (image, orientation)
        self.gamestate["board"] = tileList
        self.update()

    def player_setup(self, player_id, faction):

        name = self.gamestate["players"][str(player_id)]["player_name"]

        if self.gamestate["setup_finished"] == "True":
            return ("The game has already been setup!")

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)


        self.gamestate["players"][str(player_id)].update(faction_data[faction])
        self.update()
        #return(f"{name} is now setup!")

    def setup_finished(self):

        colors = ["blue", "red", "green", "yellow", "black", "white"]
        for i in self.gamestate["players"]:
            if len(self.gamestate["players"][i]) < 3:
                return(f"{self.gamestate['players'][i]['player_name']} still needs to be setup!")
            else:
                self.gamestate["players"][i].update({"color": colors.pop(0)})
        self.gamestate["player_count"] = len(self.gamestate["players"])
        draw_count = {2: [5, 12], 3: [8, 14], 4: [14, 16], 5: [16, 18], 6: [18, 20]}

        third_sector_tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314",
                              "315", "316", "317", "318", "381", "382"]
        sector_draws = draw_count[self.gamestate["player_count"]][0]
        tech_draws = draw_count[self.gamestate["player_count"]][1]

        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)

        while sector_draws > 0:
            random.shuffle(third_sector_tiles)
            self.gamestate["tile_deck_300"].append(third_sector_tiles.pop(0))
            sector_draws -= 1

        while tech_draws > 0:
            random.shuffle(self.gamestate["tech_deck"])
            picked_tech = self.gamestate["tech_deck"].pop(0)

            self.gamestate["available_techs"].append(tech_data[picked_tech])

            if tech_data[picked_tech]["track"] == "any":
                pass
            else:
                tech_draws -= 1

        self.gamestate["setup_finished"] = 1
        self.update()
        return("Game setup complete")

    def update(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
            json.dump(self.gamestate, f)

    def get_player(self, player_id):
        return self.gamestate["players"][str(player_id)]

    def update_player(self, *args):

        for ar in args:
            self.gamestate["players"][ar.player_id] = ar.stats
        self.update()