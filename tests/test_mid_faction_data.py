from tests.fakes import FACTIONS


def test_midas_faction_stats_match_printed_card():
    mid = FACTIONS["mid"]
    assert mid["name"] == "Legion of Midas"
    assert mid["artwork"] == "midas"
    assert mid["setup_color"] == "yellow"
    assert mid["community"] is True
    assert mid["abilities"] == ["midas_touch", "money_is_power", "all_that_glitters", "midas_neutral_pop"]
    assert (mid["materials"], mid["science"], mid["money"]) == (2, 3, 4)
    assert (mid["colony_ships"], mid["base_colony_ships"]) == (4, 3)
    assert mid["home_planet"] == "277"
    assert mid["military_tech"] == [] and mid["grid_tech"] == ["ade"] and mid["nano_tech"] == []
    assert [mid[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 2, 2, 2, 2]
    assert mid["trade_value"] == 3
    assert mid["influence_discs"] == 12
    assert mid["reputation_track"] == ["amb", "mixed", "mixed", "mixed"]
    assert mid.get("reputation_only_slots", []) == []
    assert (mid["money_pop_cubes"], mid["material_pop_cubes"], mid["science_pop_cubes"]) == (12, 12, 12)
    assert mid["tech_track"] == [-8, -6, -4, -3, -2, -1, 0, 0]
    assert [mid[key] for key in ("cost_orbital", "cost_monolith", "cost_interceptor",
                                 "cost_cruiser", "cost_dread", "cost_starbase")] == [4, 10, 3, 5, 8, 3]
    assert mid["ship_stock"] == [7, 4, 2, 4]
