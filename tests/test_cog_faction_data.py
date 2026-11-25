from tests.fakes import FACTIONS


def test_cog_faction_stats_match_printed_board():
    cog = FACTIONS["cog"]
    assert cog["name"] == "Children of Cog"
    assert cog["artwork"] == "cog"
    assert cog["setup_color"] == "green"
    assert cog["community"] is True
    assert cog["abilities"] == ["infinite_possibilities", "adaptive_transformation"]
    assert (cog["materials"], cog["science"], cog["money"]) == (3, 2, 3)
    assert (cog["colony_ships"], cog["base_colony_ships"]) == (3, 3)
    assert cog["home_planet"] == "256"
    assert cog["military_tech"] == [] and cog["grid_tech"] == [] and cog["nano_tech"] == ["nar"]
    assert [cog[key] for key in ("explore_apt", "research_apt", "upgrade_apt",
                                 "build_apt", "move_apt", "influence_apt")] == [1, 1, 3, 2, 2, 2]
    assert cog["trade_value"] == 3
    assert cog["influence_discs"] == 12
    assert cog["reputation_track"] == ["amb", "mixed", "mixed", "mixed", "mixed"]
    assert cog.get("reputation_only_slots", []) == []
    assert (cog["money_pop_cubes"], cog["material_pop_cubes"], cog["science_pop_cubes"]) == (12, 11, 11)
    assert cog["population_track"] == [28, 24, 21, 18, 15, 12, 10, 8, 6, 4, 3, 2, 0]
    assert cog["tech_track"] == [-3, -3, -2, -2, -2, -1, 0, 0]
    assert cog["tech_track_vp"] == [0, 0, 0, 1, 2, 2, 2, 3]
    assert [cog[key] for key in ("cost_orbital", "cost_monolith", "cost_interceptor",
                                 "cost_cruiser", "cost_dread", "cost_starbase")] == [4, 10, 3, 5, 8, 3]
    assert cog["ship_stock"] == [7, 4, 2, 4]
