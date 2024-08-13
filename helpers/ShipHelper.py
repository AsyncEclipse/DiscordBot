import json

p1 = {"player_name": "<@265561667293675521>", "color": "blue", "name": "Hydran Progress", "materials": 6, "science": 28, "money": 45, "colony_ships": 3,
      "base_colony_ships": 3, "home_planet": "224", "owned_tiles": [], "explore_apt": 1, "research_apt": 2, "upgrade_apt": 2, "build_apt": 2, "move_apt": 2,
      "influence_apt": 2, "trade_value": 3, "influence_discs": 3, "influence_track": [30, 25, 21, 17, 13, 10, 7, 5, 3, 2, 1, 0, 0], "money_pop_cubes": 11,
      "material_pop_cubes": 12, "science_pop_cubes": 11, "population_track": [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0],
      "military_tech": ["plm"], "grid_tech": ["fus", "ade"], "nano_tech": ["adl", "adl", "flm"], "ancient_parts": ["socha"],
      "tech_track": [-8, -5, -4, -3, -2, -1, 0, 0], "reputation_track": ["amb", "mixed", "mixed", "mixed"], "cost_orbital": 4,
      "cost_monolith": 10, "cost_interceptor": 3, "cost_cruiser": 5, "cost_dread": 8, "cost_starbase": 3, "ship_stock": [5, 1, 1, 4],
      "explore_action_counters": 0, "research_action_counters": 1, "upgrade_action_counters": 0, "build_action_counters": 3, "move_action_counters": 0,
      "influence_action_counters": 0, "base_interceptor_speed": 2, "base_interceptor_nrg": 0, "base_interceptor_comp": 0, "base_cruiser_speed": 1,
      "base_cruiser_nrg": 0, "base_cruiser_comp": 0, "base_dread_speed": 0, "base_dread_nrg": 0, "base_dread_comp": 0, "base_starbase_speed": 4,
      "base_starbase_nrg": 3, "base_starbase_comp": 0,
      "interceptor_parts": ["elc", "nus", "nud", "ioc"], "cruiser_parts": ["elc", "flm", "flm", "nus", "hul", "nud"],
      "dread_parts": ["elc", "ioc", "ioc", "empty", "nus", "hul", "hul", "nud"], "starbase_parts": ["elc", "ioc", "hul", "elc", "hul"]}

class Ship:
    def __init__(self):
        self.range = 0
        self.speed = 0
        self.energy = 0
        self.dice = []
        self.computer = 0
        self.shield = 0
        self.missile = []
        self.hull = 0
        self.repair = 0
        self.external = 0

    def build_ship_stats(self, ship_parts):

        with open("data/parts.json", "r") as f:
            part_dict = json.load(f)
        for part in ship_parts:
            if part == "empty":
                continue

            part_stats = part_dict[part]
            self.range += part_stats["range"]
            self.speed += part_stats["speed"]
            self.energy += part_stats["nrg_src"]
            self.energy -= part_stats["nrg_use"]
            if part_stats["dice"]:
                for die in part_stats["dice"]:
                    self.dice.append(die)
            self.computer += part_stats["comp"]
            self.shield += part_stats["shield"]
            if part_stats["missile"]:
                for die in part_stats["missile"]:
                    self.missile.append(die)
            self.hull += part_stats["hull"]
            self.repair += part_stats["repair"]
            self.external += part_stats["external"]

    def take_damage(self, damage):
        self.hull -= damage
        return self.hull
    def is_destroyed(self):
        if self.hull < 0:
            return True
        return False

class PlayerShip(Ship):
    def __init__(self, player, ship_type):
        super().__init__()
        self.player = player
        self.color = player["color"]
        self.ship_type = self.ship_type_fixer(ship_type)
        self.ship_parts = player[f"{self.ship_type}_parts"]
        self.build_ship_stats(self.ship_parts)

    '''
    Parameters
    ----------
        player : dict
            Takes in a player dictionary to pull out the ship stats
        ship_type : str
            Choose which ship type to create from the player. interceptor, cruiser, dread, starbase
    '''

    def ship_type_fixer(self, ship_type):
        """

        :param ship_type: Added to take in any of the various naming systems. Should be able to also take in "color-int"
        ship naming system we created.Preferred to type in the name recommended above but, I think this will be useful
        when parsing battles (directly able to build with "player_ships" in sector)
        :return:
        """
        if "-" in ship_type:
            temp = ship_type.split("-")
            ship = temp[1]
        else:
            ship = ship_type

        if ship == "int":
            return "interceptor"
        elif ship == "cru":
            return "cruiser"
        elif ship == "drd":
            return "dread"
        elif ship == "sb":
            return "starbase"
        else:
            return ship_type

    def check_valid_ship(self):
        if (self.range <= 0 and not self.ship_type == "starbase") or self.energy < 0 or (self.ship_type == "starbase" and self.range > 0):
            return False
        else:
            return True

class AI_Ship(Ship):
    def __init__(self, ship_type, advanced=False):
        super().__init__()
        with open("data/AI_ships.json", "r") as f:
            AI_parts = json.load(f)
        if advanced == True:
            ship_parts = AI_parts[ship_type + "adv"]
        else:
            ship_parts = AI_parts[ship_type]
        self.dice = ship_parts["dice"]
        self.missile = ship_parts["missile"]
        self.speed = ship_parts["speed"]
        self.computer = ship_parts["computer"]
        self.hull = ship_parts["hull"]

    '''
    Parameters
    ----------
        ship_type : string
            Takes in an ai ship type. Options are "ai-anc", "ai-grd", and "ai-gcds"
        advanced : bool
            Decides if the AI ships are of the advanced form or not. Set to True for advanced stats, default is False.
    '''



x = AI_Ship("ai-gcds", True)

print(x.dice)
print(x.missile)
print(x.speed)
print(x.computer)
print(x.hull)