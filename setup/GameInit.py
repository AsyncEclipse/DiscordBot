import json
import config
from config import update_game_number


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
            self.gamestate["players"].update({i[0]: {"player_name": f"<@{str(i[0])}>"}})

        with open(f"{config.gamestate_path}/{self.gamestate['game_id']}.json", "w") as f:
            json.dump(self.gamestate, f)
    def update_num(self):
        config.game_number +=1
