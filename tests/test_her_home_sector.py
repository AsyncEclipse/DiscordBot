import json

from PIL import Image

from tests.fakes import reload


def her_home_sector():
    with open("data/sectors.json", "r") as f:
        return json.load(f)["299"]


def test_heralds_home_sector_data():
    sector = her_home_sector()
    assert sector["name"] == "Yggdrasil"
    assert sector["type"] == "home"
    assert sector["ring"] == 2
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    # The card prints one advanced Money square plus normal Money and Science squares.
    assert sector["money_pop"] == [1]
    assert sector["moneyadv_pop"] == [0]
    assert sector["science_pop"] == [1]
    assert sector["material_pop"] == [] and sector["materialadv_pop"] == []
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_heralds_home_sector_tile_art():
    path = "images/resources/hexes/299.png"
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        assert tile.mode == "RGBA"
        assert tile.convert("RGBA").getpixel((0, 0))[3] == 0
        tile.load()


def test_heralds_home_sector_is_set_up_on_the_board(start_game):
    game, _channel = start_game(factions=["her", "eri"])
    state = reload(game)
    tile = state.gamestate["board"]["201"]
    assert tile["sector"] == "299"
    assert tile["money_pop"] == [1]
    assert tile["moneyadv_pop"] == [0]
    assert tile["science_pop"] == [1]
    player = state.get_player(1)
    assert (player["money_pop_cubes"], player["material_pop_cubes"], player["science_pop_cubes"]) == (11, 12, 11)
    assert state.gamestate["board"]["201"]["player_ships"] == ["blue-cru"]
