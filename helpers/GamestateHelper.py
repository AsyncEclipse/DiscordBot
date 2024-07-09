import json
import config

class GamestateHelper:
    def __init__(self, game_id):
        self.game_id = game_id
        self.gamestate = self.get_gamestate()

    def get_gamestate(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "r") as f:
            gamestate = json.load(f)

        return gamestate

    def update(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
            json.dump(self.gamestate, f)

    def get_player_stats(self, player_id):
        return self.gamestate["players"][str(player_id)]

    def update_player_stats(self, player_id, player_stats):
        self.gamestate["players"][str(player_id)] = player_stats
        self.update()