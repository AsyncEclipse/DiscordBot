from helpers.GamestateHelper import GamestateHelper
import json
class GameSetup:

    def __init__(self, game_id):
        self.game_id = game_id

    def player_setup(self, player_id, faction):

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)

        game = GamestateHelper(self.game_id)
        game.gamestate["players"][str(player_id)].update(faction_data[faction])
        game.update()

        return f"{game.gamestate["players"][str(player_id)]["player_name"]} set up!"