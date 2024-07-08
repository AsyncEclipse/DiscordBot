
class PlayerHelper:
    def __init__(self, player_id, player_stats):
        self.stats = player_stats
        self.player_id = str(player_id)

    def get_resources(self):
        return(f"{self.stats["player_name"]}: Materials = {self.stats["materials"]}, Science = {self.stats["science"]}, Money = {self.stats["money"]}")

    def adjust_materials(self, adjustment):

        before = self.stats["materials"]
        self.stats["materials"] += adjustment

        return(f"Adjusted materials from {before} to {before+adjustment}")