import helpers.game_state_helper as game_state_helper
import json
class GameSetup:

    def __init__(self, game_id):
        self.game_id = game_id
        self.gamestate = game_state_helper.read(game_id)

    def player_setup(self, player_id, faction):

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)

        self.gamestate["players"][str(player_id)].update(faction_data[faction])
        game_state_helper.write(self.game_id, self.gamestate)

        return(f"{self.gamestate["players"][str(player_id)]["player_name"]} set up!")