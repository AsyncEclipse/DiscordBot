from tests.fakes import reload


def test_horde_setup_loads_its_data(start_game):
    game, _channel = start_game(factions=["hor", "eri"])
    state = reload(game)
    player = state.get_player(1)
    assert player["name"].startswith("The Horde")
    assert player["home_planet"] == "288"
    assert player["military_tech"] == ["neb"] and player["nano_tech"] == ["nar"]
    assert player["build_apt"] == 3  # printed 2 plus the starting Nanorobots activation
    assert player["colony_ships"] == 4
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "288"
    assert tile["money_pop"] == [1] and tile["material_pop"] == [1]
    assert tile["player_ships"] == ["blue-int"]
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (11, 11, 12)
