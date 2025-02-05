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
        self.total_energy = 0
        self.external = 0
        self.cost = 0
        self.jumpdrive = 0

    def build_ship_stats(self, ship_parts):
        with open("data/parts.json", "r") as f:
            part_dict = json.load(f)
        for part in ship_parts:
            if part == "empty":
                continue
            if part == "jud":
                self.jumpdrive = 1
            part_stats = part_dict[part]
            self.range += part_stats["range"]
            self.speed += part_stats["speed"]
            self.energy += part_stats["nrg_src"]
            self.total_energy += part_stats["nrg_src"]
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
        self.total_energy = player[f"base_{self.ship_type}_nrg"]
        self.computer = player[f"base_{self.ship_type}_comp"]

        # added for Outcast factions
        try:
            self.shield = player[f"base_{self.ship_type}_shield"]
        except KeyError:
            pass
        try:
            self.hull = player[f"base_{self.ship_type}_hull"]
        except KeyError:
            pass

        self.ship_parts = player[f"{self.ship_type}_parts"]
        self.build_ship_stats(self.ship_parts)
        if "orb" in self.ship_type:
            self.cost = 5
        else:
            self.cost = player[f"cost_{self.ship_type}"]

    def getRange(self):
        return self.range

    def getJumpDrive(self):
        return self.jumpdrive
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
        elif ship == "orbital":
            return "orb"
        else:
            return ship_type

    def check_valid_ship(self):
        return not any([self.range <= 0 and self.ship_type not in ["starbase", "orb"],
                        self.energy < 0,
                        self.range > 0 and self.ship_type in ["starbase", "orb"]])


class AI_Ship(Ship):
    def __init__(self, ship_type, advanced=False, wa=False):
        super().__init__()
        with open("data/AI_ships.json", "r") as f:
            AI_parts = json.load(f)
        if "ai-" not in ship_type:
            ship_type = f"ai-{ship_type}"
        if advanced:
            if "adv" not in ship_type:
                ship_type += "adv"
            ship_parts = AI_parts[ship_type]
        if wa:
            if "wa" not in ship_type:
                ship_type += "wa"
            ship_parts = AI_parts[ship_type]
        else:
            ship_parts = AI_parts[ship_type]
        self.dice = ship_parts["dice"]
        self.missile = ship_parts["missile"]
        self.speed = ship_parts["speed"]
        self.computer = ship_parts["computer"]
        self.hull = ship_parts["hull"]
        self.shield = ship_parts["shield"]

    '''
    Parameters
    ----------
        ship_type : string
            Takes in an ai ship type. Options are "ai-anc", "ai-grd", and "ai-gcds"
        advanced : bool
            Decides if the AI ships are of the advanced form or not. Set to True for advanced stats, default is False.
    '''
