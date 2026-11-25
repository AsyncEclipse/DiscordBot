from tests.fakes import reload


def test_midas_setup_loads_its_data_and_money_is_power(start_game):
    game, _channel = start_game(factions=["mid", "eri"])
    state = reload(game)
    player = state.get_player(1)
    assert player["name"].startswith("Legion of Midas")
    assert player["home_planet"] == "277"
    assert player["grid_tech"] == ["ade"]
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "277"
    assert tile["moneyadv_pop"] == [1]
    assert tile["scienceadv_pop"] == [0]
    assert tile["player_ships"] == ["blue-int"]
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (11, 12, 12)
