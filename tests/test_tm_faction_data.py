from tests.fakes import FACTIONS


def test_tm_faction_stats_match_printed_board():
    tm = FACTIONS["tm"]
    assert tm["name"] == "Techno-Mages"
    # 2 materials / 6 science / 3 money / 3 colony ships, all printed on the board's storage strip.
    assert (tm["materials"], tm["science"], tm["money"]) == (2, 6, 3)
    assert (tm["colony_ships"], tm["base_colony_ships"]) == (3, 3)
    assert tm["home_planet"] == "244"
    assert tm["military_tech"] == tm["grid_tech"] == tm["nano_tech"] == []
    assert tm["trade_value"] == 3
    # Limited Manufacturing: 1 activation with a Build Action.
    assert [tm[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 1, 2, 2]
    assert tm["reputation_track"] == ["amb", "mixed", "mixed", "mixed"]
    assert tm["influence_discs"] == 12
    # Two cubes start on the home sector's science squares.
    assert (tm["money_pop_cubes"], tm["material_pop_cubes"], tm["science_pop_cubes"]) == (12, 12, 10)
    # The income row every faction uses (DrawHelper.display_cube_track_reference indexes into it).
    assert tm["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]
    assert tm["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]
