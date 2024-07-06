import json
import discord
import config
from config import update_game_number
import helpers.game_state_helper as game_state_helper

class GameSetup:
    def __init__(self, game_name, player_list):
        self.game_name = game_name
        self.player_list = player_list
        self.game_state = []

    def create_game(self):
        game_id = "aeb"+str(config.game_number)
        update_game_number()

        with open("data/basic_game.json", "r") as f:
            self.game_state = json.load(f)

        self.game_state["game_id"] = game_id
        self.game_state["game_name"] = self.game_name

        for i in self.player_list:
            self.game_state["players"].update({i[0]: {"player_name": i[1]}})

        return self.game_state

    def player_setup(self):
        #TODO
        return None

    def game_ready(self):
        self.game_state["game_ready"] = True

    def upload(self):
        game_state_helper.write(self.game_state["game_id"], self.game_state)
