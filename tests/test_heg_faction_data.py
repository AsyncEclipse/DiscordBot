from tests.fakes import FACTIONS


def test_hegemony_faction_stats_match_printed_card():
    heg = FACTIONS["heg"]
    assert heg["name"] == "Hegemony of the Highest Cushion"
    assert heg["artwork"] == "hegemony"
    assert heg["setup_color"] == "yellow"
    assert heg["community"] is True
    assert heg["abilities"] == ["nine_lives", "pounce", "solitary_hunter"]
    assert (heg["materials"], heg["science"], heg["money"]) == (2, 3, 3)
    assert (heg["colony_ships"], heg["base_colony_ships"]) == (3, 3)
    assert heg["home_planet"] == "276"
    assert (heg["military_tech"], heg["grid_tech"], heg["nano_tech"]) == ([], [], ["fud"])
    assert [heg[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 2, 2, 2]
    assert heg["trade_value"] == 3
    assert heg["influence_discs"] == 12
    assert heg.get("influence_colony_ships", 2) == 2
    assert heg["reputation_track"] == ["mixed", "mixed", "mixed", "mixed"]
    assert heg.get("reputation_only_slots", []) == []
    assert (heg["money_pop_cubes"], heg["material_pop_cubes"], heg["science_pop_cubes"]) == (11, 11, 11)
    # printed cells 0, -1, -2, -3, -4, -6, -8 (the first cell is the starting-tech space)
    assert heg["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]
    assert heg.get("tech_track_max", 7) == 7
    assert heg["vp_per_centre"] == 2
    assert heg["vp_per_centre_allies"] is False  # Pride reads "you", not "you or an Ally"
    assert [heg[key] for key in ("cost_orbital", "cost_monolith", "cost_interceptor",
                                 "cost_cruiser", "cost_dread", "cost_starbase")] == [4, 10, 3, 5, 8, 3]
    assert heg["ship_stock"] == [7, 4, 2, 4]
    assert "blueprint_slots" not in heg


def test_hegemony_blueprints_are_the_standard_ships():
    heg = FACTIONS["heg"]
    # The card prints "Standard Ships"; the board's interceptor shows a Hull where the
    # standard blueprint has its Ion Cannon, so the card's text wins.
    assert heg["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    assert heg["cruiser_parts"] == ["elc", "ioc", "empty", "nus", "hul", "nud"]
    assert heg["dread_parts"] == ["elc", "ioc", "ioc", "empty", "nus", "hul", "hul", "nud"]
    assert heg["starbase_parts"] == ["elc", "ioc", "hul", "empty", "hul"]
