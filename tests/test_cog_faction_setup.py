from tests.fakes import reload


def test_cog_setup_loads_its_data(start_game):
    game, unused_channel = start_game(factions=["cog", "eri"])
    state = reload(game)
    player = state.get_player(1)
    assert player["name"].startswith("Children of Cog")
    assert player["home_planet"] == "256"
    assert player["nano_tech"] == ["nar"]
    assert player["build_apt"] == 3  # printed 2 plus the starting Nanorobots activation
    assert player["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "256"
    assert tile["moneyadv_pop"] == [0]
    assert tile["science_pop"] == [1] and tile["scienceadv_pop"] == []
    assert tile["material_pop"] == [1] and tile["materialadv_pop"] == [0]
    assert tile["player_ships"] == ["blue-int"]
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (12, 11, 11)
