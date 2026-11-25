from tests.fakes import reload


def test_vorlons_setup_loads_its_data(start_game):
    game, _channel = start_game(factions=["vor", "eri"])
    state = reload(game)
    player = state.get_player(1)
    assert player["name"].startswith("Vorlons")
    assert player["home_planet"] == "235"
    assert player["nano_tech"] == ["reh"]
    assert player["interceptor_parts"] == ["ioc", "nus", "reh", "nud"]
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "235"
    assert tile["material_pop"] == [1] and tile["science_pop"] == [1]
    assert tile["player_ships"] == ["blue-int"]
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (12, 11, 11)
