from helpers import FactionData
from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import player_stats


def wulfen():
    return FactionData.FACTIONS["wul"]


def test_faction_identity_and_setup_facts():
    faction = wulfen()
    assert faction["name"] == "The Wulfen"
    assert faction["setup_color"] == "brown"
    assert faction["community"] is True
    assert faction["abilities"] == ["spine_cannons", "wolf_pack"]
    assert (faction["materials"], faction["science"], faction["money"]) == (2, 3, 3)
    assert (faction["colony_ships"], faction["base_colony_ships"]) == (3, 3)
    assert faction["home_planet"] == "252"
    assert faction["trade_value"] == 3
    assert faction["influence_colony_ships"] == 2


def test_action_and_influence_tracks():
    faction = wulfen()
    assert [faction[f"{action}_apt"] for action in
            ("explore", "research", "upgrade", "build", "move", "influence")] == [1, 1, 2, 2, 3, 2]
    assert faction["influence_discs"] == 12
    assert faction["influence_track"] == [30, 25, 21, 17, 13, 10, 7, 5, 3, 2, 1, 0, 0]


def test_reputation_and_population_tracks():
    faction = wulfen()
    assert faction["reputation_track"] == ["mixed", "mixed", "rep", "rep", "rep"]
    assert faction["reputation_only_slots"] == [2, 3, 4]
    assert (faction["money_pop_cubes"], faction["material_pop_cubes"],
            faction["science_pop_cubes"]) == (11, 11, 12)
    assert faction["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]


def test_technologies_and_costs():
    faction = wulfen()
    assert faction["grid_tech"] == ["fus"]
    assert faction["military_tech"] == [] and faction["nano_tech"] == []
    assert faction["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]
    assert (faction["cost_cruiser"], faction["cost_dread"], faction["cost_starbase"],
            faction["cost_orbital"], faction["cost_monolith"], faction["cost_interceptor"]) == (4, 8, 3, 4, 10, 3)
    assert faction["ship_stock"] == [0, 5, 2, 4]
    assert faction["starting_ships"] == ["cru"]
    # One cruiser starts on the home sector; five remain to build, for the printed 6 maximum.
    assert faction["ship_stock"][1] + faction["starting_ships"].count("cru") == 6
    assert "interceptor_parts" not in faction


def test_blueprints_are_valid_and_only_the_cannon_spine_slot_fires_dice():
    faction = wulfen()
    assert faction["spine_cannon_slots"] == {"cruiser": [3, 4], "dread": [6, 7], "starbase": [3, 4]}

    player = player_stats("wul", color="blue")
    for ship_type in ("cruiser", "dread", "starbase"):
        model = PlayerShip(player, ship_type)
        assert model.check_valid_ship(), ship_type
    # one Ion Cannon in the cannon slot; the augment slot contributes energy but no die
    assert PlayerShip(player, "cruiser").dice == ["yellow"]
    assert PlayerShip(player, "cruiser").dice_sources == [3]
    assert PlayerShip(player, "dread").dice == ["yellow"]
    assert PlayerShip(player, "dread").dice_sources == [6]
    assert PlayerShip(player, "starbase").dice == ["yellow"]
    assert PlayerShip(player, "starbase").dice_sources == [3]


def test_spine_slots_accept_guns_only():
    assert PlayerHelper.is_spine_gun("ioc")
    assert PlayerHelper.is_spine_gun("plc")
    assert not PlayerHelper.is_spine_gun("empty")
    assert not PlayerHelper.is_spine_gun("hul")
    assert not PlayerHelper.is_spine_gun("iom")       # missile
    assert not PlayerHelper.is_spine_gun("rican")     # rift
    assert not PlayerHelper.is_spine_gun("ricon")     # rift

    player = player_stats("wul", color="blue", military_tech=["plc"])
    assert PlayerHelper.get_spine_cannon_slots(player, "cru") == [3, 4]
    assert PlayerHelper.get_spine_cannon_slots(player, "cruiser") == [3, 4]
