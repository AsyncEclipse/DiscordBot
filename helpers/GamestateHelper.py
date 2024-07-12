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

    def player_setup(self, player_id, faction):

        name = self.gamestate["players"][str(player_id)]["player_name"]

        if self.gamestate["setup_finished"] == "True":
            return ("The game has already been setup!")

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)
        self.gamestate["players"][str(player_id)].update(faction_data[faction])
        self.update()
        return(f"{name} is now setup!")

    def setup_finished(self):

        for i in self.gamestate["players"]:
            if len(self.gamestate["players"][i]) < 3:
                return(f"{self.gamestate["players"][i]["player_name"]} still needs to be setup!")

        self.gamestate["setup_finished"] = "True"
        return("Game setup complete")

    def update(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
            json.dump(self.gamestate, f)

    def get_player_stats(self, player_id):
        return self.gamestate["players"][str(player_id)]

    def update_player_stats(self, *args):

        for ar in args:
            self.gamestate["players"][ar.player_id] = ar.stats
        self.update()