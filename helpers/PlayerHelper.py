
class PlayerHelper:
    def __init__(self, player_id, player_stats):
        self.stats = player_stats
        self.player_id = str(player_id)
        self.name = self.stats["player_name"]


    def adjust_materials(self, adjustment):
        before = self.stats["materials"]
        self.stats["materials"] += adjustment
        return(f"\n> Adjusted materials from {before} to {before+adjustment}")

    def adjust_science(self, adjustment):
        before = self.stats["science"]
        self.stats["science"] += adjustment
        return (f"\n> Adjusted science from {before} to {before + adjustment}")

    def adjust_money(self, adjustment):
        before = self.stats["money"]
        self.stats["money"] += adjustment
        return(f"\n> Adjusted money from {before} to {before+adjustment}")

    def adjust_material_cube(self, adjustment):
        before = self.stats["material_pop_cubes"]
        self.stats["material_pop_cubes"] += adjustment
        return (f"\n> Adjusted material cubes from {before} to {before + adjustment}")

    def adjust_science_cube(self, adjustment):
        before = self.stats["science_pop_cubes"]
        self.stats["science_pop_cubes"] += adjustment
        return (f"\n> Adjusted science cubes from {before} to {before + adjustment}")

    def adjust_money_cube(self, adjustment):
        before = self.stats["money_pop_cubes"]
        self.stats["money_pop_cubes"] += adjustment
        return (f"\n> Adjusted money cubes from {before} to {before + adjustment}")
    def adjust_influence(self, adjustment):
        before = self.stats["influence_discs"]
        self.stats["influence_discs"] += adjustment
        return (f"\n> Adjusted influence discs from {before} to {before + adjustment}")