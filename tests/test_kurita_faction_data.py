"""Kurita Prefecture data, read from the printed board and the V1.22 card."""
import json

from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import player_stats


def faction():
    with open("data/factions.json", "r") as f:
        return json.load(f)["kur"]


def test_kurita_identity_and_draft_data():
    kur = faction()
    assert kur["name"] == "Kurita Prefecture"
    assert kur["artwork"] == "kurita"
    assert kur["setup_color"] == "red"
    assert kur["community"] is True


def test_kurita_starting_values():
    kur = faction()
    assert (kur["materials"], kur["science"], kur["money"]) == (4, 3, 2)
    assert (kur["colony_ships"], kur["base_colony_ships"]) == (3, 3)
    assert kur["home_planet"] == "251"
    assert kur["trade_value"] == 3
    assert kur["influence_discs"] == 12
    assert [kur[f"{action}_apt"] for action in
            ("explore", "research", "upgrade", "build", "move", "influence")] == [1, 1, 2, 2, 2, 2]


def test_kurita_starts_with_phase_shields_only():
    kur = faction()
    assert kur["military_tech"] == ["phs"]
    assert kur["grid_tech"] == [] and kur["nano_tech"] == [] and kur["ancient_parts"] == []


def test_kurita_reputation_and_traitor_values():
    kur = faction()
    assert kur["reputation_track"] == ["mixed", "mixed", "rep", "rep"]
    assert kur["reputation_only_slots"] == [2, 3]
    assert kur["traitor_vp_penalty"] == -4


def test_kurita_population_tracks():
    kur = faction()
    assert (kur["money_pop_cubes"], kur["material_pop_cubes"], kur["science_pop_cubes"]) == (11, 12, 11)
    assert kur["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]
    assert kur["influence_track"] == [30, 25, 21, 17, 13, 10, 7, 5, 3, 2, 1, 0, 0]
    assert kur["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]


def test_kurita_blueprints_match_the_board():
    kur = faction()
    assert kur["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    assert kur["cruiser_parts"] == ["elc", "ioc", "empty", "nus", "hul", "nud"]
    assert kur["dread_parts"] == ["elc", "ioc", "ioc", "empty", "nus", "hul", "hul", "nud"]
    assert kur["starbase_parts"] == ["elc", "ioc", "hul", "empty", "hul"]


def test_kurita_printed_off_board_stats():
    kur = faction()
    assert [kur[f"base_{ship}_speed"] for ship in ("interceptor", "cruiser", "dread", "starbase")] == [2, 1, 0, 4]
    assert [kur[f"base_{ship}_comp"] for ship in ("interceptor", "cruiser", "dread", "starbase")] == [1, 1, 1, 1]
    assert kur["base_starbase_hull"] == 1
    assert kur["base_starbase_nrg"] == 3
    assert (kur["cost_orbital"], kur["cost_monolith"]) == (4, 10)
    assert [kur[f"cost_{ship}"] for ship in ("interceptor", "cruiser", "dread", "starbase")] == [3, 5, 8, 3]
    assert kur["ship_stock"] == [7, 4, 2, 4]
    player = player_stats("kur")
    assert [PlayerShip(player, ship).computer
            for ship in ("interceptor", "cruiser", "dread", "starbase")] == [1, 2, 2, 2]
    assert PlayerShip(player, "starbase").hull == 3
    assert PlayerShip(player_stats("hyd"), "interceptor").computer == 0
    assert PlayerShip(player_stats("atl"), "starbase").hull == 2


def test_kurita_has_only_the_two_abilities_needing_code():
    assert faction()["abilities"] == ["first_shot", "honour_victorious"]


def test_kurita_reputation_only_slots_stay_out_of_relations():
    player = faction()
    player["color"] = "blue"
    player["reputation_track"] = [1, 2, 3, 4]
    assert [index for index in range(4) if PlayerHelper.is_reputation_only_slot(player, index)] == [2, 3]
