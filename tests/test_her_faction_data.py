import pytest

from helpers.PlayerHelper import PlayerHelper
from helpers.ShipHelper import PlayerShip
from tests.fakes import FACTIONS, player_stats


def test_heralds_faction_stats_match_printed_board():
    her = FACTIONS["her"]
    assert her["name"] == "Heralds of Ragnarok"
    assert her["artwork"] == "heralds"
    assert her["setup_color"] == "yellow"
    assert her["community"] is True
    assert her["abilities"] == ["raid", "regroup"]
    assert her["starting_ships"] == ["cru"]
    assert (her["materials"], her["science"], her["money"]) == (2, 3, 3)
    assert (her["colony_ships"], her["base_colony_ships"]) == (3, 3)
    assert her["home_planet"] == "299"
    assert her["military_tech"] == ["neb"]
    assert her["trade_value"] == 3
    assert [her[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 2, 2, 2]
    assert her["influence_discs"] == 12
    assert her["reputation_track"] == ["amb", "mixed", "mixed", "rep", "rep"]
    assert her["reputation_only_slots"] == [3, 4]
    assert (her["money_pop_cubes"], her["material_pop_cubes"], her["science_pop_cubes"]) == (11, 12, 11)
    assert her["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]
    assert her["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]
    assert [her[key] for key in ("cost_orbital", "cost_monolith", "cost_interceptor",
                                 "cost_cruiser", "cost_dread", "cost_starbase")] == [4, 10, 4, 4, 8, 3]
    assert her["ship_stock"] == [8, 3, 2, 4]


@pytest.mark.parametrize("ship,expected", [
    # hull, energy, range, computer, initiative (base + Nuclear Drive), cost
    ("interceptor", (1, 1, 1, 0, 2, 4)),
    ("cruiser", (0, 1, 1, 1, 3, 4)),
    ("dread", (2, 0, 1, 1, 1, 8)),
    ("starbase", (2, 2, 0, 1, 4, 3)),
])
def test_heralds_ship_stats(ship, expected):
    model = PlayerShip(player_stats("her"), ship)
    actual = (model.hull, model.energy, model.range, model.computer, model.speed, model.cost)
    assert actual == expected


def test_heralds_reputation_track_uses_three_relation_slots():
    player = player_stats("her")
    assert PlayerHelper.is_reputation_only_slot(player, 3)
    assert PlayerHelper.is_reputation_only_slot(player, 4)
    assert PlayerHelper.has_reputation_slot_for_relation(player)

    # One ambassador-only and two mixed slots: three relations, then only rep-only slots remain.
    player["reputation_track"] = ["amb-hyd-blue", "mixed-eri-red", "mixed-dra-green", 5, 4]
    assert not PlayerHelper.has_reputation_slot_for_relation(player)


def test_heralds_blueprint_layout_has_one_cell_per_part():
    her = FACTIONS["her"]
    for ship in ("interceptor", "cruiser"):
        assert len(her[f"{ship}_parts"]) == 5
    assert [1, 0] not in her["blueprint_slots"]["cruiser"]
