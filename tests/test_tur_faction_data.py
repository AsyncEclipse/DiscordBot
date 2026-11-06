import json

from helpers.ShipHelper import PlayerShip
from tests.fakes import player_stats

TUR = "tur"


def tur_data():
    with open("data/factions.json", "r") as f:
        return json.load(f)[TUR]


def test_turtugan_data_row():
    row = tur_data()
    assert row["name"] == "Turtugan"
    assert row["artwork"] == "turtugan"
    assert row["setup_color"] == "teal"
    assert row["community"] is True
    assert set(row["abilities"]) == {"carapace_shields", "deep_space_explorers", "harvester"}
    assert row["starting_ships"] == ["sb"]
    assert (row["materials"], row["science"], row["money"]) == (4, 3, 3)
    assert (row["colony_ships"], row["base_colony_ships"]) == (3, 3)
    assert row["home_planet"] == "253"
    assert row["trade_value"] == 3
    assert (row["explore_apt"], row["research_apt"], row["upgrade_apt"],
            row["build_apt"], row["move_apt"], row["influence_apt"]) == (1, 1, 2, 2, 2, 2)
    assert row["influence_discs"] == 12
    assert row["influence_track"] == [30, 25, 21, 17, 13, 10, 7, 5, 3, 2, 1, 0, 0]
    assert (row["money_pop_cubes"], row["material_pop_cubes"], row["science_pop_cubes"]) == (11, 11, 12)
    assert row["military_tech"] == ["stb"]
    assert row["grid_tech"] == [] and row["nano_tech"] == []
    assert row["reputation_track"] == ["rep", "mixed", "mixed", "mixed"]
    assert row["reputation_only_slots"] == [0]
    assert (row["cost_orbital"], row["cost_monolith"]) == (4, 10)
    assert (row["cost_interceptor"], row["cost_cruiser"], row["cost_dread"],
            row["cost_starbase"]) == (3, 5, 8, 3)
    assert row["ship_stock"] == [8, 4, 2, 3]


def test_turtugan_blueprints_and_base_stats():
    row = tur_data()
    assert row["interceptor_parts"] == ["ioc", "nus", "nud"]
    assert row["cruiser_parts"] == ["ioc", "empty", "nus", "hul", "nud"]
    assert row["dread_parts"] == ["ioc", "ioc", "nus", "hul", "hul", "nud", "empty"]
    assert row["starbase_parts"] == ["hul", "nus", "nud"]
    for ship in ("interceptor", "cruiser", "dread", "starbase"):
        assert row[f"base_{ship}_speed"] == 0
        assert row[f"base_{ship}_nrg"] == 0
        assert row[f"base_{ship}_hull"] == 1
    assert (row["base_interceptor_comp"], row["base_cruiser_comp"],
            row["base_dread_comp"], row["base_starbase_comp"]) == (1, 1, 1, 0)


def test_turtugan_ship_stats_and_validity():
    player = player_stats(TUR, color="teal")
    expected = {
        "interceptor": (1, 1, 1, 1, 1, 3),
        "cruiser": (1, 1, 1, 2, 1, 5),
        "dreadnought": (1, 1, 0, 3, 1, 8),
        "starbase": (1, 1, 2, 2, 0, 3),
    }
    for ship_type, (speed, drive, energy, hull, computer, cost) in expected.items():
        ship = PlayerShip(player, ship_type)
        assert (ship.speed, ship.range, ship.energy, ship.hull, ship.computer, ship.cost) == \
               (speed, drive, energy, hull, computer, cost)
        assert ship.check_valid_ship(), ship_type


def test_a_normal_starbase_with_a_drive_is_still_invalid():
    assert not PlayerShip(player_stats("hyd", color="blue",
                                       starbase_parts=["hul", "nus", "nud"]), "starbase").check_valid_ship()
