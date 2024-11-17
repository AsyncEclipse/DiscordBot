import json
import config
from config import update_game_number
import random


class GameInit:
    def __init__(self, game_name, player_list, ai_ship_type, rift_cannon, turn_order_variant):
        self.game_name = game_name
        self.player_list = player_list
        self.gamestate = []
        self.ai_ship_type = ai_ship_type
        self.rift_cannon = rift_cannon
        self.turn_order_variant = turn_order_variant

    def create_game(self):
        game_id = "aeb"+str(config.game_number)
        update_game_number()

        with open("data/basic_game.json", "r") as f:
            self.gamestate = json.load(f)

        self.gamestate["game_id"] = game_id
        self.gamestate["game_name"] = self.game_name

        for i in self.player_list:
            self.gamestate["players"].update({i[0]: {"player_name": f"<@{str(i[0])}>"}})

        # Load discovery tiles
        listOfDisc = []
        with open("data/discoverytiles.json") as f:
            discTile_data = json.load(f)
        for tile in discTile_data:
            for x in range(discTile_data[tile]["num"]):
                listOfDisc.append(tile)
        random.shuffle(listOfDisc)
        self.gamestate["discTiles"] = listOfDisc

        # Loading of variants here
        if self.ai_ship_type == "adv":
            self.gamestate["advanced_ai"] = 1
        if self.ai_ship_type == "wa":
            self.gamestate["wa_ai"] = 1
        self.gamestate["turnsInPassingOrder"] = self.turn_order_variant
        if not self.rift_cannon:
            self.gamestate["tech_deck"].remove("rican")
            self.gamestate["discTiles"].remove("ricon")

        with open(f"{config.gamestate_path}/{self.gamestate['game_id']}.json", "w") as f:
            json.dump(self.gamestate, f)

    def update_num(self):
        config.game_number += 1
