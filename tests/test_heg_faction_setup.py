from tests.fakes import reload


def test_hegemony_setup_loads_its_data(start_game):
    game, _channel = start_game(factions=["heg", "eri"])
    state = reload(game)
    player = state.get_player(1)
    assert player["name"].startswith("Hegemony of the Highest Cushion")
    assert player["home_planet"] == "276"
    assert player["nano_tech"] == ["fud"]
    assert player["interceptor_parts"] == ["ioc", "nus", "nud", "empty"]
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "276"
    assert tile["material_pop"] == [1] and tile["science_pop"] == [1]
    assert tile["scienceadv_pop"] == [0] and tile["money_pop"] == [1]
    assert tile["player_ships"] == ["blue-int"]
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (11, 11, 11)
