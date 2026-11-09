import json

from PIL import Image


def home_sector():
    with open("data/sectors.json", "r") as f:
        return json.load(f)["251"]


def test_kurita_home_sector_data():
    sector = home_sector()
    assert sector["name"] == "Edo"
    assert sector["type"] == "home"
    assert (sector["ring"], sector["disctile"]) == (2, 0)
    assert sector["owner"] == 0 and sector["player_ships"] == []
    assert (sector["vp"], sector["artifact"]) == (3, 1)
    assert [sector[key] for key in ("ancient", "guardian", "gcds", "warp")] == [0, 0, 0, 0]
    assert sector["wormholes"] == [0, 1, 3, 4]


def test_kurita_home_population_squares():
    sector = home_sector()
    assert sector["money_pop"] == [1]
    assert sector["science_pop"] == [1]
    assert sector["scienceadv_pop"] == [0]
    assert sector["materialadv_pop"] == [0]
    for key in ("moneyadv_pop", "material_pop", "neutral_pop", "neutraladv_pop"):
        assert sector[key] == []
    assert sector["money1_snap"] == [323, 137]
    assert sector["science1_snap"] == [762, 203]
    assert sector["scienceadv1_snap"] == [650, 198]
    assert sector["materialadv1_snap"] == [334, 783]
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_kurita_home_sector_tile_art():
    path = "images/resources/hexes/251.png"
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        assert tile.mode == "RGBA"
        assert tile.convert("RGBA").getpixel((0, 0))[3] == 0
        tile.load()


def test_kurita_home_sector_numberless_variant():
    path = "images/resources/hexes/numberless/251.png"
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        assert tile.mode == "RGBA"
        assert tile.convert("RGBA").getpixel((0, 0))[3] == 0
        tile.load()
