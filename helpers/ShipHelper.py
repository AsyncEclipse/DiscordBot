import json

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
        self.cost = 0

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
        self.speed = player[f"base_{self.ship_type}_speed"]
        self.energy = player[f"base_{self.ship_type}_nrg"]
        self.computer = player[f"base_{self.ship_type}_comp"]
        self.ship_parts = player[f"{self.ship_type}_parts"]
        self.build_ship_stats(self.ship_parts)
        self.cost = player[f"cost_{self.ship_type}"]


    def getRange(self):
        return self.range
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
        elif ship == "drd" or ship == "dreadnought":
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
        if "ai-" not in ship_type:
            ship_type = "ai-"+ship_type
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