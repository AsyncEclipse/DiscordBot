import json

from PIL import Image


def lupis():
    with open("data/sectors.json") as f:
        return json.load(f)["252"]


def test_lupis_sector_data():
    sector = lupis()
    assert sector["name"] == "Lupis"
    assert sector["type"] == "home"
    assert sector["ring"] == 2
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    assert sector["money_pop"] == [1]
    assert sector["material_pop"] == [1]
    assert sector["materialadv_pop"] == [0]
    assert sector["science_pop"] == [] and sector["neutral_pop"] == []
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_home_tile_and_numberless_art():
    for path in ("images/resources/hexes/252.png", "images/resources/hexes/numberless/252.png"):
        with Image.open(path) as tile:
            assert tile.size == (1024, 890), path
            assert tile.mode == "RGBA"
            rgba = tile.convert("RGBA")
            assert rgba.getpixel((0, 0))[3] == 0
            # the three population square centres are inside the hex
            assert rgba.getpixel((299, 79))[3] > 0
            assert rgba.getpixel((299, 191))[3] > 0
            assert rgba.getpixel((889, 399))[3] > 0
