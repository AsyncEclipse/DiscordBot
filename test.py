import json

with open("activegames/aeb39.json", "r") as f:
    gamestate = json.load(f)

player = {"player_name": "<@1254924413946826812>", "color": "red", "name": "Mechanema", "materials": 4, "science": 3, "money": 3, "colony_ships": 3, "base_colony_ships": 3, "home_planet": "230", "owned_tiles": [], "explore_apt": 1, "research_apt": 1, "upgrade_apt": 3, "build_apt": 3, "move_apt": 2, "influence_apt": 2, "trade_value": 3, "influence_discs": 12, "influence_track": [30, 25, 21, 17, 13, 10, 7, 5, 3, 2, 1, 0, 0], "money_pop_cubes": 11, "material_pop_cubes": 12, "science_pop_cubes": 11, "population_track": [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0], "military_tech": [], "grid_tech": ["poc"], "nano_tech": [], "tech_track": [-8, -5, -4, -3, -2, -1, 0, 0], "reputation_track": ["mixed", "mixed", "mixed", "mixed"], "cost_orbital": 3, "cost_monolith": 8, "cost_interceptor": 2, "cost_cruiser": 4, "cost_dread": 7, "cost_starbase": 2, "ship_stock": [7, 4, 2, 4], "base_interceptor_speed": 2, "base_interceptor_nrg": 0, "base_interceptor_comp": 0, "base_cruiser_speed": 1, "base_cruiser_nrg": 0, "base_cruiser_comp": 0, "base_dread_speed": 0, "base_dread_nrg": 0, "base_dread_comp": 0, "base_starbase_speed": 4, "base_starbase_nrg": 3, "base_starbase_comp": 0, "interceptor_parts": ["ioc", "nus", "nud", "empty"], "cruiser_parts": ["elc", "ioc", "empty", "nus", "hul", "nud"], "dread_parts": ["elc", "ioc", "ioc", "empty", "nus", "hul", "hul", "nud"], "starbase_parts": ["elc", "ioc", "hul", "empty", "hul"]}
#def get_next_player(player):
#    player_systems = []
#    player_home = player["home_planet"]
#    for i in ["201", "203", "205", "207", "209", "211"]:
#        if "owner" in gamestate["board"][i]:
#            player_systems.append(i)
#    tile = get_system_coord(player_home)
#    index = player_systems.index(tile) + 1
#    index = index % len(player_systems)
#    new_player_color = gamestate["board"][player_systems[index]]["owner"]
#    return get_player_from_color(new_player_color)

def player_test(player):
    player_systems = []
    player_home = "207"
    for i in ["201", "203", "205", "207", "209", "211"]:
        if "owner" in gamestate["board"][i] and gamestate["board"][i]["owner"] != 0:
            player_systems.append(i)
    index = player_systems.index(player_home) + 1
    index = index % len(player_systems)
    print(index)

player_test(player)