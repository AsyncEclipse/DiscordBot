import json

from tests.fakes import FACTIONS


def test_ra_faction_stats_match_printed_board():
    ra = FACTIONS["ra"]
    assert ra["name"] == "Remnants of Ra"
    assert (ra["materials"], ra["science"], ra["money"]) == (3, 3, 2)
    assert (ra["colony_ships"], ra["base_colony_ships"]) == (3, 3)
    assert ra["home_planet"] == "255"
    assert ra["military_tech"] == ["plc"]
    assert ra["trade_value"] == 4
    assert [ra[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 2, 2, 2]
    assert ra["reputation_track"] == ["mixed"] * 4
    assert ra["influence_discs"] == 12
    assert (ra["money_pop_cubes"], ra["material_pop_cubes"], ra["science_pop_cubes"]) == (11, 12, 12)
    # The income row every faction uses (DrawHelper.display_cube_track_reference indexes into it).
    assert ra["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]


def test_ra_starting_tech_is_plasma_cannon():
    with open("data/techs.json", "r") as f:
        techs = json.load(f)
    assert techs["plc"]["name"] == "Plasma Cannon"
    assert techs["plc"]["track"] == "military"


def test_ra_blueprint_parts_exist():
    with open("data/parts.json", "r") as f:
        parts = json.load(f)
    ra = FACTIONS["ra"]
    for ship in ("interceptor", "cruiser", "dread", "starbase"):
        for part in ra[f"{ship}_parts"]:
            assert part == "empty" or part in parts, f"unknown {ship} part {part!r}"
