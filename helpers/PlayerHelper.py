
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

    def adjust_colony_ships(self, adjustement):
        if self.stats["colony_ships"] <= 0:
            return False
        elif (self.stats["colony_ships"] - adjustement) < 0:
            return False
        else:
            return(self.stats["colony_ships"] - adjustement)

    def materials_income(self):
        track = self.stats["population_track"]
        cubes = self.stats["material_pop_cubes"]
        return(track[-(cubes+1)])

    def science_income(self):
        track = self.stats["population_track"]
        cubes = self.stats["science_pop_cubes"]
        return(track[-(cubes+1)])

    def money_income(self):
        track = self.stats["population_track"]
        cubes = self.stats["money_pop_cubes"]
        return(track[-(cubes+1)])

    def upkeep(self):
        track = self.stats["influence_track"]
        discs = self.stats["influence_discs"]
        if discs >= 13:
            return(0)
        else:
            return(track[-(discs+1)])