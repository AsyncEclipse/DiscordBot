import helpers.game_state_helper as game_state_helper

class PlayerHelper:
    def __init__(self, game_id, player_id):
        self.player_id = str(player_id)
        self.game_id = game_id

    def get_player_stats(self):
        gamestate = game_state_helper.read(self.game_id)
        return(gamestate["players"][self.player_id])

    def write_player_stats(self, stats):
        gamestate = game_state_helper.read(self.game_id)
        gamestate["players"][self.player_id] = stats
        game_state_helper.write(self.game_id, gamestate)

    def get_resources(self):
        stats = self.get_player_stats()
        return(f"{stats["player_name"]}: Materials = {stats["materials"]}, Science = {stats["science"]}, Money = {stats["money"]}")

    def adjust_materials(self, adjustment):

        stats = self.get_player_stats()
        gamestate = game_state_helper.read(self.game_id)
        before = stats["materials"]
        stats["materials"] += adjustment
        self.write_player_stats(stats)

        return(f"Adjusted materials from {before} to {before+adjustment}")