import json

from PIL import Image

from tests.fakes import buttons, reload


def wra_home_sector():
    with open("data/sectors.json", "r") as f:
        return json.load(f)["254"]


def test_wra_home_sector_data():
    sector = wra_home_sector()
    assert sector["name"] == "Simulacra"
    assert sector["type"] == "home"
    assert sector["ring"] == 2
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    # The art prints one money square, one plain science square and an empty Advanced science square.
    assert sector["money_pop"] == [1]
    assert sector["science_pop"] == [1]
    assert sector["scienceadv_pop"] == [0]
    assert sector["material_pop"] == [] and sector["materialadv_pop"] == []
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_wra_home_sector_tile_art():
    for path in ("images/resources/hexes/254.png", "images/resources/hexes/numberless/254.png"):
        with Image.open(path) as tile:
            assert tile.size == (1024, 890)
            assert tile.mode == "RGBA"
            assert tile.getpixel((0, 0))[3] == 0
            tile.load()


def test_setup_places_two_cubes_and_leaves_the_advanced_science_square_empty(start_game):
    game, _channel = start_game(factions=["wra", "eri"])
    state = reload(game)
    home = state.gamestate["board"]["201"]
    player = state.get_player(1)

    assert home["sector"] == "254"
    assert home["money_pop"] == [1]
    assert home["science_pop"] == [1]
    assert home["scienceadv_pop"] == [0]
    assert home["material_pop"] == []
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (11, 12, 11)


def test_advanced_labs_unlocks_the_home_advanced_science_square(start_game, press):
    game, channel = start_game(factions=["wra", "eri"])
    game.get_player(1)["nano_tech"].append("adl")
    game.update()

    press(channel, 1, "FCIDblue_startPopDrop")
    assert "FCIDblue_fillPopulation_201_scienceadv_0" in buttons(channel)
    press(channel, 1, "FCIDblue_fillPopulation_201_scienceadv_0")

    state = reload(game)
    assert state.gamestate["board"]["201"]["scienceadv_pop"] == [1]
    assert state.get_player(1)["science_pop_cubes"] == 10
    assert state.get_player(1)["colony_ships"] == 2
