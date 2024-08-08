import json

class PlayerShip:
    """
    Class to represent ships and contain easy functions for checking ship stats.
    Function was originally created to have an is_ship_valid function to make sure upgrades are possible

    """
    def __init__(self, player, ship_type):
        self.player = player
        self.color = player["color"]
        self.ship_type = self.ship_type_fixer(ship_type)
        self.ship_parts = player[f"{self.ship_type}_parts"]
        self.range = 0
        self.speed = player[f"base_{self.ship_type}_speed"]
        self.energy = player[f"base_{self.ship_type}_nrg"]
        self.dice = []
        self.computer = player[f"base_{self.ship_type}_comp"]
        self.shield = 0
        self.missile = []
        self.hull = 0
        self.repair = 0
        self.external = 0

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
                self.dice.append(part_stats["dice"])
            self.computer += part_stats["comp"]
            self.shield += part_stats["shield"]
            if part_stats["missile"]:
                self.missile.append(part_stats["missile"])
            self.hull += part_stats["hull"]
            self.repair += part_stats["repair"]
            self.external += part_stats["external"]

    def check_valid_ship(self):
        if (self.range <= 0 and not self.ship_type == "starbase") or self.energy < 0 or (self.ship_type == "starbase" and self.range > 0):
            return False
        else:
            return True

    def take_damage(self, damage):
        self.hull -= damage

    def is_destroyed(self):
        if self.hull <= 0:
            return True
        return False