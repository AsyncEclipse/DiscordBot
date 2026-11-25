import json

from PIL import Image


def midas_home():
    with open("data/sectors.json") as f:
        return json.load(f)["277"]


def test_midas_home_sector_data():
    sector = midas_home()
    assert sector["name"] == "Phrygia - Ionys"
    assert sector["type"] == "home"
    assert sector["ring"] == 2
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    assert sector["neutral_pop"] == [0]
    assert sector["scienceadv_pop"] == [0]
    assert sector["moneyadv_pop"] == [0]
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_midas_home_tile_art():
    path = "images/resources/hexes/277.png"
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        assert tile.mode == "RGBA"
        rgba = tile.convert("RGBA")
        assert rgba.getpixel((0, 0))[3] == 0
        for point in ((279, 295), (540, 640), (713, 762)):
            assert rgba.getpixel(point)[3] > 0
        tile.load()
