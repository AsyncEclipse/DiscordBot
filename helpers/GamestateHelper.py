import json
import config
from helpers.PlayerHelper import PlayerHelper
from PIL import Image, ImageDraw, ImageFont
import os
from jproperties import Properties
import random

class GamestateHelper:
    def __init__(self, game_id):
        self.game_id = game_id
        self.gamestate = self.get_gamestate()

    def get_gamestate(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "r") as f:
            gamestate = json.load(f)
        return gamestate


    def tile_draw(self, ring):
        ring = int(int(ring)/100)
        if ring <= 3:
            random.shuffle(self.gamestate[f"tile_deck_{ring}00"])
            tile = self.gamestate[f"tile_deck_{ring}00"].pop(0)
            self.update()
            return tile
        else:
            random.shuffle(self.gamestate[f"tile_deck_300"])
            tile = self.gamestate[f"tile_deck_300"].pop(0)
            self.update()
            return tile

    def tile_discard(self, sector):
        self.gamestate["tile_discard"].append(sector)
        self.update()

    @staticmethod
    def getShipFullName(shipAbbreviation):
        if shipAbbreviation == "int":  
            return "interceptor"
        elif shipAbbreviation == "cru": 
            return "cruiser"
        elif shipAbbreviation == "drd":
            return "dreadnought"
        elif shipAbbreviation == "sta": 
            return "starbase"

    
    def getShortFactionNameFromFull(self, fullName):
        if fullName == "Descendants of Draco":  
            return "draco"
        elif fullName == "Mechanema": 
            return "mechanema"
        elif fullName == "Planta": 
            return "planta"
        elif fullName == "Orian Hegemony" or fullName == "Orion Hegemony": 
            return "orion"
        elif fullName == "Hydran Progress": 
            return "hydran"
        elif fullName == "Eridani Empire": 
            return "eridani"
        elif "Terran" in fullName:
            return fullName.lower().replace(" ","_")


    def add_tile(self, position, orientation, sector, owner=None):

        with open("data/sectors.json") as f:
            tile_data = json.load(f)
        try:
            tile = tile_data[sector]
            if owner != None:
                tile["owner"] = owner
            tile.update({"sector": sector})
            tile.update({"orientation": orientation})
        except KeyError:
            tile = {"sector": sector, "orientation": orientation}
        self.gamestate["board"][position] = tile

        configs = Properties()  
        with open("data/tileAdjacencies.properties", "rb") as f:  
            configs.load(f)  
        if position != None and sector != "sector3back":
            tiles = configs.get(position)[0].split(",")
            for adjTile in tiles:  
                if adjTile not in self.gamestate["board"]:
                    self.add_tile(adjTile, 0, "sector3back")
        self.update()

    def add_control(self, color, position):
        self.gamestate["board"][position]["owner"] = color
        self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] -= 1
        self.update()

    def remove_control(self, color, position):
        self.gamestate["board"][position]["owner"] = 0
        self.gamestate["players"][self.get_player_from_color(color)]["influence_discs"] += 1
        self.update()

    def add_units(self, unit_list, position):
        color = unit_list[0].split("-")[0]
        player = self.get_player_from_color(color)
        for i in unit_list:
            if "int" in i:
                self.gamestate["players"][player]["ship_stock"][0] -= 1
            if "cru" in i:
                self.gamestate["players"][player]["ship_stock"][1] -= 1
            if "drd" in i:
                self.gamestate["players"][player]["ship_stock"][2] -= 1
            if "sb" in i:
                self.gamestate["players"][player]["ship_stock"][3] -= 1
            self.gamestate["board"][position]["player_ships"].append(i)
        self.update()

    def add_pop(self, pop_list, position, playerID):
        for i in pop_list:
            self.gamestate["board"][position][i][0] = self.gamestate["board"][position][i][0]+1
            self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"] = self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"]-1
        self.update()
    def remove_pop(self, pop_list, position, playerID):
        for i in pop_list:
            self.gamestate["board"][position][i][0] = self.gamestate["board"][position][i][0]-1
            self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"] = self.gamestate["players"][playerID][i.replace("adv","")+"_cubes"]+1
        self.update()

    def remove_units(self, unit_list, position):
        color = unit_list[0].split("-")[0]
        player = self.get_player_from_color(color)
        for i in unit_list:
            if i in self.gamestate["board"][position]["player_ships"]:
                if "int" in i:
                    self.gamestate["players"][player]["ship_stock"][0] += 1
                if "cru" in i:
                    self.gamestate["players"][player]["ship_stock"][1] += 1
                if "drd" in i:
                    self.gamestate["players"][player]["ship_stock"][2] += 1
                if "sb" in i:
                    self.gamestate["players"][player]["ship_stock"][3] += 1
                self.gamestate["board"][position]["player_ships"].remove(i)
        self.update()


    def player_setup(self, player_id, faction, color):
        if self.gamestate["setup_finished"] == 1:
            return ("The game has already been setup!")

        with open("data/factions.json", "r") as f:
            faction_data = json.load(f)

        self.gamestate["players"][str(player_id)].update({"color": color})
        self.gamestate["players"][str(player_id)].update(faction_data[faction])
        self.update()
        #return(f"{name} is now setup!")

    def setup_finished(self):

        for i in self.gamestate["players"]:
            if len(self.gamestate["players"][i]) < 3:
                return(f"{self.gamestate['players'][i]['player_name']} still needs to be setup!")
            else:
                p1 = PlayerHelper(i, self.get_player(i))
                home = self.get_system_coord(p1.stats["home_planet"])
                if p1.stats["name"] == "Orion Hegemony":
                    self.gamestate["board"][home]["player_ships"].append(p1.stats["color"]+"-cru")
                else:
                    self.gamestate["board"][home]["player_ships"].append(p1.stats["color"] + "-int")

                if p1.stats["name"] == "Eridani Empire":
                    random.shuffle(self.gamestate["reputation_tiles"])
                    p1.stats["reputation_track"][0] = self.gamestate["reputation_tiles"].pop(0)
                    p1.stats["reputation_track"][1] = self.gamestate["reputation_tiles"].pop(0)
                    self.update_player(p1)

        self.gamestate["player_count"] = len(self.gamestate["players"])
        draw_count = {2: [5, 12], 3: [8, 14], 4: [14, 16], 5: [16, 18], 6: [18, 20]}

        third_sector_tiles = ["301", "302", "303", "304", "305", "306", "307", "308", "309", "310", "311", "312", "313", "314",
                              "315", "316", "317", "318", "381", "382"]
        sector_draws = draw_count[self.gamestate["player_count"]][0]
        tech_draws = draw_count[self.gamestate["player_count"]][1]

        with open("data/techs.json", "r") as f:
            tech_data = json.load(f)

        while sector_draws > 0:
            random.shuffle(third_sector_tiles)
            self.gamestate["tile_deck_300"].append(third_sector_tiles.pop(0))
            sector_draws -= 1

        while tech_draws > 0:
            random.shuffle(self.gamestate["tech_deck"])
            picked_tech = self.gamestate["tech_deck"].pop(0)

            self.gamestate["available_techs"].append(picked_tech)

            if tech_data[picked_tech]["track"] == "any":
                pass
            else:
                tech_draws -= 1

        self.gamestate["setup_finished"] = 1
        self.update()
        return("Game setup complete")

    def playerResearchTech(self, playerid, tech, type):
        self.gamestate["available_techs"].remove(tech)
        self.gamestate["players"][playerid][type+"_tech"].append(tech)
        self.update()
    def update(self):
        with open(f"{config.gamestate_path}/{self.game_id}.json", "w") as f:
            json.dump(self.gamestate, f)

    def get_player(self, player_id):
        return self.gamestate["players"][str(player_id)]

    def get_player_from_color(self, color):
        for i in self.gamestate["players"]:
            if self.gamestate["players"][i]["color"] == color:
                return i

    def update_player(self, *args):

        for ar in args:
            self.gamestate["players"][ar.player_id] = ar.stats
        self.update()

    def get_system_coord(self, sector):
        for i in (self.gamestate["board"]):
            if self.gamestate["board"][i]["sector"] == sector:
                return(i)
        return(False)

    def get_owned_tiles(self, player):
        tile_map = self.gamestate["board"]
        color = self.gamestate["players"][str(player)]["color"]
        tiles = []
        for tile in tile_map:
            if "owner" in tile_map[tile] and tile_map[tile]["owner"] == color:
                tiles.append(tile)
        return tiles

    def get_next_player(self, player):
        player_systems = []
        player_home = player["home_planet"]
        for i in ["201", "203", "205", "207", "209", "211"]:
            if "owner" in self.gamestate["board"][i] and self.gamestate["board"][i]["owner"] != 0:
                player_systems.append(i)
        tile = self.get_system_coord(player_home)
        index = player_systems.index(tile) + 1
        index = index % len(player_systems)
        new_player_color = self.gamestate["board"][player_systems[index]]["owner"]
        return self.get_player_from_color(new_player_color)

