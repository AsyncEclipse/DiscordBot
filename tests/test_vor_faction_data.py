import json
from pathlib import Path

import pytest

from helpers.ShipHelper import PlayerShip
from tests.fakes import FACTIONS, player_stats


def test_vorlons_faction_stats_match_printed_card():
    vor = FACTIONS["vor"]
    assert vor["name"] == "Vorlons"
    assert vor["artwork"] == "vorlons"
    assert vor["setup_color"] == "purple"
    assert vor["community"] is True
    assert vor["abilities"] == ["tech_masters", "organic_tech", "regenerative_hull"]
    assert vor["tech_masters_extra"] == {"first": 2, "step": 1}
    assert (vor["materials"], vor["science"], vor["money"]) == (2, 3, 3)
    assert (vor["colony_ships"], vor["base_colony_ships"]) == (3, 3)
    assert vor["home_planet"] == "235"
    assert vor["military_tech"] == [] and vor["grid_tech"] == [] and vor["nano_tech"] == ["reh"]
    assert [vor[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 2, 2, 2]
    assert vor["trade_value"] == 4
    assert vor["influence_discs"] == 12
    assert vor["influence_colony_ships"] == 1
    assert vor["reputation_track"] == ["mixed", "mixed", "mixed", "mixed"]
    assert vor.get("reputation_only_slots", []) == []
    assert (vor["money_pop_cubes"], vor["material_pop_cubes"], vor["science_pop_cubes"]) == (12, 11, 11)
    assert vor["tech_track"] == [-9, -7, -5, -4, -3, -2, -1, 0]
    assert vor["vp_per_centre"] == 2
    assert [vor[key] for key in ("cost_orbital", "cost_monolith", "cost_interceptor",
                                 "cost_cruiser", "cost_dread", "cost_starbase")] == [4, 10, 3, 5, 8, 3]
    assert vor["ship_stock"] == [7, 4, 2, 4]


def test_vorlons_starting_tech_is_regenerative_hull():
    with open("data/techs.json", "r") as f:
        techs = json.load(f)
    with open("data/parts.json", "r") as f:
        parts = json.load(f)
    assert techs["reh"]["name"] == "Regenerative Hull"
    assert techs["reh"]["track"] == "nano"
    assert techs["reh"]["num"] == 0
    assert parts["reh"]["hull"] == 1 and parts["reh"]["repair"] == 1


def test_vorlons_part_icon_exists():
    assert Path("images/resources/components/upgrades/regenerative_hull.png").is_file()

@pytest.mark.parametrize("ship,expected", [
    ("interceptor", (1, 1, 1, 0, 3, 3)),
    ("cruiser", (1, 1, 1, 1, 2, 5)),
    ("dread", (2, 0, 1, 1, 1, 8)),
    ("starbase", (2, 2, 0, 1, 4, 3)),
])
def test_vorlons_ship_stats(ship, expected):
    model = PlayerShip(player_stats("vor"), ship)
    assert (model.hull, model.energy, model.range, model.computer, model.speed, model.cost) == expected
