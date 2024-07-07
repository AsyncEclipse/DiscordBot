import json
import discord
import config
from config import update_game_number
import helpers.game_state_helper as game_state_helper

class GameInit:
    def __init__(self, game_name, player_list):
        self.game_name = game_name
        self.player_list = player_list
        self.gamestate = []

    def create_game(self):
        game_id = "aeb"+str(config.game_number)
        update_game_number()

        with open("data/basic_game.json", "r") as f:
            self.gamestate = json.load(f)

        self.gamestate["game_id"] = game_id
        self.gamestate["game_name"] = self.game_name

        for i in self.player_list:
            self.gamestate["players"].update({i[0]: {"player_name": i[1]}})

        return self.gamestate


    def upload(self):
        game_state_helper.write(self.gamestate["game_id"], self.gamestate)
