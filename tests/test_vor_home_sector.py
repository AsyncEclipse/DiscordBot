import json

from PIL import Image


def vorlons_home():
    with open("data/sectors.json") as f:
        return json.load(f)["235"]


def test_vorlons_home_sector_data():
    sector = vorlons_home()
    assert sector["name"] == "Vorla"
    assert sector["type"] == "home"
    assert sector["ring"] == 2
    assert sector["vp"] == 3
    assert sector["artifact"] == 1
    assert sector["wormholes"] == [0, 1, 3, 4]
    assert sector["material_pop"] == [1]
    assert sector["science_pop"] == [1]
    assert sector["neutraladv_pop"] == [0]
    for key, coords in sector.items():
        if key.endswith("_snap") and coords:
            assert len(coords) == 2, f"{key} {coords} is not a point"
            assert 0 <= coords[0] <= 1024 and 0 <= coords[1] <= 890, f"{key} {coords} is off the tile"


def test_vorlons_home_tile_art():
    path = "images/resources/hexes/235.png"
    with Image.open(path) as tile:
        assert tile.size == (1024, 890)
        assert tile.mode == "RGBA"
        rgba = tile.convert("RGBA")
        assert rgba.getpixel((0, 0))[3] == 0
        for point in ((533, 129), (699, 276), (606, 693)):
            assert rgba.getpixel(point)[3] > 0
        tile.load()
