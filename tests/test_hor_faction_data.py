import pytest

from helpers.ShipHelper import PlayerShip
from tests.fakes import FACTIONS, player_stats


def test_horde_faction_stats_match_printed_card():
    hor = FACTIONS["hor"]
    assert hor["name"] == "The Horde"
    assert hor["artwork"] == "horde"
    assert hor["setup_color"] == "red"
    assert hor["community"] is True
    assert hor["abilities"] == ["built_for_war", "raid", "call_to_arms", "battle_focus"]
    assert hor["call_to_arms_materials"] == {"int": 1, "cru": 2, "drd": 3}
    assert (hor["materials"], hor["science"], hor["money"]) == (3, 3, 2)
    assert (hor["colony_ships"], hor["base_colony_ships"]) == (4, 4)
    assert hor["home_planet"] == "288"
    assert hor["military_tech"] == ["neb"] and hor["grid_tech"] == [] and hor["nano_tech"] == ["nar"]
    assert [hor[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 3, 2, 2, 2]
    assert hor["trade_value"] == 3
    assert hor["influence_discs"] == 12
    assert hor["reputation_track"] == ["rep", "rep", "rep", "mixed", "mixed"]
    assert hor["reputation_only_slots"] == [0, 1, 2]
    assert (hor["money_pop_cubes"], hor["material_pop_cubes"], hor["science_pop_cubes"]) == (11, 11, 12)
    assert hor["tech_track"] == [-5, -3, -1, 0, 0, 0, 0, 0]
    assert hor["tech_track_max"] == 4
    assert [hor[key] for key in ("cost_orbital", "cost_monolith", "cost_interceptor",
                                 "cost_cruiser", "cost_dread", "cost_starbase")] == [4, 10, 3, 5, 8, 3]
    assert hor["ship_stock"] == [7, 4, 2, 4]


def test_horde_blueprint_slot_counts():
    hor = FACTIONS["hor"]
    assert [len(hor[f"{ship}_parts"]) for ship in ("interceptor", "cruiser", "dread")] == [4, 6, 8]


@pytest.mark.parametrize("ship,expected", [
    ("interceptor", (0, 1, 1, 0, 2, 3)),
    ("cruiser", (1, 1, 1, 1, 1, 5)),
    ("dread", (2, 0, 1, 1, 1, 8)),
    ("starbase", (2, 2, 0, 1, 3, 3)),
])
def test_horde_ship_stats(ship, expected):
    model = PlayerShip(player_stats("hor"), ship)
    assert (model.hull, model.energy, model.range, model.computer, model.speed, model.cost) == expected
