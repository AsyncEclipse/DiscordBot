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
    
    def drawTile(self, context, position, tileName):
        configs = Properties()
        with open("data/tileImageCoordinates.properties", "rb") as f:
            configs.load(f)
        x = configs.get(position)[0].split(",")[0]
        y = configs.get(position)[0].split(",")[1]
        filepath = "images/resources/hexes/defended/"+tileName+".png"
        if not os.path.exists(filepath):  
            filepath = "images/resources/hexes/homesystems/"+tileName+".png"

        tileImage = Image.open(filepath).convert("RGBA")
        tileImage = GamestateHelper.remove_background(tileImage)
        tileImage = tileImage.resize((345, 322))
        context.paste(tileImage,(int(x),int(y)))
        return context

    
    def remove_background(image):  
        cv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGBA2BGRA)  
        gray = cv2.cvtColor(cv_image, cv2.COLOR_BGRA2GRAY)  
        _, mask = cv2.threshold(gray, 250, 255, cv2.THRESH_BINARY)  
        mask = cv2.bitwise_not(mask)  
        result = cv2.bitwise_and(cv_image, cv_image, mask=mask)  

        b, g, r, a = cv2.split(result)  
        result_rgba = cv2.merge((r, g, b, a))  # Reorder the channels to RGBA format  

        result_pil = Image.fromarray(result_rgba, 'RGBA')  
        return result_pil

    def player_setup(self, player_id, faction):

        name = self.gamestate["players"][str(player_id)]["player_name"]

        if self.gamestate["setup_finished"] == "True":
            return ("The game has already been setup!")

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)

        for i in faction_data:
            if i["alias"] == faction:
                self.gamestate["players"][str(player_id)].update(i)
                self.update()
                return(f"{name} is now setup!")

    def setup_finished(self):

        for i in self.gamestate["players"]:
            if len(self.gamestate["players"][i]) < 3:
                return(f"{self.gamestate['players'][i]['player_name']} still needs to be setup!")
        self.gamestate["player_count"] = len(self.gamestate["players"])
        draw_count = {2: [5, 12], 3: [8, 14], 4: [14, 16], 5: [16, 18], 6: [18, 20]}
        third_sector_tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314",
                              "315", "316", "317", "318", "381", "382"]
        sector_draws = draw_count[self.gamestate["player_count"]][0]
        tech_draws = draw_count[self.gamestate["player_count"]][1]

        while sector_draws > 0:
            random.shuffle(third_sector_tiles)
            self.gamestate["tile_deck_300"].append(third_sector_tiles.pop(0))
            sector_draws -= 1

        while tech_draws > 0:
            random.shuffle(self.gamestate["tech_deck"])
            self.gamestate["available_techs"].append(self.gamestate["tech_deck"].pop(0))

            # TODO: once tech tile JSON is complete, needs some logic to not decrement tech_draws if it's a rare tech
            # TODO: Also add a read from the JSON file to add actual tech tile stats to available_techs board state

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